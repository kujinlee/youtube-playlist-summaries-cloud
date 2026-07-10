const validPlaylist = '11111111-1111-1111-1111-111111111111';
const validVideo = 'vid123';
const promotedSummaryMd = `# T\n**Channel:** C | **Duration:** 1:00\n\n## 1. Intro\nbody\n`;

let mockUser: { id: string } | null;
let mockIndexVideos: any[];
let mockMdBytes: Buffer | null;
let mockResolve: any;
let mockBlobGet: jest.Mock;

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
jest.mock('@/lib/html-doc/serve-doc', () => ({ resolveMagazineModel: async () => mockResolve }));
// Playlist resolution helper (owner-asserted playlistId → playlist_key) is mocked to succeed by default:
jest.mock('@/lib/storage/serve-playlist', () => ({ resolveOwnedPlaylistKey: async () => 'pk' }));

import { GET } from '@/app/api/html/[id]/route';
import { getStorageBundle } from '@/lib/storage/resolve';
import { createServerSupabase } from '@/lib/supabase/server';
const mockGetStorageBundle = getStorageBundle as jest.Mock;

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
  mockGetStorageBundle.mockClear();
  (createServerSupabase as jest.Mock).mockClear();
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
  expect(csp).not.toMatch(/unsafe-/);
  // B20: the bundle was built from the exact session client createServerSupabase returned — never bare.
  const sessionClient = (createServerSupabase as jest.Mock).mock.results[0].value;
  expect(mockGetStorageBundle).toHaveBeenCalledWith({ supabaseClient: sessionClient });
});

it('B11: no session → 401', async () => { mockUser = null; expect((await GET(req(`playlist=${validPlaylist}&type=summary`), params)).status).toBe(401); });
it('B15: non-UUID playlist → 400 (before any DB call)', async () => { expect((await GET(req('playlist=not-a-uuid&type=summary'), params)).status).toBe(400); });
it('B14: type != summary → 400 (cloud rejects dig-deeper)', async () => { expect((await GET(req(`playlist=${validPlaylist}&type=dig-deeper`), params)).status).toBe(400); });
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
