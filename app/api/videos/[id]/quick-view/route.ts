import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { assertVideoId } from '../../../../../lib/index-store';
import { getPrincipal, getStorageBundle, getPrincipalFromSession } from '../../../../../lib/storage/resolve';
import { createServerSupabase, type CookieStore } from '../../../../../lib/supabase/server';
import { resolveOwnedPlaylistKey } from '../../../../../lib/storage/serve-playlist';

type Params = { params: Promise<{ id: string }> };

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function GET(request: Request, { params }: Params) {
  const { id: videoId } = await params;
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'supabase') return serveCloud(request, videoId);
  return serveLocal(request, videoId);
}

// ---- LOCAL path — preserved verbatim (pre-2a Task 6 behavior, filesystem-backed) ----
async function serveLocal(request: Request, videoId: string): Promise<Response> {
  const { searchParams } = new URL(request.url);
  const outputFolder = searchParams.get('outputFolder');

  if (!outputFolder) {
    return NextResponse.json({ error: 'outputFolder is required' }, { status: 400 });
  }

  let principal;
  try {
    principal = getPrincipal(outputFolder);
    assertVideoId(videoId);
  } catch {
    return NextResponse.json({ error: 'invalid request' }, { status: 400 });
  }

  const index = await getStorageBundle().metadataStore.readIndex(principal);
  const video = index.videos.find((v) => v.id === videoId);

  if (!video || !video.summaryMd || !video.tldr) {
    return NextResponse.json({ error: 'quick view not available' }, { status: 404 });
  }

  return NextResponse.json({
    tldr: video.tldr,
    takeaways: video.takeaways ?? [],
    tags: video.tags ?? [],
  });
}

// ---- CLOUD path (Stage 2a Task 6) — session-scoped Supabase, owner-asserted via
// resolveOwnedPlaylistKey + RLS. Mirrors app/api/videos/route.ts serveCloud (Task 5):
// createServerSupabase → getUser → UUID guard → reject outputFolder → resolveOwnedPlaylistKey
// → getPrincipalFromSession → getStorageBundle({supabaseClient}). Applies the SAME
// summaryMd && tldr availability gate as serveLocal (parity, quick-view route:27-ish).
async function serveCloud(request: Request, videoId: string): Promise<Response> {
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

  const index = await bundle.metadataStore.readIndex(principal);
  const video = index.videos.find((v) => v.id === videoId);

  if (!video || !video.summaryMd || !video.tldr) {
    return NextResponse.json({ error: 'quick view not available' }, { status: 404 });
  }

  return NextResponse.json({
    tldr: video.tldr,
    takeaways: video.takeaways ?? [],
    tags: video.tags ?? [],
  });
}
