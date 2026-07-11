// Scope-aware browser fetch helpers (Stage 2a, Task 10). Every function here builds a URL/body
// matching the exact contract of the corresponding app/api route (Tasks 4-8) for whichever
// backend the current Scope selects. No server-only imports — this module runs in the browser.
import type { PlaylistSummary } from '@/lib/storage/metadata-store';
import type { Scope } from '@/lib/client/scope';
import type { SortColumn, SortOrder, Video } from '@/types';

export class UnauthorizedError extends Error {}

/** Shared response handling for every helper below: 401 -> UnauthorizedError (so callers /
 *  CloudApp can redirect to /login); other non-2xx -> Error using the response's {error}
 *  message when present; otherwise parse and return the JSON body. */
async function handle<T>(res: Response): Promise<T> {
  if (res.status === 401) {
    throw new UnauthorizedError('unauthorized');
  }
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { error?: string } | null;
    throw new Error(body?.error ?? `request failed with status ${res.status}`);
  }
  return res.json() as Promise<T>;
}

/** Builds the scope query param (`playlist=<uuid>` for cloud, `outputFolder=<path>` for local)
 *  onto `params`. Throws BEFORE any fetch happens if the scope is missing its required field —
 *  a cloud scope with no playlistId, or a local scope with no outputFolder. */
function addScopeParam(params: URLSearchParams, scope: Scope): void {
  if (scope.mode === 'cloud') {
    if (!scope.playlistId) {
      throw new Error('cloud scope requires a playlistId');
    }
    params.set('playlist', scope.playlistId);
  } else {
    if (!scope.outputFolder) {
      throw new Error('local scope requires an outputFolder');
    }
    params.set('outputFolder', scope.outputFolder);
  }
}

export async function listPlaylists(): Promise<PlaylistSummary[]> {
  const res = await fetch('/api/playlists');
  const data = await handle<{ playlists: PlaylistSummary[] }>(res);
  return data.playlists;
}

export interface VideoListResult {
  videos: Video[];
  playlistUrl: string;
  playlistTitle: string | null;
}

export async function listVideos(
  scope: Scope,
  sort?: { column: SortColumn; order: SortOrder },
): Promise<VideoListResult> {
  const params = new URLSearchParams();
  addScopeParam(params, scope); // throws before fetch on wrong/missing scope
  if (sort) {
    params.set('sortColumn', sort.column);
    params.set('sortOrder', sort.order);
  }
  const res = await fetch(`/api/videos?${params}`);
  return handle<VideoListResult>(res);
}

export interface QuickView {
  tldr: string;
  takeaways: string[];
  tags: string[];
}

export async function getQuickView(scope: Scope, videoId: string): Promise<QuickView> {
  const params = new URLSearchParams();
  addScopeParam(params, scope); // throws before fetch on wrong/missing scope
  const res = await fetch(`/api/videos/${encodeURIComponent(videoId)}/quick-view?${params}`);
  return handle<QuickView>(res);
}

export interface AnnotationPatch {
  personalScore?: number | null;
  personalNote?: string;
}

export async function saveAnnotation(scope: Scope, videoId: string, patch: AnnotationPatch): Promise<void> {
  let url: string;
  let body: Record<string, unknown>;
  if (scope.mode === 'cloud') {
    if (!scope.playlistId) throw new Error('cloud scope requires a playlistId'); // before fetch
    url = `/api/videos/${encodeURIComponent(videoId)}/review?playlist=${encodeURIComponent(scope.playlistId)}`;
    body = { ...patch };
  } else {
    if (!scope.outputFolder) throw new Error('local scope requires an outputFolder'); // before fetch
    url = `/api/videos/${encodeURIComponent(videoId)}/review`;
    body = { outputFolder: scope.outputFolder, ...patch };
  }
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  await handle<{ ok: true }>(res);
}

export async function setArchived(scope: Scope, videoId: string, archived: boolean): Promise<void> {
  const action = archived ? 'archive' : 'unarchive';
  let url: string;
  let body: Record<string, unknown>;
  if (scope.mode === 'cloud') {
    if (!scope.playlistId) throw new Error('cloud scope requires a playlistId'); // before fetch
    url = `/api/videos/${encodeURIComponent(videoId)}/archive?playlist=${encodeURIComponent(scope.playlistId)}`;
    body = { action };
  } else {
    if (!scope.outputFolder) throw new Error('local scope requires an outputFolder'); // before fetch
    url = `/api/videos/${encodeURIComponent(videoId)}/archive`;
    body = { outputFolder: scope.outputFolder, action };
  }
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  await handle<{ ok: true }>(res);
}
