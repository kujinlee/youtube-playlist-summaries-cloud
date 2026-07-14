import { cookies } from 'next/headers';
import { logError } from '@/lib/dev-logger';
import { assertVideoId } from '../../../../lib/index-store';
import { getPrincipal, getStorageBundle } from '../../../../lib/storage/resolve';
import { buildDocHtml } from '../../../../lib/html-doc/build-doc-html';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { loadSummaryForServe, resolveAndParse } from '@/lib/html-doc/serve-summary-core';
import { renderMagazineHtml } from '@/lib/html-doc/render';
import { generateNonce, buildSummaryCsp } from '@/lib/html-doc/csp';
import { fileResponse } from '@/lib/html-doc/file-response';

type Params = { params: Promise<{ id: string }> };

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const json = (body: unknown, status: number) => new Response(JSON.stringify(body), { status });

export async function GET(request: Request, { params }: Params) {
  const { id: videoId } = await params;
  const { searchParams } = new URL(request.url);
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'supabase') return serveCloud(request, videoId, searchParams);
  return serveLocal(videoId, searchParams);
}

async function serveCloud(request: Request, videoId: string, searchParams: URLSearchParams): Promise<Response> {
  // URL contract: cloud requires `playlist`, rejects `outputFolder`; type must be `summary`.
  if (searchParams.get('outputFolder')) return json({ error: 'outputFolder not valid on this backend' }, 400);
  const type = searchParams.get('type');
  if (type !== 'summary') return json({ error: 'unsupported or missing type' }, 400); // cloud dig-deeper deferred
  const formatValues = searchParams.getAll('format');
  const format = formatValues.length === 0 ? 'html' : formatValues[0];
  if (formatValues.length > 1 || (format !== 'html' && format !== 'md')) return json({ error: 'invalid format' }, 400);
  const download = searchParams.get('download') === '1';
  const playlistId = searchParams.get('playlist');
  if (!playlistId || !UUID_RE.test(playlistId)) return json({ error: 'invalid playlist' }, 400); // before any DB call
  try { assertVideoId(videoId); } catch { return json({ error: 'invalid videoId' }, 400); }

  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return json({ error: 'authentication required' }, 401);

  try {
    const load = await loadSummaryForServe(supabase, { videoId, playlistId, userId: user.id });
    if (!load.ok) return json({ error: load.error }, load.status);

    if (format === 'md') {
      // D4 money invariant: short-circuits BEFORE resolveAndParse/resolveMagazineModel — must NOT
      // reach reserve_serve_model / generation.
      return fileResponse(load.mdBytes, {
        kind: 'md', download, base: load.base, title: load.title,
        cache: 'private, no-store', // helper adds nosniff; inline md → text/plain, download md → text/markdown
      });
    }

    const r = await resolveAndParse(supabase, load, request.signal);
    if (!r.ok) return json({ error: r.error }, r.status);

    const nonce = generateNonce();
    const html = renderMagazineHtml(r.parsed, r.model, { nonce, dig: false }); // D11 nonce + D12 no dig
    return fileResponse(html, {
      kind: 'html', download, base: load.base, title: load.title,
      cache: 'private, no-store', csp: buildSummaryCsp(nonce),
      staleMarker: r.stale === true, // D6: serve-stale-over-budget flags X-Magazine-Stale
    });
  } catch (err) {
    const e = err as { statusCode?: number; message?: string };
    if (e.statusCode === 400) return json({ error: e.message }, 400);
    logError('html:serve', err);   // unexpected (not the 400) — surface before the generic 500
    return json({ error: 'internal error' }, 500);
  }
}

// ---- LOCAL path — preserved verbatim from pre-1F-a (sentinel principal / outputFolder / no CSP) ----
async function serveLocal(videoId: string, searchParams: URLSearchParams): Promise<Response> {
  const outputFolder = searchParams.get('outputFolder');
  if (searchParams.get('playlist')) return json({ error: 'playlist not valid on this backend' }, 400);
  if (!outputFolder) return json({ error: 'outputFolder is required' }, 400);
  let principal;
  try { principal = getPrincipal(outputFolder); assertVideoId(videoId); }
  catch { return json({ error: 'invalid request' }, 400); }

  const type = searchParams.get('type');
  if (type !== 'summary' && type !== 'dig-deeper') return json({ error: 'unsupported or missing type' }, 400);

  let video;
  try {
    const index = await getStorageBundle().metadataStore.readIndex(principal);
    video = index.videos.find((v) => v.id === videoId);
    if (!video) return json({ error: 'video not found' }, 404);
  } catch (err) {
    const e = err as { statusCode?: number; message?: string };
    if (e.statusCode === 400) return json({ error: e.message }, 400);
    logError('html:local', err);   // never swallow: log before Next returns a bare 500
    throw err;
  }

  const result = await buildDocHtml(video, outputFolder, type);
  if (result.ok) return new Response(result.html, { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
  const status = result.reason === 'invalid-path' ? 400 : 404;
  return json({ error: result.reason }, status);
}
