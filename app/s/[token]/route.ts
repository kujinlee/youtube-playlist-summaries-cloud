import { createServiceClient } from '@/lib/supabase/service';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
import { getShareServeContext } from '@/lib/share/serve';
import { readTitleStableModel } from '@/lib/html-doc/read-model';
import { parseSummaryMarkdown } from '@/lib/html-doc/parse';
import { renderMagazineHtml } from '@/lib/html-doc/render';
import { generateNonce, buildSummaryCsp } from '@/lib/html-doc/csp';
import { fileResponse } from '@/lib/html-doc/file-response';
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
const notFound400 = () => new Response(JSON.stringify({ error: 'invalid format' }), { status: 400, headers: DENIAL_HEADERS });

export async function GET(_req: Request, { params }: { params: Promise<{ token: string }> }) {
  // format/download are parsed and validated FIRST — token-independent (no oracle): a bad `format`
  // on a malformed token must 400 without ever reaching TOKEN_RE/DB, so it can't leak
  // token-existence timing (D12/B-L2). `getAll` (not `.get`) so a duplicate ?format=… param can't
  // bypass validation via the first value (the owner route shipped exactly this bypass — Codex
  // Medium — fixed here from the start).
  const { searchParams } = new URL(_req.url);
  const formatValues = searchParams.getAll('format');
  const format = formatValues.length === 0 ? 'html' : formatValues[0];
  if (formatValues.length > 1 || (format !== 'html' && format !== 'md')) return notFound400();
  const download = searchParams.get('download') === '1';

  const { token } = await params;
  if (!TOKEN_RE.test(token)) return notFound(); // malformed → before any DB call (B11)

  const svc = createServiceClient();
  const ctx = await getShareServeContext(svc, token);
  if ('status' in ctx) return notFound(); // denied — expired/revoked/unknown/unpromoted (B9/B10/B12/B13)

  const fullStore = new SupabaseBlobStore(svc, ARTIFACTS_BUCKET);
  const readOnly: ReadOnlyBlobStore = { get: fullStore.get.bind(fullStore) }; // runtime get-only (D16)
  const principal = { id: ctx.ownerId, indexKey: ctx.playlistKey };

  let mdBytes;
  try {
    mdBytes = await readOnly.get(principal, ctx.mdKey);
  } catch (err) {
    // Corrupt persisted mdKey (e.g. a path-traversal key) makes the store's assertLogicalKey throw
    // (statusCode 400). Coarse 404, never a 500 leak (B13b). A genuine infra error (no 400) still
    // surfaces as 500 rather than being masked as "not found".
    if ((err as { statusCode?: number }).statusCode === 400) return notFound();
    throw err;
  }
  if (!mdBytes) return notFound(); // MD lost behind promoted (B13b)

  if (format === 'md') {
    // D4 money invariant: short-circuits AFTER the mdBytes read/bad-key catch but BEFORE
    // parseSummaryMarkdown/readTitleStableModel — must NOT resolve a model or charge.
    // D12/B10b: still runs the SAME mandatory pre-response re-check the html path runs, so a
    // revoke/un-promote landing between the initial resolve (above) and this response is caught —
    // read-only, never charges.
    const recheck = await getShareServeContext(svc, token);
    if ('status' in recheck) return notFound();
    return fileResponse(mdBytes, {
      kind: 'md', download, base: ctx.mdKey.replace(/\.md$/, ''), title: ctx.title,
      cache: 'no-store', referrerPolicy: 'no-referrer', // helper adds nosniff; inline md → text/plain
    });
  }

  let parsed;
  try { parsed = parseSummaryMarkdown(mdBytes.toString('utf-8')); }
  catch { return notFound(); } // corrupt/unparsable MD → coarse 404, never 500 (B13b)
  parsed.sourceMd = ctx.mdKey;
  const base = ctx.mdKey.replace(/\.md$/, '');
  const titles = parsed.sections.map((s) => s.title);

  // TITLE-STABLE, not fresh: a version-skewed model is SERVED rather than refused (M1.4 item B4,
  // product decision 2026-08-11 — "tolerate"). Skew is the normal state during a rolling deploy,
  // and the old behavior's self-heal ("heals after owner next views") never fires for a share
  // whose owner does not revisit the doc, so the link stayed broken indefinitely.
  //
  // What zod does and does NOT cover here — stated exactly, because the first draft of this comment
  // overclaimed it (B4 review High-1). readModelEnvelope safeParses against the CURRENT
  // ModelEnvelopeSchema and returns null on mismatch, so an envelope that VIOLATES the schema fails
  // closed (missing/mistyped fields, out-of-bounds `bullets`). But the strictness is shallow:
  // ModelEnvelopeSchema deliberately dropped `.strict()` for forward-compat (model-store.ts), and
  // only the top-level MagazineModelSchema is strict — BulletSchema and MagazineSectionSchema are
  // not (lib/html-doc/types.ts), so a version bump that ADDS a nested field (`section.pullQuote`,
  // `bullet.kind`) parses fine and is silently stripped, and one that changes the MEANING of an
  // existing field of the same type is invisible to zod entirely.
  // So: tolerating admits the prompt half of GENERATOR_VERSION (same structure, older prose) AND
  // the nested-additive/semantic half. That is the accepted cost of the "tolerate" decision, not a
  // guarantee against it. What still fails closed is a schema VIOLATION, plus the two checks below.
  //
  // `titles` still gates positional coherence — a drifted-title model would mis-pair against the
  // current markdown, so it is still refused. Same helper, and the same rationale, as the D5
  // owner_over_budget path in serve-doc.ts. Still NO generation (B7/B8/B18b).
  const model = await readTitleStableModel({ blobStore: readOnly, principal, base, titles });
  if (model.status !== 'ok') return notReady(); // absent / title-drifted / unparsable

  // Mandatory pre-response re-check: closes revoke/un-promote-before-final-check (D14/B10b).
  const recheck = await getShareServeContext(svc, token);
  if ('status' in recheck) return notFound();

  const nonce = generateNonce();
  const html = renderMagazineHtml(parsed, model.model, { nonce, dig: false, share: true });
  return fileResponse(html, {
    kind: 'html', download, base: ctx.mdKey.replace(/\.md$/, ''), title: ctx.title,
    cache: 'no-store', csp: buildSummaryCsp(nonce), referrerPolicy: 'no-referrer',
  });
}
