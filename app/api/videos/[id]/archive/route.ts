import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { assertOutputFolder, assertVideoId } from '../../../../../lib/index-store';
import { archiveVideo, unarchiveVideo } from '../../../../../lib/archive';
import { getPrincipalFromSession, getStorageBundle } from '../../../../../lib/storage/resolve';
import { createServerSupabase, type CookieStore } from '../../../../../lib/supabase/server';
import { resolveOwnedPlaylistKey } from '../../../../../lib/storage/serve-playlist';

type Params = { params: Promise<{ id: string }> };

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function POST(request: Request, { params }: Params) {
  const { id: videoId } = await params;
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'supabase') return serveCloud(request, videoId);
  return serveLocal(request, videoId);
}

// ---- LOCAL path — preserved verbatim (pre-2a Task 8 behavior, filesystem-backed) ----
async function serveLocal(request: Request, videoId: string): Promise<Response> {
  const body = await request.json().catch(() => null);
  const outputFolder = body?.outputFolder;
  const action = body?.action;

  if (!outputFolder) return NextResponse.json({ error: 'outputFolder is required' }, { status: 400 });
  if (action !== 'archive' && action !== 'unarchive') {
    return NextResponse.json({ error: 'action must be archive or unarchive' }, { status: 400 });
  }

  try {
    assertOutputFolder(outputFolder);
    assertVideoId(videoId);
  } catch {
    return NextResponse.json({ error: 'invalid request' }, { status: 400 });
  }

  if (action === 'archive') {
    await archiveVideo(outputFolder, videoId);
  } else {
    await unarchiveVideo(outputFolder, videoId);
  }

  return NextResponse.json({ ok: true });
}

// ---- CLOUD path (Stage 2a Task 8) — session-scoped Supabase, owner-asserted via
// resolveOwnedPlaylistKey + RLS + the update_video_annotations RPC's own auth.uid()
// guard (belt-and-suspenders). Mirrors the Task 7 review-route cloud flow: createServerSupabase →
// getUser → UUID guard → reject outputFolder → validate action → resolveOwnedPlaylistKey →
// getPrincipalFromSession → getStorageBundle({supabaseClient}). Writes go through
// updateVideoAnnotations (update_video_annotations RPC) — `archived` is already in its
// allowlist (Task 7); no new RPC is added here.
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

  const body = await request.json().catch(() => null) as Record<string, unknown> | null;

  if (body && 'outputFolder' in body) {
    return NextResponse.json({ error: 'outputFolder not valid on this backend' }, { status: 400 });
  }

  const action = body?.action;
  if (action !== 'archive' && action !== 'unarchive') {
    return NextResponse.json({ error: 'action must be archive or unarchive' }, { status: 400 });
  }

  const playlistKey = await resolveOwnedPlaylistKey(supabase, playlistId, user.id); // owner-asserted (D6/D9)
  if (!playlistKey) return NextResponse.json({ error: 'not found' }, { status: 404 });

  const principal = getPrincipalFromSession({ userId: user.id }, playlistKey);
  const bundle = getStorageBundle({ supabaseClient: supabase }); // session-scoped, RLS-enforced

  const { found } = await bundle.metadataStore.updateVideoAnnotations(
    principal, videoId, { archived: action === 'archive' }, [],
  );
  if (!found) return NextResponse.json({ error: 'video not found' }, { status: 404 });

  return NextResponse.json({ ok: true });
}
