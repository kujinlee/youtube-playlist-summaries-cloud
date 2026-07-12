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

import { GET } from '@/app/api/pdf/[id]/route';
import { generateDocPdf } from '@/lib/pdf/generate-doc-pdf';
import { PdfRendererUnavailable } from '@/lib/pdf/pdf-renderer-error';

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
