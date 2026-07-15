// Scope-aware browser fetch helpers (Stage 2a, Task 10). Every function here builds a URL/body
// matching the exact contract of the corresponding app/api route (Tasks 4-8) for whichever
// backend the current Scope selects. No server-only imports — this module runs in the browser.
import type { PlaylistSummary } from '@/lib/storage/metadata-store';
import type { Scope } from '@/lib/client/scope';
import type { SortColumn, SortOrder, Video } from '@/types';
import type { ProducerCounts, JobFanoutResult } from '@/lib/job-queue/producer';
import type { PlaylistJobRow } from '@/lib/storage/job-queue';
import type { Rollup } from '@/lib/job-queue/poll-client';

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

/** Bounded, owner-scoped backfill for playlists missing a real YouTube title (BUG-6).
 *  Invoked by PlaylistSidebar's auto-backfill trigger — see app/api/playlists/backfill-titles. */
export async function backfillPlaylistTitles(): Promise<{ updated: number; attempted: number }> {
  const res = await fetch('/api/playlists/backfill-titles', { method: 'POST' });
  return handle<{ updated: number; attempted: number }>(res);
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

export interface IngestResult {
  playlistId: string | null;
  jobs: JobFanoutResult[];
  counts: ProducerCounts;
  challengeRequired: boolean;
  dailyCapReached?: boolean;
}

export class IngestError extends Error {
  constructor(
    readonly status: number,
    readonly info: { retryAfterSeconds?: number; limit?: number; found?: number } = {},
  ) {
    super(`ingest failed (${status})`);
    this.name = 'IngestError';
  }
}

export function ingestErrorMessage(err: IngestError): string {
  switch (err.status) {
    case 400: return 'Enter a valid YouTube playlist URL.';
    case 403: return "This account can't ingest right now.";
    case 422:
      return typeof err.info.found === 'number' && typeof err.info.limit === 'number'
        ? `That playlist has ${err.info.found} videos; the limit is ${err.info.limit}. Try a smaller one.`
        : 'That playlist is too large. Try a smaller one.';
    case 429: return `You're adding playlists too quickly — try again in ${err.info.retryAfterSeconds}s.`;
    case 502: return "Couldn't reach YouTube for that playlist. Try again.";
    case 503: return 'The service is at capacity. Try again shortly.';
    default:  return 'Something went wrong. Try again.';
  }
}

export async function createIngest(playlistUrl: string): Promise<IngestResult> {
  const res = await fetch('/api/jobs', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ playlistUrl }),
  });
  if (res.status === 401) throw new UnauthorizedError('unauthorized');
  if (!res.ok) {
    const raw = await res.json().catch(() => null);
    const body: Record<string, unknown> = raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : {};
    const info: { retryAfterSeconds?: number; limit?: number; found?: number } = {};
    if (res.status === 429) {
      const h = res.headers.get('retry-after');
      const n = Number(h);
      info.retryAfterSeconds = h && Number.isFinite(n) && n >= 1 ? n : 60;
    }
    if (res.status === 422) {
      if (typeof body.limit === 'number') info.limit = body.limit;
      if (typeof body.found === 'number') info.found = body.found;
    }
    throw new IngestError(res.status, info);
  }
  return res.json();
}

export async function getJobStatus(
  playlistId: string,
): Promise<{ jobs: PlaylistJobRow[]; rollup: Rollup }> {
  const res = await fetch(`/api/jobs?playlistId=${encodeURIComponent(playlistId)}`);
  return handle(res);
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

/** Builds the serveCloud summary-doc URL. View = no opts; downloads set format + download=1. */
export function summaryHref(
  playlistId: string,
  videoId: string,
  opts?: { format?: 'md' | 'html'; download?: boolean },
): string {
  const params = new URLSearchParams();
  params.set('playlist', playlistId);
  params.set('type', 'summary');
  if (opts?.format) params.set('format', opts.format);
  if (opts?.download) params.set('download', '1');
  return `/api/html/${encodeURIComponent(videoId)}?${params.toString()}`;
}

/** Builds the serveCloud PDF URL. */
export function pdfHref(playlistId: string, videoId: string): string {
  const p = new URLSearchParams({ playlist: playlistId, type: 'summary' });
  return `/api/pdf/${encodeURIComponent(videoId)}?${p.toString()}`;
}

/** Builds the serveCloud dig-deeper-doc URL (interactive per-section digging). Mirrors summaryHref/pdfHref. */
export function digHref(playlistId: string, videoId: string): string {
  const params = new URLSearchParams();
  params.set('playlist', playlistId);
  params.set('type', 'dig-deeper');
  return `/api/html/${encodeURIComponent(videoId)}?${params.toString()}`;
}

export type ShareTtl = 7 | 30 | 'never';

export interface CreateShareResult {
  id: string;
  token: string;
  url: string;                 // path only: '/s/<token>' — caller prefixes window.location.origin
  expiresAt: string | null;
}

export async function createShare(
  playlistId: string,
  videoId: string,
  ttl: ShareTtl,
): Promise<CreateShareResult> {
  const res = await fetch('/api/share', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ playlistId, videoId, ttlDays: ttl }),
  });
  return handle<CreateShareResult>(res);
}

export async function revokeShare(shareId: string): Promise<{ revoked: boolean }> {
  const res = await fetch(`/api/share/${encodeURIComponent(shareId)}/revoke`, { method: 'POST' });
  return handle<{ revoked: boolean }>(res);
}

/** Full hard-delete of a cloud playlist (Task 9). A 404 means the playlist is already gone
 *  (this call, or a concurrent one, already deleted it) — treated as success, not an error,
 *  so a double-click or a stale UI doesn't surface a spurious failure. */
export async function deletePlaylist(id: string): Promise<void> {
  const res = await fetch(`/api/playlists/${encodeURIComponent(id)}`, { method: 'DELETE' });
  if (res.status === 404) return;
  if (res.status === 401) throw new UnauthorizedError('unauthorized');
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { error?: string } | null;
    throw new Error(body?.error ?? `request failed with status ${res.status}`);
  }
}
