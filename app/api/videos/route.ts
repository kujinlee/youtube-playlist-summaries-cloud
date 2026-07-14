import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getPrincipal, getStorageBundle, getPrincipalFromSession } from '../../../lib/storage/resolve';
import { recoverOrphanedVideos } from '../../../lib/pipeline';
import { createServerSupabase, type CookieStore } from '../../../lib/supabase/server';
import { resolveOwnedPlaylistKey } from '../../../lib/storage/serve-playlist';
import type { SortColumn, SortOrder, Video } from '../../../types';
import { logError } from '../../../lib/dev-logger';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const AUDIENCE_ORDER: Record<string, number> = { Beginner: 1, Intermediate: 2, Advanced: 3 };

// Accepted values for the `sortColumn` query param. Keep in sync with the SortColumn
// union in types/index.ts (the literal types here are compile-time-checked against it).
// An unrecognized value (e.g. a stale `playlistIndex` from an old bookmark) falls back
// to 'name' instead of silently producing an unsorted list.
const SORT_COLUMNS = new Set<SortColumn>([
  'name', 'overall', 'usefulness', 'depth', 'originality', 'recency', 'completeness',
  'language', 'videoType', 'audience', 'serialNumber', 'videoPublishedAt', 'addedToPlaylistAt', 'personalScore',
  'channel', 'durationSeconds',
]);

function sortVideos(videos: Video[], column: SortColumn, order: SortOrder): Video[] {
  const sorted = [...videos].sort((a, b) => {
    let aVal: string | number | undefined;
    let bVal: string | number | undefined;
    if (column === 'name') {
      aVal = a.title?.toLowerCase();
      bVal = b.title?.toLowerCase();
    } else if (column === 'overall') {
      aVal = a.overallScore;
      bVal = b.overallScore;
    } else if (column === 'language') {
      // Preserve undefined (don't coalesce to '') so an incomplete row sorts LAST via the
      // shared nulls-last tail, not first — uniform with every other column.
      aVal = a.language;
      bVal = b.language;
    } else if (column === 'videoType') {
      aVal = a.videoType;
      bVal = b.videoType;
    } else if (column === 'audience') {
      // Absent audience (== null catches undefined/null) → undefined (sorts last, consistent with
      // the shared tail); present-but-unrecognized → rank 0 (as before).
      aVal = a.audience == null ? undefined : (AUDIENCE_ORDER[a.audience] ?? 0);
      bVal = b.audience == null ? undefined : (AUDIENCE_ORDER[b.audience] ?? 0);
    } else if (column === 'serialNumber') {
      // Videos with no summary yet have no serial — always sort them last, regardless of direction.
      if (a.serialNumber === undefined && b.serialNumber === undefined) return 0;
      if (a.serialNumber === undefined) return 1;
      if (b.serialNumber === undefined) return -1;
      const cmp = a.serialNumber - b.serialNumber;
      return order === 'asc' ? cmp : -cmp;
    } else if (column === 'videoPublishedAt' || column === 'addedToPlaylistAt') {
      const aDate = a[column];
      const bDate = b[column];
      if (!aDate && !bDate) return 0;
      if (!aDate) return 1;  // nulls always to bottom
      if (!bDate) return -1;
      const cmp = aDate.localeCompare(bDate);
      return order === 'asc' ? cmp : -cmp;
    } else if (column === 'personalScore') {
      // Unscored videos (undefined) always sort last, regardless of direction
      if (a.personalScore === undefined && b.personalScore === undefined) return 0;
      if (a.personalScore === undefined) return 1;
      if (b.personalScore === undefined) return -1;
      const cmp = a.personalScore - b.personalScore;
      return order === 'asc' ? cmp : -cmp;
    } else if (column === 'channel') {
      // Optional field — videos with no channel always sort to the bottom, regardless of direction.
      const aCh = a.channel ?? '';
      const bCh = b.channel ?? '';
      if (!aCh && !bCh) return 0;
      if (!aCh) return 1;
      if (!bCh) return -1;
      const cmp = aCh.localeCompare(bCh);
      return order === 'asc' ? cmp : -cmp;
    } else if (column === 'durationSeconds') {
      aVal = a.durationSeconds;
      bVal = b.durationSeconds;
    } else {
      aVal = a.ratings?.[column as keyof typeof a.ratings];
      bVal = b.ratings?.[column as keyof typeof b.ratings];
    }
    // Incomplete rows (a reserved slot whose summary hasn't landed, so this sort key
    // is absent) sort LAST regardless of direction — never dereference undefined and
    // 500 the whole list. Mirrors the nulls-last handling for channel/personalScore.
    if (aVal == null || bVal == null) {   // == null catches undefined (and any jsonb null)
      if (aVal == null && bVal == null) return 0;
      return aVal == null ? 1 : -1;       // the missing one sorts last, both directions
    }
    if (aVal < bVal) return order === 'asc' ? -1 : 1;
    if (aVal > bVal) return order === 'asc' ? 1 : -1;
    return 0;
  });
  return sorted;
}

export async function GET(request: Request) {
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'supabase') return serveCloud(request);
  return serveLocal(request);
}

// ---- LOCAL path — preserved verbatim (pre-2a Task 5 behavior, filesystem-backed) ----
async function serveLocal(request: Request): Promise<Response> {
  const { searchParams } = new URL(request.url);
  const outputFolder = searchParams.get('outputFolder');
  if (!outputFolder) {
    return NextResponse.json({ error: 'outputFolder is required' }, { status: 400 });
  }

  let principal;
  try {
    principal = getPrincipal(outputFolder);
  } catch {
    return NextResponse.json({ error: 'invalid outputFolder' }, { status: 400 });
  }

  // Best-effort: recover orphaned MD files.
  try { await recoverOrphanedVideos(outputFolder); } catch { /* non-fatal */ }

  const rawSortColumn = searchParams.get('sortColumn');
  const sortColumn: SortColumn =
    rawSortColumn && SORT_COLUMNS.has(rawSortColumn as SortColumn) ? (rawSortColumn as SortColumn) : 'name';
  const sortOrder = (searchParams.get('sortOrder') ?? 'asc') as SortOrder;

  let index;
  try {
    index = await getStorageBundle().metadataStore.readIndex(principal);
  } catch (err) {
    const e = err as { statusCode?: number; message?: string };
    if (e.statusCode === 400) {
      return NextResponse.json({ error: e.message }, { status: 400 });
    }
    logError('videos:readIndex', err);   // never swallow: log the real cause before Next returns a bare 500
    throw err;
  }
  const videos = sortVideos(index.videos, sortColumn, sortOrder);
  return NextResponse.json({ videos, playlistUrl: index.playlistUrl, playlistTitle: index.playlistTitle });
}

// ---- CLOUD path (Stage 2a Task 5) — session-scoped Supabase, owner-asserted via
// resolveOwnedPlaylistKey + RLS. Mirrors the app/api/html/[id]/route.ts serveCloud flow:
// createServerSupabase → getUser → UUID guard → resolveOwnedPlaylistKey → getPrincipalFromSession
// → getStorageBundle({supabaseClient}). Does NOT call recoverOrphanedVideos (filesystem-only).
async function serveCloud(request: Request): Promise<Response> {
  const { searchParams } = new URL(request.url);

  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'authentication required' }, { status: 401 });

  const playlistId = searchParams.get('playlist');
  if (!playlistId || !UUID_RE.test(playlistId)) {
    return NextResponse.json({ error: 'invalid playlist' }, { status: 400 }); // before any DB call
  }

  if (searchParams.get('outputFolder')) {
    return NextResponse.json({ error: 'outputFolder not valid on this backend' }, { status: 400 });
  }

  const playlistKey = await resolveOwnedPlaylistKey(supabase, playlistId, user.id); // owner-asserted (D6/D9)
  if (!playlistKey) return NextResponse.json({ error: 'not found' }, { status: 404 });

  const principal = getPrincipalFromSession({ userId: user.id }, playlistKey);
  const bundle = getStorageBundle({ supabaseClient: supabase }); // session-scoped, RLS-enforced

  let index;
  try {
    index = await bundle.metadataStore.readIndex(principal);
  } catch (err) {
    const e = err as { statusCode?: number; message?: string };
    if (e.statusCode === 400) {
      return NextResponse.json({ error: e.message }, { status: 400 });
    }
    logError('videos:readIndex', err);   // never swallow: log the real cause before Next returns a bare 500
    throw err;
  }

  const rawSortColumn = searchParams.get('sortColumn');
  const sortColumn: SortColumn =
    rawSortColumn && SORT_COLUMNS.has(rawSortColumn as SortColumn) ? (rawSortColumn as SortColumn) : 'name';
  const rawSortOrder = searchParams.get('sortOrder');
  const sortOrder: SortOrder = rawSortOrder === 'asc' || rawSortOrder === 'desc' ? rawSortOrder : 'asc';

  const videos = sortVideos(index.videos, sortColumn, sortOrder);
  return NextResponse.json({ videos, playlistUrl: index.playlistUrl, playlistTitle: index.playlistTitle });
}
