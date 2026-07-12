import { cookies } from 'next/headers';
import { assertVideoId } from '@/lib/index-store';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { loadSummaryForServe, resolveAndParse } from '@/lib/html-doc/serve-summary-core';
import { renderMagazineHtml } from '@/lib/html-doc/render';
import { pdfCacheKey } from '@/lib/pdf/pdf-render-version';
import { generateDocPdf } from '@/lib/pdf/generate-doc-pdf';
import { PdfRendererUnavailable } from '@/lib/pdf/pdf-renderer-error';
import { runSingleFlight, withPdfSlot, PdfBusyError } from '@/lib/pdf/pdf-concurrency';

type Params = { params: Promise<{ id: string }> };
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const json = (body: unknown, status: number) => new Response(JSON.stringify(body), { status });

/**
 * GET /api/pdf/[id] — lazily render a video's cloud summary to a print-ready A4 PDF, cache it
 * content-addressed (`pdfCacheKey`, keyed on the NONCE-FREE rendered HTML so the cache hits
 * deterministically), and stream it inline. Composes Task 6's two-stage serve-summary-core
 * (gate+read, then parse+resolve — money is charged there) with Tasks 3-5's PDF cache/concurrency/
 * render primitives. Cloud-only: the local backend keeps its own export action (see AGENTS.md route
 * conventions in app/api/html/[id]/route.ts serveLocal).
 */
export async function GET(request: Request, { params }: Params) {
  if ((process.env.STORAGE_BACKEND ?? 'local') !== 'supabase') return json({ error: 'use the export action' }, 400);
  const { id: videoId } = await params;
  const { searchParams } = new URL(request.url);
  // URL contract mirrors app/api/html/[id]/route.ts's serveCloud: cloud requires `playlist`,
  // rejects `outputFolder`, and only serves `type=summary` (dig-deeper deferred).
  if (searchParams.get('outputFolder')) return json({ error: 'outputFolder not valid on this backend' }, 400);
  if (searchParams.get('type') !== 'summary') return json({ error: 'unsupported or missing type' }, 400);
  const playlistId = searchParams.get('playlist');
  if (!playlistId || !UUID_RE.test(playlistId)) return json({ error: 'invalid playlist' }, 400); // before any DB call
  try { assertVideoId(videoId); } catch { return json({ error: 'invalid videoId' }, 400); } // 400 BEFORE auth
  // stray format/download params (relevant only to the HTML/MD route) are intentionally ignored here —
  // this route always serves a PDF.

  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return json({ error: 'authentication required' }, 401);

  try {
    const load = await loadSummaryForServe(supabase, { videoId, playlistId, userId: user.id });
    if (!load.ok) return json({ error: load.error }, load.status);

    const r = await resolveAndParse(supabase, load, request.signal);
    if (!r.ok) return json({ error: r.error }, r.status);

    // NONCE-FREE render: a nonce would make the hash (and thus the cache key) different on every
    // request, defeating content-addressed caching. `dig: false` — cloud never serves dig-deeper.
    const html = renderMagazineHtml(r.parsed, r.model, { nonce: undefined, dig: false });
    const key = pdfCacheKey(load.base, html);
    // Owner-scoped flight key: collapses concurrent identical-content requests from the SAME owner's
    // SAME playlist index, without accidentally colliding across owners/playlists that happen to
    // produce the same content hash (H1).
    const flightKey = `${load.principal.id}/${load.principal.indexKey}/${key}`;

    let bytes = await load.bundle.blobStore.get(load.principal, key); // single get = hit detection
    if (!bytes) {
      bytes = await runSingleFlight(flightKey, () => withPdfSlot(async () => {
        const cached = await load.bundle.blobStore.get(load.principal, key); // recheck INSIDE the slot
        if (cached) return cached;
        return generateDocPdf(html, load.principal, key, { blobStore: load.bundle.blobStore, returnBuffer: true }) as Promise<Buffer>;
      }));
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/pdf',
      'Content-Disposition': 'inline',
      'Cache-Control': 'private, no-store',
    };
    if (r.stale) headers['X-Magazine-Stale'] = '1';
    // `as BodyInit`: @types/node's Buffer is not structurally assignable to lib.dom's BodyInit
    // (mirrors lib/html-doc/file-response.ts:55).
    return new Response(bytes as BodyInit, { status: 200, headers });
  } catch (err) {
    const e = err as { statusCode?: number; message?: string };
    if (e instanceof PdfBusyError || e instanceof PdfRendererUnavailable || e.statusCode === 503) {
      return json({ error: 'PDF renderer unavailable, retry' }, 503);
    }
    if (e.statusCode === 400) return json({ error: e.message }, 400);
    return json({ error: 'internal error' }, 500);
  }
}
