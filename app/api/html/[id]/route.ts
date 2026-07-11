import { cookies } from 'next/headers';
import { assertVideoId } from '../../../../lib/index-store';
import { getPrincipal, getStorageBundle, getPrincipalFromSession } from '../../../../lib/storage/resolve';
import { buildDocHtml } from '../../../../lib/html-doc/build-doc-html';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { resolveOwnedPlaylistKey } from '@/lib/storage/serve-playlist';
import { resolveMagazineModel } from '@/lib/html-doc/serve-doc';
import { parseSummaryMarkdown } from '@/lib/html-doc/parse';
import { renderMagazineHtml } from '@/lib/html-doc/render';
import { generateNonce, buildSummaryCsp } from '@/lib/html-doc/csp';
import { fileResponse } from '@/lib/html-doc/file-response';
import type { Video } from '@/types';

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
    const playlistKey = await resolveOwnedPlaylistKey(supabase, playlistId, user.id); // owner-asserted (D6/D9)
    if (!playlistKey) return json({ error: 'not found' }, 404);

    const principal = getPrincipalFromSession({ userId: user.id }, playlistKey);
    const bundle = getStorageBundle({ supabaseClient: supabase }); // session-scoped, RLS-enforced (D5)
    const index = await bundle.metadataStore.readIndex(principal);
    const video = index.videos.find((v) => v.id === videoId) as Video | undefined;
    if (!video) return json({ error: 'not found' }, 404);

    const artifact = (video as unknown as { artifacts?: { summaryMd?: { key?: string; status?: string } } }).artifacts?.summaryMd;
    const status = artifact?.status;
    if (status === 'committed') return json({ error: 'not ready, retry' }, 503); // finalizing window (B12)
    if (status !== 'promoted') return json({ error: 'not found' }, 404);          // absent/unknown (B13)

    // Key source: prefer artifacts.summaryMd.key (the artifact record), fall back to top-level
    // video.summaryMd. persist_summary (0009) writes BOTH to the same value, so they agree; reading the
    // artifact key first addresses Codex H-2 (don't fetch a blob the artifact record doesn't govern).
    const mdKey = artifact?.key ?? video.summaryMd;
    if (!mdKey) return json({ error: 'not found' }, 404);
    const mdBytes = await bundle.blobStore.get(principal, mdKey);
    if (!mdBytes) return json({ error: 'repair needed' }, 409); // promoted but blob lost (B13b)

    // IDENTITY COHERENCE (Task 5/6 carry-forward): `base` is the canonical, DB-persisted baseName
    // (`${padSerial(serial)}_${slug}` — the worker's summary-handler key), derived deterministically
    // from the SAME summaryMd key the model store is keyed on (readModelEnvelope/writeModelEnvelope use
    // `base`). Because every request recomputes `base` from that persisted key, the reserve-RPC charge
    // (keyed on p_video_id=videoId) and the cached model blob (keyed on `base`) stay coherent across
    // views: the model written after a charge is found by the next read → no re-charge despite a cache
    // hit. (NOTE: base is NOT videoId in this system; the summary key is serial_slug, so an assertion
    // `base === videoId` would be wrong — coherence comes from `base` being deterministic per video.)
    const base = mdKey.replace(/\.md$/, '');

    // M1 (1F-c whole-branch review): `video` is a cast, not zod-parsed, so a corrupt non-string
    // data.title would reach fileResponse and throw on .trim(). Coerce defensively — symmetric with
    // the share path (lib/share/serve.ts) — so non-string/blank → undefined → filename falls back to base.
    const rawTitle: unknown = video.title;
    const title = typeof rawTitle === 'string' && rawTitle.trim() ? rawTitle : undefined;

    if (format === 'md') {
      // D4 money invariant: short-circuits AFTER the mdBytes read/409 check but BEFORE any model
      // resolution — must NOT call resolveMagazineModel / reserve_serve_model / generation.
      return fileResponse(mdBytes, {
        kind: 'md', download, base, title,
        cache: 'private, no-store', // helper adds nosniff; inline md → text/plain, download md → text/markdown
      });
    }

    const parsed = parseSummaryMarkdown(mdBytes.toString('utf-8'));
    parsed.sourceMd = mdKey;

    const resolved = await resolveMagazineModel({
      supabaseClient: supabase, blobStore: bundle.blobStore, principal,
      playlistId, videoId, base, parsed, language: video.language, signal: request.signal,
    });
    switch (resolved.status) {
      case 'denied': return json({ error: 'not found' }, 404);                 // generic, no leak
      case 'busy': return json({ error: 'generating, retry shortly' }, 503);   // B6b
      case 'attempts_exhausted': return json({ error: 'temporarily unavailable, try later' }, 503); // B7f
      case 'at_capacity': return json({ error: 'at capacity' }, 503);          // B6
      case 'over_budget': return json({ error: 'daily refresh budget reached, try tomorrow' }, 503); // D6/G1
      case 'ok': break;
    }

    const nonce = generateNonce();
    const html = renderMagazineHtml(parsed, resolved.model, { nonce, dig: false }); // D11 nonce + D12 no dig
    return fileResponse(html, {
      kind: 'html', download, base, title,
      cache: 'private, no-store', csp: buildSummaryCsp(nonce),
      staleMarker: resolved.stale === true, // D6: serve-stale-over-budget flags X-Magazine-Stale
    });
  } catch (err) {
    const e = err as { statusCode?: number; message?: string };
    if (e.statusCode === 400) return json({ error: e.message }, 400);
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
    throw err;
  }

  const result = await buildDocHtml(video, outputFolder, type);
  if (result.ok) return new Response(result.html, { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
  const status = result.reason === 'invalid-path' ? 400 : 404;
  return json({ error: result.reason }, status);
}
