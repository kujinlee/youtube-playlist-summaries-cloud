// tests/api/html-dig-serve.test.ts
// The cloud html route awaits cookies() from next/headers — MUST mock it or the route throws
// before reaching the behavior (every existing cloud route test does this; see tests/api/dig-cloud-route.test.ts:13).
jest.mock('next/headers', () => ({ cookies: jest.fn(async () => ({ getAll: () => [], set: () => {} })) }));

// Mocking mechanism note (T5, per T3 gotcha): jest.spyOn(namespace, 'fn') on `import * as X` THROWS
// "Cannot redefine property" under this repo's Next16/SWC jest — so these modules are mocked via
// jest.mock(...) automock + (fn as jest.Mock) instead of jest.spyOn, per tests/api/dig-cloud-route.test.ts
// and tests/lib/dig/cloud/enqueue-dig-core.test.ts precedent. All assertions are identical to the brief;
// only the mock-install mechanism differs. serve-summary-core is partially mocked (spread actual) so
// resolveAndParse — used by the (unmocked) summary branch — stays real.
jest.mock('@/lib/dig/cloud/load-dig-for-serve', () => ({ loadDigForServe: jest.fn() }));
jest.mock('@/lib/html-doc/serve-summary-core', () => ({
  ...jest.requireActual('@/lib/html-doc/serve-summary-core'),
  loadSummaryForServe: jest.fn(),
}));
jest.mock('@/lib/supabase/server', () => ({ createServerSupabase: jest.fn() }));

import { GET } from '@/app/api/html/[id]/route';
import { loadDigForServe } from '@/lib/dig/cloud/load-dig-for-serve';
import { loadSummaryForServe } from '@/lib/html-doc/serve-summary-core';
import { createServerSupabase } from '@/lib/supabase/server';

const OLD = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { process.env.STORAGE_BACKEND = OLD; });
afterEach(() => jest.clearAllMocks());

// isAnon: profiles.is_anonymous value returned for a signed-in user. Undefined defaults to false
// (registered) so pre-existing tests that call mockAuth({id:'u'}) keep working; the dedicated
// null-row test below exercises the route's real fail-closed path separately.
function mockAuth(user: { id: string } | null, isAnon?: boolean) {
  (createServerSupabase as jest.Mock).mockReturnValue({
    auth: { getUser: async () => ({ data: { user } }) },
    from: () => ({ select: () => ({ eq: () => ({ single: async () => ({ data: user ? { is_anonymous: isAnon ?? false } : null }) }) }) }),
  });
}
const PL = '0d6f76b5-a1ec-4616-aa74-ad8cd4d7e660';
const url = (extra = '') => `http://x/api/html/v?playlist=${PL}&type=dig-deeper${extra}`;
const params = { params: Promise.resolve({ id: 'v' }) };

it('serves dig html with the summary CSP', async () => {
  mockAuth({ id: 'u' });
  (loadDigForServe as jest.Mock).mockResolvedValue({
    ok: true, summary: { title: 'T', sections: [{ numeral: '1', title: 'A', prose: 'p', timeRange: { startSec: 65, endSec: 120, label: 'l', url: 'https://youtu.be/v?t=65s' } }] } as never,
    envelope: null, dug: [{ sectionId: 65, startSec: 65, title: 'A', bodyMarkdown: 'body', generatedAt: 'g', genVersion: 3, slides: [] }] as never,
    base: 'base', title: 'T', language: 'en',
  } as never);
  const res = await GET(new Request(url()), params);
  expect(res.status).toBe(200);
  expect(res.headers.get('Content-Type')).toContain('text/html');
  expect(res.headers.get('Content-Security-Policy')).toContain("script-src 'nonce-");
  expect(await res.text()).toContain('body');
});

it('401 for an anonymous request', async () => {
  mockAuth(null);
  const res = await GET(new Request(url()), params);
  expect(res.status).toBe(401);
});

it('rejects format=md on dig with 400', async () => {
  mockAuth({ id: 'u' });
  const res = await GET(new Request(url('&format=md')), params);
  expect(res.status).toBe(400);
});

it('rejects outputFolder on cloud dig with 400 — even empty (presence-based, behavior 14)', async () => {
  mockAuth({ id: 'u' });
  const res = await GET(new Request(url('&outputFolder=')), params); // empty value still present
  expect(res.status).toBe(400);
});

it('propagates loader 404 (no dig content)', async () => {
  mockAuth({ id: 'u' });
  (loadDigForServe as jest.Mock).mockResolvedValue({ ok: false, status: 404, error: 'not found' } as never);
  const res = await GET(new Request(url()), params);
  expect(res.status).toBe(404);
});

it('still serves summary — reaches the summary branch, not the type gate (regression)', async () => {
  mockAuth({ id: 'u' });
  // Mock the summary loader so the summary branch resolves deterministically. Without this the real
  // resolveOwnedPlaylistKey runs against the bare auth mock (no `.from`) → TypeError → 500, and the
  // assertion would pass for the WRONG reason. A 404 here proves control reached loadSummaryForServe
  // (the summary branch), i.e. the type gate did NOT reject type=summary with a 400.
  (loadSummaryForServe as jest.Mock).mockResolvedValue({ ok: false, status: 404, error: 'not found' } as never);
  const res = await GET(new Request(`http://x/api/html/v?playlist=${PL}&type=summary`), params);
  expect(res.status).toBe(404);
  expect(loadSummaryForServe).toHaveBeenCalled();  // summary branch entered
  expect(res.status).not.toBe(400);                // not the unsupported-type gate
});

it('renders the cloud dig doc INTERACTIVE (trigger + poll engine, no SSE)', async () => {
  mockAuth({ id: 'u' }, false); // registered
  (loadDigForServe as jest.Mock).mockResolvedValue({
    ok: true,
    summary: { title: 'T', sections: [
      { numeral: '1', title: 'A', prose: 'p', timeRange: { startSec: 65, endSec: 120, label: 'l', url: 'https://youtu.be/v?t=65s' } },
      { numeral: '2', title: 'B', prose: 'q', timeRange: { startSec: 120, endSec: 200, label: 'l', url: 'https://youtu.be/v?t=120s' } },
    ] } as never,
    envelope: null, dug: [{ sectionId: 65, startSec: 65, title: 'A', bodyMarkdown: 'body', generatedAt: 'g', genVersion: 3, slides: [] }] as never,
    base: 'base', title: 'T', language: 'en',
  } as never);
  const res = await GET(new Request(url()), params);
  const html = await res.text();
  expect(res.status).toBe(200);
  expect(html).toContain('<a class="dig-trigger" data-section="120">'); // un-dug section 2 is clickable
  expect(html).toContain('dig-state?playlist=');                        // cloud poll engine injected
  expect(html).not.toContain('EventSource');                            // not the local SSE script
});

it('anonymous user (profiles.is_anonymous=true): dig triggers are pre-disabled spans', async () => {
  mockAuth({ id: 'u' }, true); // anonymous per profiles
  (loadDigForServe as jest.Mock).mockResolvedValue({
    ok: true,
    summary: { title: 'T', sections: [
      { numeral: '1', title: 'A', prose: 'p', timeRange: { startSec: 65, endSec: 120, label: 'l', url: 'https://youtu.be/v?t=65s' } },
    ] } as never,
    envelope: null, dug: [] as never, base: 'base', title: 'T', language: 'en',
  } as never);
  const html = await (await GET(new Request(url()), params)).text();
  expect(html).toContain('aria-disabled="true" title="Create an account to dig deeper"');
  expect(html).not.toContain('<a class="dig-trigger" data-section="65">');
});

it('unresolved profile (null row) fails CLOSED → triggers pre-disabled', async () => {
  // user present but profiles read returns null → treated as anonymous (fail-closed).
  (createServerSupabase as jest.Mock).mockReturnValue({
    auth: { getUser: async () => ({ data: { user: { id: 'u' } } }) },
    from: () => ({ select: () => ({ eq: () => ({ single: async () => ({ data: null }) }) }) }),
  });
  (loadDigForServe as jest.Mock).mockResolvedValue({
    ok: true,
    summary: { title: 'T', sections: [
      { numeral: '1', title: 'A', prose: 'p', timeRange: { startSec: 65, endSec: 120, label: 'l', url: 'https://youtu.be/v?t=65s' } },
    ] } as never,
    envelope: null, dug: [] as never, base: 'base', title: 'T', language: 'en',
  } as never);
  const html = await (await GET(new Request(url()), params)).text();
  expect(html).toContain('aria-disabled="true" title="Create an account to dig deeper"'); // fail-closed
});
