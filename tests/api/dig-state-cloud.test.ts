// tests/api/dig-state-cloud.test.ts
// Cloud branch awaits cookies() — mock next/headers (repo convention).
jest.mock('next/headers', () => ({ cookies: jest.fn(async () => ({ getAll: () => [], set: () => {} })) }));

// Mocking mechanism note (T6, per T3 gotcha carried through T5): jest.spyOn(namespace, 'fn') on
// `import * as X` THROWS "Cannot redefine property" under this repo's Next16/SWC jest — so these
// modules are mocked via jest.mock(...) automock + (fn as jest.Mock) instead of jest.spyOn, per
// tests/api/dig-cloud-route.test.ts and tests/api/html-dig-serve.test.ts precedent in this same
// route family. All assertions are identical to the brief; only the mock-install mechanism differs.
jest.mock('@/lib/html-doc/serve-summary-core', () => ({
  ...jest.requireActual('@/lib/html-doc/serve-summary-core'),
  loadSummaryForServe: jest.fn(),
}));
jest.mock('@/lib/supabase/server', () => ({ createServerSupabase: jest.fn() }));

import { GET } from '@/app/api/videos/[id]/dig-state/route';
import { loadSummaryForServe } from '@/lib/html-doc/serve-summary-core';
import { createServerSupabase } from '@/lib/supabase/server';
import { DIG_GENERATOR_VERSION as V } from '@/lib/dig/generate';

const OLD = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { process.env.STORAGE_BACKEND = OLD; });
afterEach(() => jest.clearAllMocks());

const PL = '0d6f76b5-a1ec-4616-aa74-ad8cd4d7e660';
const params = { params: Promise.resolve({ id: 'v' }) };
function mockAuth(user: { id: string } | null) {
  (createServerSupabase as jest.Mock).mockReturnValue({ auth: { getUser: async () => ({ data: { user } }) } });
}
// loadSummaryForServe is reused wholesale — mock its OK result (gate passed) with a fake bundle.
function mockLoadOk(base: string, keys: string[]) {
  (loadSummaryForServe as jest.Mock).mockResolvedValue({
    ok: true, base, mdBytes: Buffer.from('#'), mdKey: `${base}.md`, title: 'T',
    principal: { id: 'o', indexKey: 'k' } as never, playlistId: PL, video: { id: 'v', language: 'en' } as never,
    bundle: { blobStore: { list: async (_p: unknown, prefix: string) => keys.filter((k) => k.startsWith(prefix)) } } as never,
  } as never);
}

it('lists dug section ids ascending, excluding stale versions', async () => {
  mockAuth({ id: 'u' });
  mockLoadOk('base', [`dig/base/200.r${V}.md`, `dig/base/65.r${V}.md`, `dig/base/9.r${V - 1}.md`]);
  const res = await GET(new Request(`http://x/api/videos/v/dig-state?playlist=${PL}`), params);
  expect(res.status).toBe(200);
  expect(await res.json()).toEqual({ sectionIds: [65, 200] }); // stale r{V-1} excluded, sorted asc
});

it('returns {sectionIds:[]} when nothing is dug (200, not 404)', async () => {
  mockAuth({ id: 'u' });
  mockLoadOk('base', []);
  const res = await GET(new Request(`http://x/api/videos/v/dig-state?playlist=${PL}`), params);
  expect(res.status).toBe(200);
  expect(await res.json()).toEqual({ sectionIds: [] });
});

it('propagates the summary gate: 404 not-owner / unpromoted / unknown video', async () => {
  mockAuth({ id: 'u' });
  (loadSummaryForServe as jest.Mock).mockResolvedValue({ ok: false, status: 404, error: 'not found' } as never);
  const res = await GET(new Request(`http://x/api/videos/v/dig-state?playlist=${PL}`), params);
  expect(res.status).toBe(404);
});

it('propagates the summary gate: 503 while the summary is finalizing (committed)', async () => {
  mockAuth({ id: 'u' });
  (loadSummaryForServe as jest.Mock).mockResolvedValue({ ok: false, status: 503, error: 'not ready, retry' } as never);
  const res = await GET(new Request(`http://x/api/videos/v/dig-state?playlist=${PL}`), params);
  expect(res.status).toBe(503);
});

it('401 for anon (before any loader call)', async () => {
  mockAuth(null);
  const res = await GET(new Request(`http://x/api/videos/v/dig-state?playlist=${PL}`), params);
  expect(res.status).toBe(401);
  expect(loadSummaryForServe).not.toHaveBeenCalled();
});

it('400 for a non-UUID playlist (before auth)', async () => {
  mockAuth({ id: 'u' });
  const res = await GET(new Request('http://x/api/videos/v/dig-state?playlist=not-a-uuid'), params);
  expect(res.status).toBe(400);
});
