'use client';

/**
 * Stage 2a T13: cloud library sidebar. Fetches the signed-in owner's playlists via the
 * scope-aware api client (lib/client/api.ts — `listPlaylists()` needs no scope argument;
 * the owner is resolved server-side from the session) and renders one nav item per
 * playlist, linking to `/?playlist=<uuid>` (spec §9 URL Contracts). The active item is
 * derived from the current `?playlist` query param via `useSearchParams()`.
 *
 * "+ New playlist" invokes the optional `onNewPlaylist` callback (ingest UI wiring lands
 * elsewhere in Stage 2b); it never fetches or navigates on its own.
 *
 * Not wrapped in useScope()/ScopeProvider: that wiring lands in T15 alongside CloudApp's
 * full library view. This component only needs the (unscoped) playlist list + the URL.
 *
 * playlist-sidebar-ux T5 (BUG-6 backfill trigger): after the initial load, if the caller
 * is signed in (`userId` non-null) and the loaded list contains at least one null title,
 * fire the bounded backfill route once per session per user (sessionStorage key
 * `backfilledTitles:${userId}`) and re-fetch. A `useRef` one-shot guard (NOT derived from
 * `playlists` state) plus the sessionStorage flag — both set BEFORE the backfill call
 * resolves — ensure this fires at most once even if the post-backfill refetch still has
 * null rows, and survives React 18 StrictMode's double effect invocation. `userId === null`
 * (no session) is a documented skip, not a fallback key — there is nothing to backfill for
 * an unauthenticated sidebar and no per-user key can be formed.
 *
 * playlist-sidebar-ux T10 (full hard-delete): each row gets a trash button that is a
 * SIBLING of the row's `<Link>` (never nested inside the `<a>` — invalid interactive
 * nesting and can still navigate, spec §B7). Clicking it opens `DeletePlaylistDialog` for
 * that row; `stopPropagation`/`preventDefault` on the button's own click for good measure.
 * `onDeleted` refetches the list and, if the deleted playlist was the active one
 * (`?playlist=` match), navigates to `/` (no `?playlist=` param).
 */
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { backfillPlaylistTitles, listPlaylists, UnauthorizedError } from '@/lib/client/api';
import type { PlaylistSummary } from '@/lib/storage/metadata-store';
import { DeletePlaylistDialog } from './DeletePlaylistDialog';

const activeLinkClass =
  'block truncate rounded-r px-2 py-1.5 border-l-2 border-[var(--accent)] bg-[var(--surface-overlay)] text-[var(--text-primary)]';
const inactiveLinkClass =
  'block truncate rounded-r px-2 py-1.5 border-l-2 border-transparent text-[var(--text-secondary)] hover:bg-[var(--surface-overlay)] hover:text-[var(--text-primary)]';

interface PlaylistSidebarProps {
  onNewPlaylist?: () => void;
  userId: string | null;
  /** backlog #37: CHANGE this value to make the sidebar re-read the list. The parent owns it
   *  because the parent is what changes the list — see the refetch effect below for why it is a
   *  separate input rather than something this component could detect on its own. Only the fact
   *  that it changed matters, not its value or starting point. */
  refreshKey?: number;
}

export default function PlaylistSidebar({ onNewPlaylist, userId, refreshKey }: PlaylistSidebarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activePlaylistId = searchParams.get('playlist');

  const [playlists, setPlaylists] = useState<PlaylistSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<PlaylistSummary | null>(null);
  // One-shot guard for the auto-backfill trigger — deliberately NOT derived from `playlists`
  // state (a state-derived guard would re-arm and loop if the post-backfill refetch still
  // has null titles). Persists across StrictMode's double effect invocation because it's the
  // same fiber's ref, not remounted.
  const backfillFiredRef = useRef(false);

  // Every path that loads the list goes through `loadPlaylists` below — the [userId] mount effect,
  // the [refreshKey] ingest refetch, the post-backfill reloads, and handleDeleted. It took three
  // review rounds to get the concurrency right, and each round's fix produced the next round's
  // defect, so the reasoning is recorded here rather than rediscovered.
  //
  // Round 1 (High) — per-effect `cancelled` booleans are not enough. Each only knows its own effect,
  // so a slow mount fetch could resolve AFTER a fast post-ingest refetch and overwrite the new
  // playlist with the pre-ingest list, restoring the very bug this branch removes. It is reachable
  // because "+ New playlist" renders while the list is still loading. `PlaylistLibrary` already
  // guards listVideos this way (CloudApp.tsx `reqSeq`); this is the same problem.
  //
  // Round 2 (High, twice) — one counter is not enough either, because "newest STARTED" and "newest
  // APPLIED" diverge exactly when a load fails. Guarding only successes let a stale REJECTION raise
  // an error, or redirect to /login, over a list a newer load had already rendered. Guarding against
  // newest-started let a newer FAILED load permanently discard an older one that then succeeded.
  // What governs the screen is the newest load that actually applied something.
  //
  // Round 3 (High) — a caller checking its own `cancelled` flag on the returned promise checks too
  // late, because the write happens inside the helper. Cancellation is now passed IN.
  //
  // Three questions, asked at the moment of the write: was I superseded (appliedSeq), am I still the
  // newest attempt (startedSeq), and does my caller still exist (isCancelled)?
  const startedSeqRef = useRef(0);
  const appliedSeqRef = useRef(0);

  /** Fetch the list and apply it only if no NEWER load has already applied one. Returns the list
   *  when applied, or null when this load no longer speaks for the screen — callers must read null
   *  as "do nothing further", never as "the owner has no playlists".
   *
   *  `isCancelled` is the CALLER's teardown check and is consulted before the state write, not
   *  after. Round 3 (High): this helper writes state internally, so a caller that checked its own
   *  `cancelled` flag on the returned promise was checking too late — on an in-place account switch
   *  (userId A→B, no remount) user A's in-flight load would render A's playlists under B's sidebar.
   *  Sequence answers "was I superseded?", cancellation answers "does my caller still exist?", and
   *  both have to be asked at the moment of the write.
   *
   *  Rejections propagate to the caller ONLY while this is still the newest load in flight; a stale
   *  rejection resolves to null instead, because a load that has been overtaken has no standing to
   *  put an error on screen. */
  async function loadPlaylists(isCancelled: () => boolean = () => false): Promise<PlaylistSummary[] | null> {
    const seq = ++startedSeqRef.current;
    try {
      const result = await listPlaylists();
      if (isCancelled() || seq <= appliedSeqRef.current) return null;
      appliedSeqRef.current = seq;
      setPlaylists(result);
      // Clear any banner a PREVIOUS failure left behind: we now have a good list, and the render
      // shows both, so a stale error would otherwise sit above fresh data forever (round 3, Medium).
      setError(null);
      return result;
    } catch (err) {
      if (isCancelled() || seq !== startedSeqRef.current) return null; // overtaken — stay silent
      throw err;
    }
  }

  useEffect(() => {
    let cancelled = false;
    // review fix: reset the one-shot guard at the START of the effect (before any check) so an
    // in-place account switch (userId A→B on the same mounted instance, no remount) gives B its
    // own one-shot instead of inheriting A's already-fired ref. This runs on every [userId]
    // change, including the initial mount, so it's a no-op the very first time (ref already
    // starts false). It does NOT reopen the door within a session for the SAME userId: the ref
    // and sessionStorage key are both re-set (see below) before this effect can run again for
    // that userId, and the effect only re-runs when userId itself changes.
    backfillFiredRef.current = false;
    loadPlaylists(() => cancelled)
      .then(async (result) => {
        if (cancelled || result === null) return; // null ⇒ superseded by a newer load

        if (userId === null) return; // no session ⇒ no per-user key, nothing to backfill
        const sessionKey = `backfilledTitles:${userId}`;
        const alreadyRan = backfillFiredRef.current || sessionStorage.getItem(sessionKey) !== null;
        if (alreadyRan || !result.some((p) => !p.playlistTitle)) return;

        // Set both guards before awaiting so a slow/failed call still counts as "ran this
        // session" — matches the once-per-session contract even on backfill failure.
        backfillFiredRef.current = true;
        sessionStorage.setItem(sessionKey, '1');
        try {
          await backfillPlaylistTitles();
          if (cancelled) return;
          await loadPlaylists(() => cancelled);
        } catch {
          // best-effort — keep the pre-backfill list on failure, matching the existing
          // silent-ignore pattern used elsewhere in this component (see handleArchive
          // callers under CloudApp).
        }
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof UnauthorizedError) {
          router.replace('/login');
          return;
        }
        setError(err instanceof Error ? err.message : 'Failed to load playlists.');
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  // backlog #37: refetch when the parent signals that IT changed the list (today: a completed
  // ingest). Measured against prod v6 on 2026-08-12 — 3 playlists in the database, 1 in the
  // sidebar, and a hard reload showed all 3.
  //
  // Why the parent has to tell us. This component is a SIBLING of the content pane inside
  // `CloudAppBody`, and is never keyed by playlistId — so `router.push('/?playlist=<new>')` after
  // an ingest reconciles it rather than remounting it. The mount effect above is keyed on
  // [userId], which is stable for the whole signed-in session. Nothing observable from in here
  // distinguishes "a playlist was just created" from any other re-render.
  //
  // Deliberately a SEPARATE effect from the [userId] one rather than another dependency on it:
  // that effect also owns the once-per-session title backfill and resets `backfillFiredRef` as
  // its first act, so folding the refetch in would re-arm the one-shot on every ingest. Two
  // concerns, two effects.
  //
  // Skip while refreshKey still holds the value it had on the FIRST render — that is the initial
  // render, which the mount effect already owns. `useRef(refreshKey)` captures that value once and
  // ignores the argument on every later render, so this works no matter what number the parent
  // starts its counter at (round 1, Low: the old `refreshKey === 0` sentinel silently required 0).
  //
  // It is also the reason this is a VALUE comparison and not a "have I run before?" flag. A run
  // counter is not StrictMode-safe: React 18 runs effects setup→cleanup→setup on mount, so the
  // first setup would consume the flag and the SECOND would fetch on mount anyway — dev-only, but
  // it would make the stated contract false, and it could fire the null-title backfill below
  // outside its intended trigger. Comparing values makes both setups skip (round 2, Low).
  const initialRefreshKeyRef = useRef(refreshKey);
  useEffect(() => {
    if (refreshKey === initialRefreshKeyRef.current) return;
    let cancelled = false;
    (async () => {
      const result = await loadPlaylists(() => cancelled);
      if (cancelled || result === null) return;

      // A brand-new playlist can legitimately arrive with NO title: producer.ts deliberately leaves
      // the row untitled when the YouTube title fetch misses or throws, on the stated expectation
      // that "the backfill route retries later". Before this branch that row was invisible, so the
      // gap never showed. Now it renders as "Untitled playlist" — and the mount effect's backfill is
      // once-per-session, already spent, so nothing in-session would repair it (review, Medium).
      //
      // So the refresh path runs its own repair. It intentionally does NOT consult (or set) the
      // once-per-session sessionStorage key: that key throttles the unsolicited sign-in sweep, while
      // this is a bounded response to a specific new row the user just created. It stays bounded
      // because the effect runs exactly once per refreshKey increment, i.e. once per ingest.
      if (userId === null || !result.some((p) => !p.playlistTitle)) return;
      try {
        await backfillPlaylistTitles();
        if (!cancelled) await loadPlaylists(() => cancelled);
      } catch {
        // best-effort: an untitled row still renders and is still reachable.
      }
    })().catch(() => {
      // Round 3 (High) — do NOT swallow this. Keeping the last good list on screen is right; doing
      // it SILENTLY is the "quietly serves stale data" failure this project treats as the worst
      // kind. The user just created a playlist: a sidebar that omits it with no explanation is
      // indistinguishable from the bug this branch fixes.
      //
      // This is also where rounds 2 and 3 appeared to contradict each other. Round 2: a newer
      // FAILED load must not discard an older successful one, or the sidebar strands on a spinner
      // holding good data. Round 3: applying that older result shows pre-ingest data with no sign
      // anything went wrong. Both hold, and they only conflicted because the render treated "show a
      // list" and "show an error" as mutually exclusive. They are not — see the render below, which
      // now shows the banner ABOVE whatever list we have.
      if (!cancelled) setError('Could not refresh the playlist list — it may be out of date.');
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  // T10: called from DeletePlaylistDialog.onDeleted. Refetches the list and, if the
  // deleted playlist was the active one, navigates to `/` (no `?playlist=` param) since
  // its video pane would otherwise 404/empty against a now-gone playlist.
  async function handleDeleted(deletedId: string) {
    setDeleteTarget(null);
    try {
      // No cancellation argument: this runs from an event handler, not an effect, so there is no
      // teardown to observe. It still shares the sequence guard, so a slow earlier load cannot
      // resurrect the deleted row.
      await loadPlaylists();
    } catch {
      // best-effort refetch — matches the silent-ignore pattern used by the backfill path
      // above; the row is gone server-side regardless of whether this refetch succeeds.
    }
    if (deletedId === activePlaylistId) {
      router.push('/');
    }
  }

  return (
    <nav
      aria-label="Playlists"
      className="w-56 shrink-0 border-r border-[var(--border)] bg-[var(--surface-raised)] p-3"
    >
      <h2 className="mb-2 px-2 text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
        Playlists
      </h2>

      {/* The banner sits ABOVE the list rather than replacing it (round 3). A failed refresh still
          leaves the last good list worth showing; what it must not do is show it silently. Only the
          "Loading…" placeholder is suppressed by an error, because a load that failed is not still
          in progress. */}
      {error && <p className="px-2 text-sm text-[var(--danger)]">{error}</p>}

      {!error && playlists === null && (
        <p className="px-2 text-sm text-[var(--text-muted)]">Loading playlists…</p>
      )}

      {playlists !== null && playlists.length === 0 && (
        <div className="px-2 text-sm text-[var(--text-secondary)]">
          <p>You have no playlists yet.</p>
          <p className="mt-1 text-[var(--text-muted)]">Adding playlists comes with ingest.</p>
        </div>
      )}

      {playlists !== null && playlists.length > 0 && (
        <ul className="space-y-1">
          {playlists.map((p) => {
            const isActive = p.id === activePlaylistId;
            const displayTitle = p.playlistTitle ?? 'Untitled playlist';
            return (
              <li key={p.id} className="group relative">
                <Link
                  href={`/?playlist=${p.id}`}
                  aria-current={isActive ? 'page' : undefined}
                  className={isActive ? activeLinkClass : inactiveLinkClass}
                >
                  {displayTitle}
                </Link>
                <button
                  type="button"
                  aria-label={`Delete playlist ${displayTitle}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    setDeleteTarget(p);
                  }}
                  className="absolute right-1 top-1/2 -translate-y-1/2 rounded px-1.5 py-1 text-[var(--text-muted)] opacity-0 hover:text-[var(--danger)] focus:opacity-100 group-hover:opacity-100 group-focus-within:opacity-100"
                >
                  🗑
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <button
        type="button"
        onClick={onNewPlaylist}
        className="mt-3 w-full rounded border border-[var(--border)] px-2 py-1.5 text-left text-sm text-[var(--text-primary)] hover:bg-[var(--surface-overlay)]"
      >
        + New playlist
      </button>

      {deleteTarget && (
        <DeletePlaylistDialog
          playlistId={deleteTarget.id}
          playlistTitle={deleteTarget.playlistTitle ?? 'Untitled playlist'}
          onClose={() => setDeleteTarget(null)}
          onDeleted={() => handleDeleted(deleteTarget.id)}
        />
      )}
    </nav>
  );
}
