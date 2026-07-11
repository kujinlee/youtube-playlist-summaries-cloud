'use client';

/**
 * Stage 2a T15b: cloud shell full wiring. `app/page.tsx` renders this in cloud mode
 * (`STORAGE_BACKEND=supabase`) with the RSC-read session.
 *
 * `CloudAppBody` reads `?playlist` via `useSearchParams()`, which requires a Suspense
 * boundary in Next.js — `PlaylistSidebar` reads it too, so both live inside the one
 * boundary here rather than each wrapping itself.
 *
 * When `?playlist` is present, `PlaylistLibrary` builds a memoized cloud `Scope`
 * (`{ mode: 'cloud', playlistId }`, memoized on `playlistId` per T15a's guidance — an
 * unmemoized literal would re-fire VideoQuickView's effect on every render) and mounts a
 * `ScopeProvider` around the main pane so the shared leaves (StarRating/NoteCell/
 * VideoQuickView/VideoMenu) resolve their own scope-aware requests.
 */
import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import type { FilterState, SortColumn, SortOrder, Video } from '@/types';
import { FILTER_DEFAULTS } from '@/types';
import AccountMenu from './AccountMenu';
import PlaylistSidebar from './PlaylistSidebar';
import FilterBar from '@/components/FilterBar';
import VideoList from '@/components/VideoList';
import { ScopeProvider, type Scope } from '@/lib/client/scope';
import { listVideos, setArchived, UnauthorizedError } from '@/lib/client/api';

export interface CloudAppProps {
  session: { userId: string; email: string } | null;
}

export default function CloudApp({ session }: CloudAppProps) {
  return (
    <main className="min-h-screen bg-[var(--surface-base)] text-[var(--text-primary)]">
      <header className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)] bg-[var(--surface-raised)]">
        <h1 className="text-lg font-semibold">YouTube Playlist Summaries</h1>
        {session ? (
          <AccountMenu email={session.email} />
        ) : (
          <span className="text-sm text-[var(--text-secondary)]">Not signed in</span>
        )}
      </header>

      <Suspense
        fallback={
          <div className="px-6 py-12 text-center text-[var(--text-muted)]">Loading…</div>
        }
      >
        <CloudAppBody />
      </Suspense>
    </main>
  );
}

function CloudAppBody() {
  const searchParams = useSearchParams();
  const playlistId = searchParams.get('playlist');

  return (
    <div className="flex">
      <PlaylistSidebar />
      {playlistId ? (
        <PlaylistLibrary playlistId={playlistId} />
      ) : (
        <section
          aria-label="Cloud library"
          className="flex-1 px-6 py-12 text-center text-[var(--text-muted)]"
        >
          <p>Pick a playlist from the sidebar to view its videos.</p>
        </section>
      )}
    </div>
  );
}

function PlaylistLibrary({ playlistId }: { playlistId: string }) {
  const router = useRouter();
  // Memoized so StarRating/NoteCell/VideoQuickView (mounted under the ScopeProvider below)
  // don't see a new scope identity — and re-run their fetch effects — on every render.
  const cloudScope: Scope = useMemo(() => ({ mode: 'cloud', playlistId }), [playlistId]);

  const [videos, setVideos] = useState<Video[] | null>(null); // null = loading
  const [error, setError] = useState<string | null>(null);
  const [sortColumn, setSortColumn] = useState<SortColumn | null>(null);
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
  const [showArchive, setShowArchive] = useState(false);
  const [filters, setFilters] = useState<FilterState>(FILTER_DEFAULTS);

  const fetchVideos = useCallback(
    async (col: SortColumn | null, order: SortOrder) => {
      try {
        const result = await listVideos(cloudScope, col ? { column: col, order } : undefined);
        setVideos(result.videos);
        setError(null);
      } catch (err) {
        if (err instanceof UnauthorizedError) {
          router.replace('/login');
          return;
        }
        setError(err instanceof Error ? err.message : 'Failed to load videos.');
      }
    },
    [cloudScope, router],
  );

  // Fetch on mount and whenever the selected playlist changes. Sort re-fetches are triggered
  // explicitly by handleSort (mirrors LocalApp's fetchVideos/handleSort split) so this effect
  // doesn't also fire on every sort change.
  useEffect(() => {
    setVideos(null);
    setError(null);
    fetchVideos(null, 'asc');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cloudScope]);

  const handleSort = useCallback(
    (col: SortColumn, order: SortOrder) => {
      setSortColumn(col);
      setSortOrder(order);
      fetchVideos(col, order);
    },
    [fetchVideos],
  );

  const handleArchive = useCallback(
    async (videoId: string, action: 'archive' | 'unarchive') => {
      try {
        await setArchived(cloudScope, videoId, action === 'archive');
        setVideos((prev) =>
          prev ? prev.map((v) => (v.id === videoId ? { ...v, archived: action === 'archive' } : v)) : prev,
        );
      } catch (err) {
        if (err instanceof UnauthorizedError) {
          router.replace('/login');
          return;
        }
        // best-effort — leave the row as-is on failure (mirrors LocalApp's silent-ignore pattern)
      }
    },
    [cloudScope, router],
  );

  const handleAnnotationChange = useCallback(
    (videoId: string, patch: Partial<Pick<Video, 'personalScore' | 'personalNote'>>) => {
      // The save already happened inside StarRating/NoteCell via apiClient — this callback
      // only syncs this component's copy of the video list.
      setVideos((prev) => (prev ? prev.map((v) => (v.id === videoId ? { ...v, ...patch } : v)) : prev));
    },
    [],
  );

  const handleFilterChange = useCallback((patch: Partial<FilterState>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
  }, []);

  // Doc-generation is out of scope for 2a — no-ops (VideoMenu already hides these items in
  // cloud mode; VideoList/VideoRow still require the callback props).
  const noop = useCallback(() => {}, []);

  const filteredVideos = (videos ?? [])
    .filter((v) => showArchive || !v.archived)
    .filter(
      (v) =>
        !filters.searchText ||
        v.title.toLowerCase().includes(filters.searchText.toLowerCase()) ||
        (v.channel ?? '').toLowerCase().includes(filters.searchText.toLowerCase()),
    )
    .filter((v) => filters.language === 'all' || v.language === filters.language)
    .filter((v) => filters.videoType === 'all' || v.videoType === filters.videoType)
    .filter((v) => filters.audience === 'all' || v.audience === filters.audience)
    .filter((v) => v.overallScore >= filters.minScore)
    .filter((v) => {
      if (filters.minPersonalScore === 0) return true;
      if (v.personalScore === undefined) return true; // unscored: shown dimmed, not hidden
      return v.personalScore >= filters.minPersonalScore;
    });

  return (
    <ScopeProvider scope={cloudScope}>
      <section aria-label="Cloud library" className="flex-1 px-6 py-6">
        {error && (
          <p role="alert" className="mb-4 text-sm text-[var(--danger)]">
            {error}
          </p>
        )}

        {videos === null && !error && (
          <p className="py-12 text-center text-[var(--text-muted)]">Loading videos…</p>
        )}

        {videos !== null && videos.length === 0 && (
          <div className="py-12 text-center text-[var(--text-muted)]">
            <p>No videos here yet.</p>
            <p className="mt-1 text-sm">Ingestion may still be running.</p>
          </div>
        )}

        {videos !== null && videos.length > 0 && (
          <>
            <div className="flex items-center justify-between pb-2 mb-4 border-b border-[var(--border)]">
              <FilterBar filters={filters} onChange={handleFilterChange} />
              <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)] cursor-pointer ml-4">
                <input
                  type="checkbox"
                  checked={showArchive}
                  onChange={(e) => setShowArchive(e.target.checked)}
                  className="rounded border-[var(--border-strong)] bg-[var(--surface-overlay)] text-[var(--accent)] focus:ring-[var(--accent)]"
                />
                Show Archive
              </label>
            </div>
            <VideoList
              videos={filteredVideos}
              showArchive={true}
              onArchive={handleArchive}
              onGenerateHtml={noop}
              onResummarize={noop}
              onSavePdf={noop}
              sortColumn={sortColumn}
              sortOrder={sortOrder}
              onSort={handleSort}
              minPersonalScore={filters.minPersonalScore}
              onAnnotationChange={handleAnnotationChange}
            />
          </>
        )}
      </section>
    </ScopeProvider>
  );
}
