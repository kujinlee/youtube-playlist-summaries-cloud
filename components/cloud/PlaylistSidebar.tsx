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
}

export default function PlaylistSidebar({ onNewPlaylist, userId }: PlaylistSidebarProps) {
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
    listPlaylists()
      .then(async (result) => {
        if (cancelled) return;
        setPlaylists(result);

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
          const refreshed = await listPlaylists();
          if (!cancelled) setPlaylists(refreshed);
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

  // T10: called from DeletePlaylistDialog.onDeleted. Refetches the list and, if the
  // deleted playlist was the active one, navigates to `/` (no `?playlist=` param) since
  // its video pane would otherwise 404/empty against a now-gone playlist.
  async function handleDeleted(deletedId: string) {
    setDeleteTarget(null);
    try {
      const refreshed = await listPlaylists();
      setPlaylists(refreshed);
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
