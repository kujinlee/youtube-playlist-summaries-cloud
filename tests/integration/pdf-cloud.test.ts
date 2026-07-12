// tests/integration/pdf-cloud.test.ts
//
// GET /api/pdf/[id] (cloud PDF serve route, app/api/pdf/[id]/route.ts) against a REAL local
// Supabase stack — the non-vacuous proof of the money + owner-scoping invariants that the T8 unit
// tests could only mock. Mirrors tests/integration/html-download.test.ts's auth-plumbing pattern:
// only next/headers + @/lib/supabase/server are mocked (to hand the route a REAL signed-in session
// client from `signInAs`); everything downstream (RLS, resolveOwnedPlaylistKey, getStorageBundle,
// resolveMagazineModel, reserve_serve_model, real Supabase Storage) runs for real. `lib/gemini` is
// mocked per the dev-process lib boundary; `generateDocPdf` (real impl launches headless Chromium)
// is stubbed to mimic its real contract — it MUST write to the blob store via the passed
// `opts.blobStore` (real Supabase storage) and return the buffer, so the cache round-trip is real.
//
// Proves:
//  - round-trip cache: first request renders+caches the pdf blob; second serves from cache
//    (generateDocPdf called exactly ONCE total).
//  - owner isolation: a SECOND real user session requesting the FIRST owner's video → 404.
//  - the money invariant NON-VACUOUSLY: with a FRESH magazine model pre-seeded, the PDF request
//    makes NO reserve_serve_model RPC and spend_ledger is unchanged — proven against a mutation
//    control (same request, no fresh model) that DOES reserve once, so a regression that starts
//    charging on a fresh/cache hit would be caught.
//  - owner-scoped PDF cache flight key (H1): two DIFFERENT owners with IDENTICAL summary content
//    (same md/model/base -> identical content hash) firing genuinely concurrent requests BOTH get
//    their own owner-namespaced pdf blob written — a bare content-hash flight key would collapse
//    the two in-flight renders into one and silently drop the second owner's write.
//  - (best-effort) concurrent same-owner same-content miss collapses into exactly one render.
import { AsyncLocalStorage } from 'async_hooks';
import { randomUUID } from 'crypto';
import { SupabaseClient } from '@supabase/supabase-js';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo, seedSummaryBlob } from './helpers/seed';
import { writeModelEnvelope } from '@/lib/html-doc/model-store';
import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
import { parseSummaryMarkdown } from '@/lib/html-doc/parse';
import { renderMagazineHtml } from '@/lib/html-doc/render';
import { pdfCacheKey } from '@/lib/pdf/pdf-render-version';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
import type { Principal } from '@/lib/storage/principal';
import type { BlobStore } from '@/lib/storage/blob-store';

jest.mock('next/headers', () => ({ cookies: async () => ({ getAll: () => [], set: () => {} }) }));

// AsyncLocalStorage-scoped session client — a single shared mutable variable (the
// html-download.test.ts pattern) is NOT safe for a test that fires TWO DIFFERENT users' requests
// genuinely concurrently: both GETs perform the identical number/shape of awaits before reaching
// createServerSupabase, so they resume in lockstep and would both end up observing whichever value
// a plain variable last held (set synchronously by the test before either promise's continuation
// ever runs). AsyncLocalStorage threads the correct per-call client through the whole async chain
// regardless of interleaving — the same mechanism Next.js itself uses for request-scoped
// cookies()/headers(). Sequential tests keep using the simpler `mockClient` fallback.
// `mock`-prefixed per babel-plugin-jest-hoist's static-analysis whitelist (jest.mock factories are
// hoisted above these declarations) — same pattern as tests/integration/html-download.test.ts.
const mockAls = new AsyncLocalStorage<SupabaseClient>();
let mockClient: SupabaseClient;
jest.mock('@/lib/supabase/server', () => ({
  createServerSupabase: jest.fn(() => mockAls.getStore() ?? mockClient),
}));

jest.mock('@/lib/gemini', () => ({
  generateMagazineModel: jest.fn(async () => ({
    sections: [{ lead: 'L', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] }],
  })),
}));
import { generateMagazineModel } from '@/lib/gemini';

const SMALL_PDF_BUFFER = Buffer.from('%PDF-1.4 fake pdf bytes for test\n', 'utf-8');
// Widened ONLY by the concurrency test below (reset in its own try/finally) to make the
// same-owner single-flight race reproducible: the DB round-trips a real request performs before
// reaching runSingleFlight are fast on local loopback Postgres, so an instant stub risks the first
// request's render+put completing (and clearing the flight-map entry) before the second request
// even registers — an artificial delay here widens that window without affecting correctness.
let renderDelayMs = 0;
jest.mock('@/lib/pdf/generate-doc-pdf', () => ({ generateDocPdf: jest.fn() }));
import { generateDocPdf } from '@/lib/pdf/generate-doc-pdf';
(generateDocPdf as jest.Mock).mockImplementation(
  async (_html: string, principal: Principal, key: string, opts: { blobStore: BlobStore }) => {
    if (renderDelayMs > 0) await new Promise((r) => setTimeout(r, renderDelayMs));
    await opts.blobStore.put(principal, key, SMALL_PDF_BUFFER, 'application/pdf');
    return SMALL_PDF_BUFFER;
  },
);

import { GET } from '@/app/api/pdf/[id]/route';

const svc = adminClient();
const MD = `# T\n**Channel:** C | **Duration:** 1:00\n\n## 1. Intro\nbody\n`;
const FRESH_MODEL = {
  sections: [{ lead: 'L', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] }],
};

// getStorageBundle({ supabaseClient }) selects the Supabase stores only when STORAGE_BACKEND==='supabase'.
const priorBackend = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { if (priorBackend === undefined) delete process.env.STORAGE_BACKEND; else process.env.STORAGE_BACKEND = priorBackend; });

beforeEach(async () => {
  (generateMagazineModel as jest.Mock).mockClear();
  (generateDocPdf as jest.Mock).mockClear();
  renderDelayMs = 0;
  // Clear the shared money tables and pin generous, deterministic guardrail headroom — this local
  // Supabase stack persists across test runs, so a stale spend_ledger row from an earlier file/run
  // could otherwise trip at_capacity here (mirrors html-download.test.ts's own beforeEach).
  await svc.from('serve_model_charge').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
  await svc.from('serve_owner_budget').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
  await svc.from('guardrail_config').update({
    daily_cap_cents: 500, magazine_est_cents: 6, max_serve_attempts: 5, lease_ttl_seconds: 180,
    per_owner_serve_daily_cents: 60,
  }).eq('id', true);
});

let vidSeq = 0;
/** assertVideoId (lib/index-store.ts) requires `^[A-Za-z0-9_-]{1,20}$` — a plain `v-${randomUUID()}`
 *  (38 chars) fails it, so mint a short id here rather than relying on seedPromotedVideo's default. */
function shortVideoId(): string {
  return `v${Date.now().toString(36)}${(vidSeq++).toString(36)}`;
}

async function seedDoc(ownerId: string, title: string, base?: string) {
  const { playlistId, playlistKey } = await seedPlaylist(svc, ownerId);
  const { videoId, base: b } = await seedPromotedVideo(svc, {
    ownerId, playlistId, title, videoId: shortVideoId(), ...(base ? { base } : {}),
  });
  return { playlistId, playlistKey, videoId, base: b };
}

/** Seed an owner + promoted doc + MD blob, sign in as the owner, and arm the route's mocked
 *  createServerSupabase to hand back that REAL session client (via the `mockClient` fallback). */
async function ownerAndDoc(title = 'My Doc Title', base?: string) {
  const u = await newUser();
  const { playlistId, playlistKey, videoId, base: seededBase } = await seedDoc(u.user.id, title, base);
  await seedSummaryBlob(svc, u.user.id, playlistKey, seededBase, MD);
  const { client } = await signInAs(u.email, u.password);
  mockClient = client;
  return { u, playlistId, playlistKey, videoId, base: seededBase, client };
}

function req(videoId: string, qs: string) {
  return new Request(`http://localhost/api/pdf/${videoId}?${qs}`);
}
function invoke(id: string) { return { params: Promise.resolve({ id }) }; }

/** Materialize a FRESH magazine model envelope (current GENERATOR_VERSION, section titles matching
 *  MD) so resolveMagazineModel's readFreshMagazineModel short-circuits: NO Gemini call, NO
 *  reserve_serve_model RPC (lib/html-doc/serve-doc.ts:48-49). */
async function primeFreshModel(client: SupabaseClient, base: string, principal: Principal): Promise<void> {
  const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
  const titles = parseSummaryMarkdown(MD).sections.map((s) => s.title);
  await writeModelEnvelope(principal, base, {
    sourceMd: `${base}.md`,
    generatedAt: '2026-01-01T00:00:00.000Z',
    sourceSections: titles,
    generatorVersion: GENERATOR_VERSION,
    model: FRESH_MODEL,
  }, blob);
}

/** Compute the exact pdf cache key the route will derive for (base, MD, FRESH_MODEL) — mirrors the
 *  route's own parse -> render(nonce:undefined, dig:false) -> pdfCacheKey pipeline exactly (same
 *  pure inputs => same deterministic output) so the test can assert cache existence directly
 *  without reaching into route internals. */
function expectedFreshPdfKey(base: string): string {
  const parsed = parseSummaryMarkdown(MD);
  parsed.sourceMd = `${base}.md`;
  const html = renderMagazineHtml(parsed, FRESH_MODEL, { nonce: undefined, dig: false });
  return pdfCacheKey(base, html);
}

describe('pdf-cloud (GET /api/pdf/[id], real DB)', () => {
  it('round-trip: first GET renders+caches the pdf blob; second GET serves from cache (generateDocPdf called ONCE total)', async () => {
    const { u, playlistId, playlistKey, videoId, base } = await ownerAndDoc();
    const principal: Principal = { id: u.user.id, indexKey: playlistKey };
    await primeFreshModel(mockClient, base, principal);
    const key = expectedFreshPdfKey(base);
    const blob = new SupabaseBlobStore(mockClient, ARTIFACTS_BUCKET);

    expect(await blob.get(principal, key)).toBeNull(); // no pdf cached yet

    const res1 = await GET(req(videoId, `playlist=${playlistId}&type=summary`), invoke(videoId));
    expect(res1.status).toBe(200);
    expect(res1.headers.get('content-type')).toBe('application/pdf');
    expect(generateDocPdf).toHaveBeenCalledTimes(1);
    const body1 = Buffer.from(await res1.arrayBuffer());
    expect(body1.equals(SMALL_PDF_BUFFER)).toBe(true);

    const cached = await blob.get(principal, key); // pdfs/{base}.r*.pdf now exists in the owner's namespace
    expect(cached).not.toBeNull();
    expect(cached!.equals(SMALL_PDF_BUFFER)).toBe(true);

    const res2 = await GET(req(videoId, `playlist=${playlistId}&type=summary`), invoke(videoId));
    expect(res2.status).toBe(200);
    expect(generateDocPdf).toHaveBeenCalledTimes(1); // still ONE total — second request is a genuine cache hit
    const body2 = Buffer.from(await res2.arrayBuffer());
    expect(body2.equals(SMALL_PDF_BUFFER)).toBe(true);
  });

  it('owner isolation: a SECOND real user session requesting the FIRST user\'s video/playlist -> 404', async () => {
    const { playlistId, videoId } = await ownerAndDoc();
    const second = await newUser();
    const { client: secondClient } = await signInAs(second.email, second.password);
    mockClient = secondClient; // second user's own real session, NOT service role

    const res = await GET(req(videoId, `playlist=${playlistId}&type=summary`), invoke(videoId));
    expect(res.status).toBe(404); // resolveOwnedPlaylistKey returns null for a non-owner
    expect(generateDocPdf).not.toHaveBeenCalled();
  });

  it('money: fresh model -> PDF request makes NO reserve_serve_model RPC; spend_ledger unchanged', async () => {
    const { u, playlistId, playlistKey, videoId, base } = await ownerAndDoc();
    const principal: Principal = { id: u.user.id, indexKey: playlistKey };
    await primeFreshModel(mockClient, base, principal);
    const { data: ledgerBefore } = await svc.from('spend_ledger').select('*').order('day');
    const rpcSpy = jest.spyOn(SupabaseClient.prototype, 'rpc');

    const res = await GET(req(videoId, `playlist=${playlistId}&type=summary`), invoke(videoId));

    expect(res.status).toBe(200);
    const reserveCalls = rpcSpy.mock.calls.filter((c) => c[0] === 'reserve_serve_model');
    expect(reserveCalls.length).toBe(0); // B1 fresh short-circuit — no reserve RPC at all
    const { data: ledgerAfter } = await svc.from('spend_ledger').select('*').order('day');
    expect(ledgerAfter ?? []).toEqual(ledgerBefore ?? []);
    expect(generateMagazineModel).not.toHaveBeenCalled();
    rpcSpy.mockRestore();
  });

  it('money mutation control: WITHOUT a fresh model, the SAME request DOES call reserve_serve_model once (proves the no-charge assertion above is non-vacuous)', async () => {
    const { playlistId, videoId } = await ownerAndDoc(); // no model seeded — absent, must reserve+generate
    const rpcSpy = jest.spyOn(SupabaseClient.prototype, 'rpc');

    const res = await GET(req(videoId, `playlist=${playlistId}&type=summary`), invoke(videoId));

    expect(res.status).toBe(200);
    const reserveCalls = rpcSpy.mock.calls.filter((c) => c[0] === 'reserve_serve_model');
    expect(reserveCalls.length).toBe(1); // absent model -> charged path: proves the spy would have caught a regression above
    expect(generateMagazineModel).toHaveBeenCalledTimes(1);
    rpcSpy.mockRestore();
  });

  it('owner-scoped cache (H1): two DIFFERENT owners, IDENTICAL content (same md/model/base) -> BOTH owner-namespaced pdf blobs get written on genuinely concurrent requests', async () => {
    const sharedBase = `shared-${randomUUID().slice(0, 8)}`;
    const first = await ownerAndDoc('Doc A', sharedBase);
    const firstClient = first.client;
    const second = await ownerAndDoc('Doc B', sharedBase);
    const secondClient = second.client;

    const p1: Principal = { id: first.u.user.id, indexKey: first.playlistKey };
    const p2: Principal = { id: second.u.user.id, indexKey: second.playlistKey };
    await primeFreshModel(firstClient, sharedBase, p1);
    await primeFreshModel(secondClient, sharedBase, p2);

    const key = expectedFreshPdfKey(sharedBase); // identical for both — same md/model/base => same content hash

    // ALS-scoped so each request's ENTIRE async chain sees its own session client regardless of
    // interleaving (see the module-level comment on mockAls) — a bare shared `mockClient` variable
    // would be unsafe here since both requests perform the identical await shape before reaching
    // createServerSupabase.
    const [res1, res2] = await Promise.all([
      mockAls.run(firstClient, () => GET(req(first.videoId, `playlist=${first.playlistId}&type=summary`), invoke(first.videoId))),
      mockAls.run(secondClient, () => GET(req(second.videoId, `playlist=${second.playlistId}&type=summary`), invoke(second.videoId))),
    ]);

    expect(res1.status).toBe(200);
    expect(res2.status).toBe(200);

    const blob1 = new SupabaseBlobStore(firstClient, ARTIFACTS_BUCKET);
    const blob2 = new SupabaseBlobStore(secondClient, ARTIFACTS_BUCKET);
    const owner1Pdf = await blob1.get(p1, key);
    const owner2Pdf = await blob2.get(p2, key);
    expect(owner1Pdf).not.toBeNull(); // owner 1's own pdf blob exists
    expect(owner2Pdf).not.toBeNull(); // owner 2's own pdf blob exists — NOT dropped by a bare content-hash flight key
  });

  it('(best-effort) concurrent same-owner same-content miss collapses into exactly ONE render (single-flight)', async () => {
    const { playlistId, playlistKey, videoId, base, u } = await ownerAndDoc();
    const principal: Principal = { id: u.user.id, indexKey: playlistKey };
    await primeFreshModel(mockClient, base, principal);
    renderDelayMs = 40; // widen the render window so both requests reliably overlap in-flight

    try {
      const [res1, res2] = await Promise.all([
        GET(req(videoId, `playlist=${playlistId}&type=summary`), invoke(videoId)),
        GET(req(videoId, `playlist=${playlistId}&type=summary`), invoke(videoId)),
      ]);
      expect(res1.status).toBe(200);
      expect(res2.status).toBe(200);
      expect(generateDocPdf).toHaveBeenCalledTimes(1); // single-flight collapse — one render for both callers
    } finally {
      renderDelayMs = 0;
    }
  });
});
