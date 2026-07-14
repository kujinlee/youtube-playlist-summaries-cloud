const validPlaylist = '11111111-1111-1111-1111-111111111111';
const validVideo = 'vid123';
const promotedSummaryMd = `# T\n**Channel:** C | **Duration:** 1:00\n\n## 1. Intro\nbody\n`;

let mockUser: { id: string } | null;
let mockIndexVideos: any[];
let mockMdBytes: Buffer | null;
let mockResolve: any;
let mockBlobGet: jest.Mock;
let mockPlaylistKey: string | null;

jest.mock('next/headers', () => ({ cookies: async () => ({ getAll: () => [], set: () => {} }) }));
// A stable session-client sentinel so the B20 test can assert getStorageBundle received THIS client.
jest.mock('@/lib/supabase/server', () => ({
  createServerSupabase: jest.fn(() => ({ __session: true, auth: { getUser: async () => ({ data: { user: mockUser } }) } })),
}));
// B20: getStorageBundle MUST be called with { supabaseClient: <session client> }. The mock THROWS if the
// session client is absent, so a bare getStorageBundle() (service-role default) fails the test.
jest.mock('@/lib/storage/resolve', () => {
  const actual = jest.requireActual('@/lib/storage/resolve');
  return {
    ...actual,
    getStorageBundle: jest.fn((arg?: { supabaseClient?: unknown }) => {
      if (!arg || !arg.supabaseClient) throw new Error('B20: getStorageBundle called without a session supabaseClient');
      return {
        metadataStore: { readIndex: async () => ({ videos: mockIndexVideos }) },
        blobStore: { get: mockBlobGet },
      };
    }),
    getPrincipalFromSession: () => ({ id: mockUser?.id, indexKey: 'pk' }),
  };
});
jest.mock('@/lib/html-doc/serve-doc', () => ({ resolveMagazineModel: jest.fn(async () => mockResolve) }));
// Playlist resolution helper (owner-asserted playlistId → playlist_key) is mocked to succeed by default;
// mockPlaylistKey is mutable so tests can simulate a foreign/unowned playlist (resolves to null).
jest.mock('@/lib/storage/serve-playlist', () => ({ resolveOwnedPlaylistKey: async () => mockPlaylistKey }));

import { GET } from '@/app/api/html/[id]/route';
import { getStorageBundle } from '@/lib/storage/resolve';
import { createServerSupabase } from '@/lib/supabase/server';
import { resolveMagazineModel } from '@/lib/html-doc/serve-doc';
const mockGetStorageBundle = getStorageBundle as jest.Mock;
const mockResolveMagazineModel = resolveMagazineModel as jest.Mock;

function req(qs: string) { return new Request(`http://localhost/api/html/${validVideo}?${qs}`); }
const params = { params: Promise.resolve({ id: validVideo }) };

// Mirrors the worker row (summary-handler.ts:149-164): top-level summaryMd + language + the promoted artifact.
const promotedVideo = { id: validVideo, language: 'en', summaryMd: `${validVideo}.md`, artifacts: { summaryMd: { key: `${validVideo}.md`, status: 'promoted' } } };

beforeEach(() => {
  process.env.STORAGE_BACKEND = 'supabase';
  mockUser = { id: 'owner-1' };
  mockIndexVideos = [promotedVideo];
  mockMdBytes = Buffer.from(promotedSummaryMd, 'utf-8');
  mockBlobGet = jest.fn(async () => mockMdBytes);
  mockResolve = { status: 'ok', model: { sections: [{ lead: 'L', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] }] } };
  mockPlaylistKey = 'pk';
  mockGetStorageBundle.mockClear();
  (createServerSupabase as jest.Mock).mockClear();
  mockResolveMagazineModel.mockClear();
});
afterEach(() => { delete process.env.STORAGE_BACKEND; });

it('B8/B16/B17/B20: owner gets 200 HTML with a coherent nonce CSP + private no-store, bundle built from the SESSION client', async () => {
  const res = await GET(req(`playlist=${validPlaylist}&type=summary`), params);
  expect(res.status).toBe(200);
  expect(res.headers.get('content-type')).toMatch(/text\/html/);
  expect(res.headers.get('cache-control')).toBe('private, no-store');
  const csp = res.headers.get('content-security-policy')!;
  const nonce = csp.match(/'nonce-([^']+)'/)![1];
  const html = await res.text();
  for (const tag of html.match(/<script[^>]*>/g) ?? []) expect(tag).toContain(`nonce="${nonce}"`);
  // CSP regression guard: style-src has no unsafe-inline, so a dropped style-nonce silently breaks rendering.
  const styleTags = html.match(/<style[^>]*>/g) ?? [];
  expect(styleTags.length).toBeGreaterThan(0);
  for (const tag of styleTags) expect(tag).toContain(`nonce="${nonce}"`);
  expect(csp).not.toMatch(/unsafe-/);
  // B20: the bundle was built from the exact session client createServerSupabase returned — never bare.
  const sessionClient = (createServerSupabase as jest.Mock).mock.results[0].value;
  expect(mockGetStorageBundle).toHaveBeenCalledWith({ supabaseClient: sessionClient });
});

it('B11: no session → 401', async () => { mockUser = null; expect((await GET(req(`playlist=${validPlaylist}&type=summary`), params)).status).toBe(401); });
it('B15: non-UUID playlist → 400 (before any DB call)', async () => { expect((await GET(req('playlist=not-a-uuid&type=summary'), params)).status).toBe(400); });
// B14 superseded by feat/cloud-dig-serving: cloud now accepts type=dig-deeper (see
// tests/api/html-dig-serve.test.ts for full dig-deeper coverage). The type gate still rejects any
// other unsupported/missing type — pinned here with a value that is neither summary nor dig-deeper.
it('B14: type not summary/dig-deeper → 400', async () => { expect((await GET(req(`playlist=${validPlaylist}&type=bogus`), params)).status).toBe(400); });
it('URL contract: cloud rejects outputFolder → 400', async () => { expect((await GET(req(`outputFolder=/x&type=summary`), params)).status).toBe(400); });
it('B13: unknown video → 404', async () => { mockIndexVideos = []; expect((await GET(req(`playlist=${validPlaylist}&type=summary`), params)).status).toBe(404); });
it('B12: summary committed (finalizing) → 503, not 404', async () => {
  mockIndexVideos = [{ ...promotedVideo, artifacts: { summaryMd: { status: 'committed' } } }];
  expect((await GET(req(`playlist=${validPlaylist}&type=summary`), params)).status).toBe(503);
});
it('B13: no summary artifact → 404', async () => {
  mockIndexVideos = [{ id: validVideo, language: 'en', summaryMd: null }];
  expect((await GET(req(`playlist=${validPlaylist}&type=summary`), params)).status).toBe(404);
});
it('B13b: promoted but MD blob null → repair-needed 409', async () => {
  mockMdBytes = null;
  expect((await GET(req(`playlist=${validPlaylist}&type=summary`), params)).status).toBe(409);
});
it('B6b: resolve busy (in_flight) → 503', async () => { mockResolve = { status: 'busy' }; expect((await GET(req(`playlist=${validPlaylist}&type=summary`), params)).status).toBe(503); });
it('reserve denied → 404 (generic, no leak)', async () => { mockResolve = { status: 'denied' }; expect((await GET(req(`playlist=${validPlaylist}&type=summary`), params)).status).toBe(404); });
it('at_capacity → 503', async () => { mockResolve = { status: 'at_capacity' }; expect((await GET(req(`playlist=${validPlaylist}&type=summary`), params)).status).toBe(503); });
it('attempts_exhausted → 503', async () => { mockResolve = { status: 'attempts_exhausted' }; expect((await GET(req(`playlist=${validPlaylist}&type=summary`), params)).status).toBe(503); });
it('a storage/logical-key error with statusCode===400 surfaces as 400 (not 500) after the cloud split', async () => {
  // e.g. assertLogicalKey rejecting a bad key inside blobStore.get → { statusCode: 400 }.
  mockBlobGet = jest.fn(async () => { throw Object.assign(new Error('invalid logical key'), { statusCode: 400 }); });
  expect((await GET(req(`playlist=${validPlaylist}&type=summary`), params)).status).toBe(400);
});

it('auth boundary: foreign/unowned playlist (resolveOwnedPlaylistKey → null) → generic 404, no existence leak', async () => {
  // Simulates a playlistId that is well-formed (passes the UUID regex) but not owned by this user —
  // resolveOwnedPlaylistKey returns null in that case. The route's `if (!playlistKey) return 404` line
  // otherwise has no coverage at any layer. Must be indistinguishable from other 404s (no owner/existence leak).
  mockPlaylistKey = null;
  const res = await GET(req(`playlist=${validPlaylist}&type=summary`), params);
  expect(res.status).toBe(404);
  const body = await res.json();
  expect(body).toEqual({ error: 'not found' });
});

it('money coherence: base is derived from the promoted MD key, not videoId, while videoId is passed through unchanged', async () => {
  // Real worker keys MD as `${padSerial(serial)}_${slug}.md` (e.g. "0001_intro.md"), which is NOT videoId.
  // The cache (resolveMagazineModel `base`) must key on that stable serial_slug base while the reserve-RPC
  // charge keys on videoId. Pin both independently so a regression that swaps base<->videoId is caught.
  const distinctVideoId = 'abcDEF12345'; // clearly different from the MD key below, 11-char YouTube-style id
  mockIndexVideos = [{
    id: distinctVideoId,
    language: 'en',
    summaryMd: '0001_intro.md',
    artifacts: { summaryMd: { key: '0001_intro.md', status: 'promoted' } },
  }];
  const res = await GET(new Request(`http://localhost/api/html/${distinctVideoId}?playlist=${validPlaylist}&type=summary`), { params: Promise.resolve({ id: distinctVideoId }) });
  expect(res.status).toBe(200);
  expect(mockResolveMagazineModel).toHaveBeenCalledTimes(1);
  const call = mockResolveMagazineModel.mock.calls[0][0];
  expect(call.base).toBe('0001_intro');
  expect(call.videoId).toBe(distinctVideoId);
});
