'use client';

/**
 * Stage 2a T13: cloud library sidebar. Fetches the signed-in owner's playlists via the
 * scope-aware api client (lib/client/api.ts — `listPlaylists()` needs no scope argument;
 * the owner is resolved server-side from the session) and renders one nav item per
 * playlist, linking to `/?playlist=<uuid>` (spec §9 URL Contracts). The active item is
 * derived from the current `?playlist` query param via `useSearchParams()`.
 *
 * "+ New playlist" is a deliberately inert affordance — ingest ships in Stage 2b. It must
 * never navigate or issue a request; `disabled` on a native `<button>` guarantees both.
 *
 * Not wrapped in useScope()/ScopeProvider: that wiring lands in T15 alongside CloudApp's
 * full library view. This component only needs the (unscoped) playlist list + the URL.
 */
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { listPlaylists } from '@/lib/client/api';
import type { PlaylistSummary } from '@/lib/storage/metadata-store';

const activeLinkClass =
  'block truncate rounded-r px-2 py-1.5 border-l-2 border-[var(--accent)] bg-[var(--surface-overlay)] text-[var(--text-primary)]';
const inactiveLinkClass =
  'block truncate rounded-r px-2 py-1.5 border-l-2 border-transparent text-[var(--text-secondary)] hover:bg-[var(--surface-overlay)] hover:text-[var(--text-primary)]';

export default function PlaylistSidebar() {
  const searchParams = useSearchParams();
  const activePlaylistId = searchParams.get('playlist');

  const [playlists, setPlaylists] = useState<PlaylistSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listPlaylists()
      .then((result) => {
        if (!cancelled) setPlaylists(result);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load playlists.');
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

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
            return (
              <li key={p.id}>
                <Link
                  href={`/?playlist=${p.id}`}
                  aria-current={isActive ? 'page' : undefined}
                  className={isActive ? activeLinkClass : inactiveLinkClass}
                >
                  {p.playlistTitle ?? 'Untitled playlist'}
                </Link>
              </li>
            );
          })}
        </ul>
      )}

      <button
        type="button"
        disabled
        title="Adding playlists comes with ingest"
        className="mt-3 w-full cursor-not-allowed rounded border border-[var(--border)] px-2 py-1.5 text-left text-sm text-[var(--text-muted)]"
      >
        + New playlist
      </button>
    </nav>
  );
}
