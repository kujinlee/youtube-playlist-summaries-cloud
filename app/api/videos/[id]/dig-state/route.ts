import path from 'path';
import { assertVideoId } from '../../../../../lib/index-store';
import { getPrincipal, getStorageBundle } from '../../../../../lib/storage/resolve';
import { readDugSectionIds } from '../../../../../lib/dig/companion-doc';
import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { cookies } from 'next/headers';
import { loadSummaryForServe } from '@/lib/html-doc/serve-summary-core';
import { logError } from '@/lib/dev-logger';

type Params = { params: Promise<{ id: string }> };

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

export async function GET(request: Request, { params }: Params) {
  const { id: videoId } = await params;
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'supabase') return serveCloud(request, videoId);
  return serveLocal(request, videoId); // existing body, renamed, unchanged
}

async function serveCloud(request: Request, videoId: string): Promise<Response> {
  const { searchParams } = new URL(request.url);
  const playlistId = searchParams.get('playlist');
  if (!playlistId || !UUID_RE.test(playlistId)) return json({ error: 'invalid playlist' }, 400);
  try { assertVideoId(videoId); } catch { return json({ error: 'invalid videoId' }, 400); }

  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return json({ error: 'authentication required' }, 401);

  try {
    // Reuse the html loader's owner-assert + status gate (committed→503, !promoted→404, not-owner→404)
    // and canonical base — identical to loadDigForServe (T3), so both endpoints agree on dig/{base}/.
    const load = await loadSummaryForServe(supabase, { videoId, playlistId, userId: user.id });
    if (!load.ok) return json({ error: load.error }, load.status);

    const suffix = `.r${DIG_GENERATOR_VERSION}.md`;
    const keys = await load.bundle.blobStore.list(load.principal, `dig/${load.base}/`);
    const sectionIds = keys
      .filter((k) => k.endsWith(suffix))                     // current version only (behavior 11)
      .map((k) => k.match(/\/(\d+)\.r\d+\.md$/))
      .filter((m): m is RegExpMatchArray => m !== null)
      .map((m) => parseInt(m[1], 10))
      .sort((a, b) => a - b);                                // ascending by sectionId (== startSec)
    return json({ sectionIds }, 200);
  } catch (err) {
    logError('dig-state:cloud', err); // observability parity with the html route (PR #18 5xx sweep)
    return json({ error: 'internal error' }, 500);
  }
}

async function serveLocal(request: Request, videoId: string): Promise<Response> {
  const { searchParams } = new URL(request.url);
  const outputFolder = searchParams.get('outputFolder');

  if (!outputFolder) {
    return new Response(JSON.stringify({ error: 'outputFolder is required' }), { status: 400 });
  }

  let principal;
  try {
    principal = getPrincipal(outputFolder);
    assertVideoId(videoId);
  } catch {
    return new Response(JSON.stringify({ error: 'invalid request' }), { status: 400 });
  }

  let video;
  try {
    const index = await getStorageBundle().metadataStore.readIndex(principal);
    video = index.videos.find((v) => v.id === videoId);
    if (!video) {
      return new Response(JSON.stringify({ error: 'video not found' }), { status: 404 });
    }
  } catch (err) {
    const e = err as { statusCode?: number; message?: string };
    if (e.statusCode === 400) {
      return new Response(JSON.stringify({ error: e.message }), { status: 400 });
    }
    throw err;
  }

  const digDeeperMd = video.digDeeperMd;
  if (!digDeeperMd) {
    return new Response(JSON.stringify({ sectionIds: [] }), {
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const digDeeperPath = path.join(outputFolder, digDeeperMd);
  const sectionIds = await readDugSectionIds(digDeeperPath);

  return new Response(JSON.stringify({ sectionIds }), {
    headers: { 'Content-Type': 'application/json' },
  });
}
