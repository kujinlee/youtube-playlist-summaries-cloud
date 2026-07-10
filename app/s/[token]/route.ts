import { createServiceClient } from '@/lib/supabase/service';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
import { getShareServeContext } from '@/lib/share/serve';
import { readFreshMagazineModel } from '@/lib/html-doc/read-model';
import { parseSummaryMarkdown } from '@/lib/html-doc/parse';
import { renderMagazineHtml } from '@/lib/html-doc/render';
import { generateNonce, buildSummaryCsp } from '@/lib/html-doc/csp';
import type { ReadOnlyBlobStore } from '@/lib/storage/blob-store';

// MONEY GUARD (spec B18b, enforced by tests/lib/share/import-guard.test.ts): this module must not
// import the charging/serve-doc modules and must never call the reserve RPC. (Do NOT name the
// forbidden symbols here — the guard greps this file's raw text for them.)

const TOKEN_RE = /^[A-Za-z0-9_-]{43}$/; // 32-byte base64url
// Both denial responses carry no-store/no-referrer too (Claude Minor): a cached 503 for a
// valid-but-not-ready token could otherwise outlive the model being materialized, and a cached
// 404 could leak token-existence timing via a shared/browser cache.
const DENIAL_HEADERS = { 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer' };
const notFound = () => new Response(JSON.stringify({ error: 'not found' }), { status: 404, headers: DENIAL_HEADERS });
const notReady = () => new Response(JSON.stringify({ error: 'not ready, retry shortly' }), { status: 503, headers: DENIAL_HEADERS });

export async function GET(_req: Request, { params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  if (!TOKEN_RE.test(token)) return notFound(); // malformed → before any DB call (B11)

  const svc = createServiceClient();
  const ctx = await getShareServeContext(svc, token);
  if ('status' in ctx) return notFound(); // denied — expired/revoked/unknown/unpromoted (B9/B10/B12/B13)

  const fullStore = new SupabaseBlobStore(svc, ARTIFACTS_BUCKET);
  const readOnly: ReadOnlyBlobStore = { get: fullStore.get.bind(fullStore) }; // runtime get-only (D16)
  const principal = { id: ctx.ownerId, indexKey: ctx.playlistKey };

  const mdBytes = await readOnly.get(principal, ctx.mdKey);
  if (!mdBytes) return notFound(); // MD lost behind promoted (B13b)

  let parsed;
  try { parsed = parseSummaryMarkdown(mdBytes.toString('utf-8')); }
  catch { return notFound(); } // corrupt/unparsable MD → coarse 404, never 500 (B13b)
  parsed.sourceMd = ctx.mdKey;
  const base = ctx.mdKey.replace(/\.md$/, '');
  const titles = parsed.sections.map((s) => s.title);

  const model = await readFreshMagazineModel({ blobStore: readOnly, principal, base, titles });
  if (model.status !== 'ok') return notReady(); // absent/stale — NO generation (B7/B8)

  // Mandatory pre-response re-check: closes revoke/un-promote-before-final-check (D14/B10b).
  const recheck = await getShareServeContext(svc, token);
  if ('status' in recheck) return notFound();

  const nonce = generateNonce();
  const html = renderMagazineHtml(parsed, model.model, { nonce, dig: false, share: true });
  return new Response(html, {
    status: 200,
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Content-Security-Policy': buildSummaryCsp(nonce),
      'Cache-Control': 'no-store',
      'Referrer-Policy': 'no-referrer',
    },
  });
}
