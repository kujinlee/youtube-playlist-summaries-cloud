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

  // ONE monotonic sequence shared by every path that loads the list — the [userId] mount effect,
  // the [refreshKey] ingest refetch, the post-backfill reload, and handleDeleted.
  //
  // Per-effect `cancelled` booleans are NOT enough, and the first version of this branch used them.
  // Each flag only knows about its own effect, so a slow mount fetch could resolve AFTER a fast
  // post-ingest refetch and overwrite the new playlist with the pre-ingest list — restoring the very
  // bug this branch removes. Reachable in practice because "+ New playlist" renders while the list
  // is still loading, so an ingest can start and finish before a slow initial fetch returns.
  // Found by adversarial review (High, docs/reviews/backlog-37-sidebar-refresh-codex.md).
  //
  // This is the same guard `PlaylistLibrary` already applies to listVideos (CloudApp.tsx `reqSeq`),
  // for the identical reason. The `cancelled` flags stay: sequence answers "was I superseded?",
  // cancelled answers "did my effect tear down?" — different questions, both worth asking.
  // TWO counters, because "newest started" and "newest applied" are different questions and they
  // diverge precisely when a load FAILS. Round 2 of review found both halves of that gap (High):
  //   • guarding only successes let a stale REJECTION still raise `error` — or redirect to /login —
  //     over a list a newer load had already rendered correctly;
  //   • guarding against "newest started" meant a newer load that FAILED permanently discarded an
  //     older in-flight load that then succeeded, stranding the sidebar on "Loading playlists…"
  //     while holding a perfectly good result.
  // What governs the screen is the newest load that actually APPLIED something.
  const startedSeqRef = useRef(0);
  const appliedSeqRef = useRef(0);

  /** Fetch the list and apply it only if no NEWER load has already applied one. Returns the list
   *  when applied, or null when this load no longer speaks for the screen — callers must read null
   *  as "do nothing further", never as "the owner has no playlists".
   *
   *  Rejections propagate to the caller ONLY while this is still the newest load in flight; a stale
   *  rejection resolves to null instead, because a load that has been overtaken has no standing to
   *  put an error on screen. */
  async function loadPlaylists(): Promise<PlaylistSummary[] | null> {
    const seq = ++startedSeqRef.current;
    try {
      const result = await listPlaylists();
      if (seq <= appliedSeqRef.current) return null;
      appliedSeqRef.current = seq;
      setPlaylists(result);
      return result;
    } catch (err) {
      if (seq !== startedSeqRef.current) return null; // overtaken — stay silent
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
    loadPlaylists()
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
          await loadPlaylists();
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
      const result = await loadPlaylists();
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
        if (!cancelled) await loadPlaylists();
      } catch {
        // best-effort: an untitled row still renders and is still reachable.
      }
    })().catch(() => {
      // best-effort, matching handleDeleted below: the row exists server-side either way, and a
      // failed refetch should leave the last good list on screen rather than blanking it.
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
      await loadPlaylists(); // shares the sequence guard, so a slow earlier load cannot resurrect the row
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

      {error && <p className="px-2 text-sm text-[var(--danger)]">{error}</p>}

      {!error && playlists === null && (
        <p className="px-2 text-sm text-[var(--text-muted)]">Loading playlists…</p>
      )}

      {!error && playlists !== null && playlists.length === 0 && (
        <div className="px-2 text-sm text-[var(--text-secondary)]">
          <p>You have no playlists yet.</p>
          <p className="mt-1 text-[var(--text-muted)]">Adding playlists comes with ingest.</p>
        </div>
      )}

      {!error && playlists !== null && playlists.length > 0 && (
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
