const validPlaylist = '11111111-1111-1111-1111-111111111111';
const validVideo = 'vid123';
const promotedSummaryMd = `# T\n**Channel:** C | **Duration:** 1:00\n\n## 1. Intro\nbody\n`;

let mockUser: { id: string } | null;
let mockIndexVideos: any[];
let mockMdBytes: Buffer | null;
let mockResolve: any;
let mockBlobGet: jest.Mock;
let mockPlaylistKey: string | null;
let pdfCacheBytes: Buffer | null;

jest.mock('next/headers', () => ({ cookies: async () => ({ getAll: () => [], set: () => {} }) }));
jest.mock('@/lib/supabase/server', () => ({
  createServerSupabase: jest.fn(() => ({ __session: true, auth: { getUser: async () => ({ data: { user: mockUser } }) } })),
}));
jest.mock('@/lib/storage/resolve', () => {
  const actual = jest.requireActual('@/lib/storage/resolve');
  return {
    ...actual,
    getStorageBundle: jest.fn((arg?: { supabaseClient?: unknown }) => {
      if (!arg || !arg.supabaseClient) throw new Error('getStorageBundle called without a session supabaseClient');
      return {
        metadataStore: { readIndex: async () => ({ videos: mockIndexVideos }) },
        blobStore: { get: mockBlobGet },
      };
    }),
    getPrincipalFromSession: () => ({ id: mockUser?.id, indexKey: 'pk' }),
  };
});
jest.mock('@/lib/html-doc/serve-doc', () => ({ resolveMagazineModel: jest.fn(async () => mockResolve) }));
jest.mock('@/lib/storage/serve-playlist', () => ({ resolveOwnedPlaylistKey: async () => mockPlaylistKey }));
jest.mock('@/lib/pdf/generate-doc-pdf', () => ({ generateDocPdf: jest.fn() }));
// Wrap runSingleFlight (keeping its REAL single-flight behavior via requireActual) so tests can spy
// on the key it's called with — this is the only way to pin the owner-scoped flight key (H1 fix)
// against a regression to a bare cache key, since a bare key would still "work" functionally in
// every existing test (same owner throughout) but would collapse across DIFFERENT owners in prod.
jest.mock('@/lib/pdf/pdf-concurrency', () => {
  const actual = jest.requireActual('@/lib/pdf/pdf-concurrency');
  return { __esModule: true, ...actual, runSingleFlight: jest.fn(actual.runSingleFlight) };
});

import { GET } from '@/app/api/pdf/[id]/route';
import { generateDocPdf } from '@/lib/pdf/generate-doc-pdf';
import { PdfRendererUnavailable } from '@/lib/pdf/pdf-renderer-error';
import { runSingleFlight } from '@/lib/pdf/pdf-concurrency';

function req(qs: string) { return new Request(`http://localhost/api/pdf/${validVideo}?${qs}`); }
function ctx() { return { params: Promise.resolve({ id: validVideo }) }; }

// Mirrors the worker row (summary-handler.ts:149-164): top-level summaryMd + language + the promoted artifact.
const promotedVideo = { id: validVideo, language: 'en', summaryMd: `${validVideo}.md`, artifacts: { summaryMd: { key: `${validVideo}.md`, status: 'promoted' } } };

beforeEach(() => {
  process.env.STORAGE_BACKEND = 'supabase';
  mockUser = { id: 'owner-1' };
  mockIndexVideos = [promotedVideo];
  mockMdBytes = Buffer.from(promotedSummaryMd, 'utf-8');
  pdfCacheBytes = null; // default: cache MISS
  mockBlobGet = jest.fn(async (_p: any, key: string) => (key.endsWith('.md') ? mockMdBytes : pdfCacheBytes));
  mockResolve = { status: 'ok', model: { sections: [{ lead: 'L', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] }] } };
  mockPlaylistKey = 'pk';
  (generateDocPdf as jest.Mock).mockReset();
  (generateDocPdf as jest.Mock).mockResolvedValue(Buffer.from('NEW'));
  (runSingleFlight as jest.Mock).mockClear();
});
afterEach(() => { delete process.env.STORAGE_BACKEND; });

it('local backend → 400', async () => {
  process.env.STORAGE_BACKEND = 'local';
  const res = await GET(req(`type=summary&playlist=${validPlaylist}`), ctx());
  expect(res.status).toBe(400);
});

it('no user → 401', async () => {
  mockUser = null;
  const res = await GET(req(`type=summary&playlist=${validPlaylist}`), ctx());
  expect(res.status).toBe(401);
});

it('type != summary → 400', async () => {
  const res = await GET(req(`type=dig-deeper&playlist=${validPlaylist}`), ctx());
  expect(res.status).toBe(400);
});

it('bad playlist → 400', async () => {
  const res = await GET(req(`type=summary&playlist=not-a-uuid`), ctx());
  expect(res.status).toBe(400);
});

it('outputFolder present → 400', async () => {
  const res = await GET(req(`type=summary&playlist=${validPlaylist}&outputFolder=/x`), ctx());
  expect(res.status).toBe(400);
});

it('outputFolder present but EMPTY (?outputFolder=) → 400 (PRESENCE rejects, not truthiness)', async () => {
  // Regression pin: `.get('outputFolder')` on an empty string is falsy and would silently pass this
  // check — must use `.has()` so mere presence of the param (even blank) 400s.
  const res = await GET(req(`type=summary&playlist=${validPlaylist}&outputFolder=`), ctx());
  expect(res.status).toBe(400);
});

it('missing playlist param (no `playlist` at all) → 400', async () => {
  const res = await GET(req(`type=summary`), ctx());
  expect(res.status).toBe(400);
});

it('invalid videoId → 400 before auth (mockUser stays null, no 401)', async () => {
  mockUser = null;
  const badReq = new Request(`http://localhost/api/pdf/bad%20id?type=summary&playlist=${validPlaylist}`);
  const badCtx = { params: Promise.resolve({ id: 'bad id' }) };
  const res = await GET(badReq, badCtx);
  expect(res.status).toBe(400);
});

it('committed (finalizing) → 503', async () => {
  mockIndexVideos = [{ ...promotedVideo, artifacts: { summaryMd: { status: 'committed' } } }];
  const res = await GET(req(`type=summary&playlist=${validPlaylist}`), ctx());
  expect(res.status).toBe(503);
});

it('absent (unknown video) → 404', async () => {
  mockIndexVideos = [];
  const res = await GET(req(`type=summary&playlist=${validPlaylist}`), ctx());
  expect(res.status).toBe(404);
});

it('lost md blob (promoted but blob null) → 409', async () => {
  mockMdBytes = null;
  const res = await GET(req(`type=summary&playlist=${validPlaylist}`), ctx());
  expect(res.status).toBe(409);
});

it('cache HIT (pdfs key present) streams inline application/pdf, generateDocPdf NOT called', async () => {
  pdfCacheBytes = Buffer.from('CACHED');
  const res = await GET(req(`type=summary&playlist=${validPlaylist}`), ctx());
  expect(res.status).toBe(200);
  expect(res.headers.get('content-type')).toBe('application/pdf');
  expect(res.headers.get('content-disposition')).toBe('inline');
  expect(res.headers.get('cache-control')).toBe('private, no-store');
  const body = Buffer.from(await res.arrayBuffer());
  expect(body.toString()).toBe('CACHED');
  expect(generateDocPdf).not.toHaveBeenCalled();
});

it('cache MISS calls generateDocPdf once and streams the result', async () => {
  pdfCacheBytes = null;
  (generateDocPdf as jest.Mock).mockResolvedValueOnce(Buffer.from('NEW'));
  const res = await GET(req(`type=summary&playlist=${validPlaylist}`), ctx());
  expect(res.status).toBe(200);
  expect(res.headers.get('content-type')).toBe('application/pdf');
  const body = Buffer.from(await res.arrayBuffer());
  expect(body.toString()).toBe('NEW');
  expect(generateDocPdf).toHaveBeenCalledTimes(1);
  // Pin `{ blobStore, returnBuffer: true }` exactly: returnBuffer is load-bearing — without it
  // generate-doc-pdf.ts returns `void` on success and the route would stream `undefined` as the
  // PDF body. Deleting `returnBuffer: true` from the route call must fail this assertion.
  expect(generateDocPdf).toHaveBeenCalledWith(
    expect.any(String), // rendered, nonce-free html
    { id: 'owner-1', indexKey: 'pk' }, // principal, per the mocked getPrincipalFromSession
    expect.stringMatching(/^pdfs\//), // content-addressed pdf cache key
    { blobStore: { get: mockBlobGet }, returnBuffer: true }, // the session bundle's blobStore, exactly
  );
});

it('typed PdfRendererUnavailable → 503, not 500', async () => {
  pdfCacheBytes = null;
  (generateDocPdf as jest.Mock).mockRejectedValueOnce(new PdfRendererUnavailable('no binary'));
  const res = await GET(req(`type=summary&playlist=${validPlaylist}`), ctx());
  expect(res.status).toBe(503);
});

it('propagates X-Magazine-Stale: 1 when resolve is stale', async () => {
  mockResolve = { status: 'ok', model: mockResolve.model, stale: true };
  pdfCacheBytes = Buffer.from('CACHED');
  const res = await GET(req(`type=summary&playlist=${validPlaylist}`), ctx());
  expect(res.status).toBe(200);
  expect(res.headers.get('x-magazine-stale')).toBe('1');
});

it('X-Magazine-Stale is absent when resolve is not stale', async () => {
  pdfCacheBytes = Buffer.from('CACHED');
  const res = await GET(req(`type=summary&playlist=${validPlaylist}`), ctx());
  expect(res.headers.get('x-magazine-stale')).toBeNull();
});

it('stray format/download params are ignored (still inline pdf)', async () => {
  pdfCacheBytes = Buffer.from('CACHED');
  const res = await GET(req(`type=summary&playlist=${validPlaylist}&format=md&download=1`), ctx());
  expect(res.status).toBe(200);
  expect(res.headers.get('content-type')).toBe('application/pdf');
  expect(res.headers.get('content-disposition')).toBe('inline');
});

it('resolve busy (in_flight) → 503', async () => {
  mockResolve = { status: 'busy' };
  const res = await GET(req(`type=summary&playlist=${validPlaylist}`), ctx());
  expect(res.status).toBe(503);
});

it('foreign/unowned playlist (resolveOwnedPlaylistKey → null) → generic 404', async () => {
  mockPlaylistKey = null;
  const res = await GET(req(`type=summary&playlist=${validPlaylist}`), ctx());
  expect(res.status).toBe(404);
});

describe('owner-scoped flight key + single-flight (H1 fix regression pins)', () => {
  it('runSingleFlight is called with an OWNER-scoped key ("<principal.id>/<indexKey>/<cacheKey>"), not the bare cache key', async () => {
    // A regression to the bare `key` (pre-H1-fix) would still pass every OTHER test in this file
    // (same owner throughout) — this is the only test that pins the actual flight-key SHAPE, so a
    // revert to `runSingleFlight(key, ...)` fails here even though functional behavior looks identical.
    pdfCacheBytes = null; // force a MISS so runSingleFlight is invoked at all
    const res = await GET(req(`type=summary&playlist=${validPlaylist}`), ctx());
    expect(res.status).toBe(200);
    expect(runSingleFlight).toHaveBeenCalledTimes(1);
    const flightKey = (runSingleFlight as jest.Mock).mock.calls[0][0] as string;
    // Principal per the mocked getPrincipalFromSession: `{ id: mockUser.id, indexKey: 'pk' }`.
    const principalId = mockUser!.id;
    const indexKey = 'pk';
    expect(flightKey.startsWith(`${principalId}/${indexKey}/`)).toBe(true);
    // The remainder after the owner prefix must be the real pdf cache key (`pdfs/...`) — proves the
    // key is owner-prefix + cache-key, not just the bare cache key on its own.
    expect(flightKey).toMatch(new RegExp(`^${principalId}/${indexKey}/pdfs/`));
  });

  it('two concurrent GETs for the SAME owner + same content (both cache MISS) collapse into ONE generateDocPdf call', async () => {
    pdfCacheBytes = null; // both requests see a MISS on the initial get
    let resolveGen!: (b: Buffer) => void;
    const genPromise = new Promise<Buffer>((resolve) => { resolveGen = resolve; });
    (generateDocPdf as jest.Mock).mockImplementationOnce(() => genPromise);

    const p1 = GET(req(`type=summary&playlist=${validPlaylist}`), ctx());
    const p2 = GET(req(`type=summary&playlist=${validPlaylist}`), ctx());

    // Drain the microtask queue fully (a macrotask boundary guarantees every already-resolved
    // intermediate await — auth, index read, resolveMagazineModel, the outer cache-miss get, the
    // in-slot recheck — has run) BEFORE we resolve the deliberately-held generateDocPdf promise.
    // Both GETs should have reached (and the second collapsed into) the single generateDocPdf call
    // by this point.
    await new Promise<void>((resolve) => setImmediate(resolve));

    expect(generateDocPdf).toHaveBeenCalledTimes(1); // the second GET collapsed into the first — no regression to a fresh render per request

    resolveGen(Buffer.from('COLLAPSED'));
    const [res1, res2] = await Promise.all([p1, p2]);

    expect(generateDocPdf).toHaveBeenCalledTimes(1); // still exactly once after both settle
    expect(res1.status).toBe(200);
    expect(res2.status).toBe(200);
    const body1 = Buffer.from(await res1.arrayBuffer()).toString();
    const body2 = Buffer.from(await res2.arrayBuffer()).toString();
    expect(body1).toBe('COLLAPSED');
    expect(body2).toBe('COLLAPSED');
  });
});
