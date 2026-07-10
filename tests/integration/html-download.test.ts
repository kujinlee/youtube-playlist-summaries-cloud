// tests/integration/html-download.test.ts
//
// Owner route (`app/api/html/[id]/route.ts` serveCloud) `format`/`download` query params + the MD
// short-circuit branch (D4/D5 money invariant), against a REAL local Supabase stack.
//
// Auth plumbing: the route builds its Supabase client via `createServerSupabase(cookies())`. We
// mock ONLY that plumbing layer (next/headers + @/lib/supabase/server) to hand the route a REAL
// signed-in session client from `signInAs` — everything downstream (RLS, resolveOwnedPlaylistKey,
// getStorageBundle, resolveMagazineModel, reserve_serve_model) runs for real. `lib/gemini` is
// mocked only to avoid a real network call on the charge path (C4); it is never invoked on the MD
// path (C2/C3), which is exactly the money invariant this file exists to prove.
import { SupabaseClient } from '@supabase/supabase-js';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo, seedSummaryBlob } from './helpers/seed';

jest.mock('next/headers', () => ({ cookies: async () => ({ getAll: () => [], set: () => {} }) }));

// mock*-prefixed per babel-plugin-jest-hoist's static-analysis whitelist (jest.mock factories are
// hoisted above this declaration) — same pattern as tests/integration/share-route.test.ts.
let mockClient: SupabaseClient;
jest.mock('@/lib/supabase/server', () => ({
  createServerSupabase: jest.fn(() => mockClient),
}));

jest.mock('@/lib/gemini', () => ({
  generateMagazineModel: jest.fn(async () => ({
    sections: [{ lead: 'L', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] }],
  })),
}));
import { generateMagazineModel } from '@/lib/gemini';

import { GET } from '@/app/api/html/[id]/route';

const svc = adminClient();
const MD = `# T\n**Channel:** C | **Duration:** 1:00\n\n## 1. Intro\nbody\n`;

// getStorageBundle({ supabaseClient }) selects the Supabase stores only when STORAGE_BACKEND==='supabase'.
const priorBackend = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { if (priorBackend === undefined) delete process.env.STORAGE_BACKEND; else process.env.STORAGE_BACKEND = priorBackend; });

beforeEach(async () => {
  (generateMagazineModel as jest.Mock).mockClear();
  // Clear the shared money tables and pin generous, deterministic guardrail headroom — this local
  // Supabase stack persists across test runs, so a stale spend_ledger row from an earlier file/run
  // could otherwise trip at_capacity here (mirrors serve-model-charge.test.ts's own beforeEach).
  await svc.from('serve_model_charge').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
  await svc.from('guardrail_config').update({
    daily_cap_cents: 500, magazine_est_cents: 6, max_serve_attempts: 5, lease_ttl_seconds: 180,
  }).eq('id', true);
});

let vidSeq = 0;
/** assertVideoId (lib/index-store.ts) requires `^[A-Za-z0-9_-]{1,20}$` — a plain `v-${randomUUID()}`
 *  (38 chars) fails it, so mint a short id here rather than relying on seedPromotedVideo's default. */
function shortVideoId(): string {
  return `v${Date.now().toString(36)}${(vidSeq++).toString(36)}`;
}

async function seedDoc(ownerId: string, title: string, status: 'promoted' | 'committed' = 'promoted') {
  const { playlistId, playlistKey } = await seedPlaylist(svc, ownerId);
  const { videoId, base } = await seedPromotedVideo(svc, { ownerId, playlistId, status, title, videoId: shortVideoId() });
  return { playlistId, playlistKey, videoId, base };
}

/** Seed an owner + promoted doc + MD blob, sign in as the owner, and arm the route's mocked
 *  createServerSupabase to hand back that REAL session client. */
async function ownerAndDoc(title = 'My Doc Title') {
  const u = await newUser();
  const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id, title);
  await seedSummaryBlob(svc, u.user.id, playlistKey, base, MD);
  const { client } = await signInAs(u.email, u.password);
  mockClient = client;
  return { u, playlistId, playlistKey, videoId, base };
}

function req(videoId: string, qs: string) {
  return new Request(`http://localhost/api/html/${videoId}?${qs}`);
}
function invoke(id: string) { return { params: Promise.resolve({ id }) }; }

describe('html-download (owner route, real DB)', () => {
  it('C1: owner GET (no format/download) → 200 html, CSP + private,no-store, nosniff, NO Referrer-Policy, no Content-Disposition (view regression)', async () => {
    const { playlistId, videoId } = await ownerAndDoc();
    const res = await GET(req(videoId, `playlist=${playlistId}&type=summary`), invoke(videoId));
    expect(res.status).toBe(200);
    expect(res.headers.get('content-type')).toMatch(/text\/html/);
    expect(res.headers.get('cache-control')).toBe('private, no-store');
    expect(res.headers.get('content-security-policy')).toMatch(/nonce-/);
    expect(res.headers.get('x-content-type-options')).toBe('nosniff'); // NEW
    expect(res.headers.get('referrer-policy')).toBeNull();             // still absent
    expect(res.headers.get('content-disposition')).toBeNull();         // still absent

    // Full header-set assertion: prove no unintended extra header appears, and that the only
    // keys present are the legacy set (content-type, cache-control) PLUS the new
    // x-content-type-options and the html-branch content-security-policy. Pattern-match the CSP
    // nonce value rather than hard-coding it (generateNonce() is random per request).
    const keys = [...res.headers.keys()].sort();
    expect(keys).toEqual(
      ['cache-control', 'content-security-policy', 'content-type', 'x-content-type-options'].sort(),
    );
    expect(res.headers.get('content-security-policy')).toMatch(/'nonce-[A-Za-z0-9+/=]+'/);
  });

  it('C2: owner GET format=md&download=1 → 200 text/markdown, attachment filename="<base>.md"; no reserve_serve_model call; spend_ledger unchanged', async () => {
    const { playlistId, videoId, base } = await ownerAndDoc();
    const rpcSpy = jest.spyOn(SupabaseClient.prototype, 'rpc');
    const { data: ledgerBefore } = await svc.from('spend_ledger').select('*').order('day');

    const res = await GET(req(videoId, `playlist=${playlistId}&type=summary&format=md&download=1`), invoke(videoId));

    expect(res.status).toBe(200);
    expect(res.headers.get('content-type')).toMatch(/text\/markdown/);
    expect(res.headers.get('x-content-type-options')).toBe('nosniff');
    expect(res.headers.get('content-disposition')).toMatch(new RegExp(`attachment; filename="${base}\\.md"`));
    for (const call of rpcSpy.mock.calls) expect(call[0]).not.toBe('reserve_serve_model'); // D4 money invariant
    const { data: ledgerAfter } = await svc.from('spend_ledger').select('*').order('day');
    expect(ledgerAfter ?? []).toEqual(ledgerBefore ?? []);
    expect(generateMagazineModel).not.toHaveBeenCalled();
    rpcSpy.mockRestore();
  });

  it('C3: owner GET format=md (no download) → 200 text/plain; charset=utf-8, nosniff, no Content-Disposition; no charge', async () => {
    const { playlistId, videoId } = await ownerAndDoc();
    const rpcSpy = jest.spyOn(SupabaseClient.prototype, 'rpc');
    const { data: ledgerBefore } = await svc.from('spend_ledger').select('*').order('day');

    const res = await GET(req(videoId, `playlist=${playlistId}&type=summary&format=md`), invoke(videoId));

    expect(res.status).toBe(200);
    expect(res.headers.get('content-type')).toBe('text/plain; charset=utf-8');
    expect(res.headers.get('x-content-type-options')).toBe('nosniff');
    expect(res.headers.get('content-disposition')).toBeNull();
    for (const call of rpcSpy.mock.calls) expect(call[0]).not.toBe('reserve_serve_model'); // D4 money invariant
    const { data: ledgerAfter } = await svc.from('spend_ledger').select('*').order('day');
    expect(ledgerAfter ?? []).toEqual(ledgerBefore ?? []);
    expect(generateMagazineModel).not.toHaveBeenCalled();
    rpcSpy.mockRestore();
  });

  it('C4: owner GET format=html&download=1 → 200 html attachment; goes through resolveMagazineModel (charge-once semantics preserved)', async () => {
    const { playlistId, videoId, base } = await ownerAndDoc();
    const rpcSpy = jest.spyOn(SupabaseClient.prototype, 'rpc');

    const res = await GET(req(videoId, `playlist=${playlistId}&type=summary&format=html&download=1`), invoke(videoId));

    expect(res.status).toBe(200);
    expect(res.headers.get('content-type')).toMatch(/text\/html/);
    expect(res.headers.get('x-content-type-options')).toBe('nosniff');
    expect(res.headers.get('content-disposition')).toMatch(new RegExp(`attachment; filename="${base}\\.html"`));
    const reserveCalls = rpcSpy.mock.calls.filter((c) => c[0] === 'reserve_serve_model');
    expect(reserveCalls.length).toBe(1); // D5: charge-once via the EXISTING owner money path
    expect(generateMagazineModel).toHaveBeenCalledTimes(1);
    rpcSpy.mockRestore();
  });

  it('C5: format=pdf → 400 (validated after type; ?type=bad&format=pdf → the type-400 fires first)', async () => {
    const { playlistId, videoId } = await ownerAndDoc();
    const res1 = await GET(req(videoId, `playlist=${playlistId}&type=summary&format=pdf`), invoke(videoId));
    expect(res1.status).toBe(400);

    const res2 = await GET(req(videoId, `type=bad&format=pdf`), invoke(videoId)); // no playlist either — type-400 must win
    expect(res2.status).toBe(400);
    const body2 = await res2.json();
    expect(body2.error).toBe('unsupported or missing type'); // proves the type check ran before the format check
  });

  it('C5b: duplicate format params (e.g. format=html&format=pdf) → 400 invalid format, not the first value', async () => {
    const { playlistId, videoId } = await ownerAndDoc();

    const res1 = await GET(req(videoId, `playlist=${playlistId}&type=summary&format=html&format=pdf`), invoke(videoId));
    expect(res1.status).toBe(400);
    const body1 = await res1.json();
    expect(body1.error).toBe('invalid format');

    const res2 = await GET(req(videoId, `playlist=${playlistId}&type=summary&format=md&format=pdf`), invoke(videoId));
    expect(res2.status).toBe(400);
    const body2 = await res2.json();
    expect(body2.error).toBe('invalid format');
  });

  it('C6: owner GET format=md when the MD blob is missing behind promoted → 409 repair needed', async () => {
    const u = await newUser();
    const { playlistId, videoId } = await seedDoc(u.user.id, 'No Blob Title');
    // deliberately no seedSummaryBlob call — the MD blob is missing behind the 'promoted' status.
    const { client } = await signInAs(u.email, u.password);
    mockClient = client;

    const res = await GET(req(videoId, `playlist=${playlistId}&type=summary&format=md`), invoke(videoId));
    expect(res.status).toBe(409);
  });
});
