// Status-mapping seam tests for resolveMagazineModel (Stage 1F-a Task 6 money-path depth).
// Unlike tests/integration/serve-doc-materialize.test.ts, these do NOT hit a real Supabase project:
// `supabaseClient` is a FAKE whose `.rpc('reserve_serve_model', …)` resolves a scripted status, and
// `blobStore` is a FAKE whose `.get()` answers are scripted per-call. This isolates the pure mapping
// resolveMagazineModel performs from each `reserve_serve_model` status to its ResolveResult, and locks
// "only 'reserved' ever calls generateMagazineModel".
import type { SupabaseClient } from '@supabase/supabase-js';
import { resolveMagazineModel } from '@/lib/html-doc/serve-doc';
import { GENERATOR_VERSION } from '@/lib/html-doc/render';
import type { BlobStore } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';
import type { ParsedSummary } from '@/lib/html-doc/types';

jest.mock('@/lib/gemini', () => ({
  generateMagazineModel: jest.fn(async (sections: Array<{ title: string }>) => ({
    sections: sections.map(() => ({ lead: 'GEN', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] })),
  })),
}));
import { generateMagazineModel } from '@/lib/gemini';

const principal: Principal = { id: 'u1', indexKey: 'pk1' };
const parsed = (): ParsedSummary => ({
  title: 'T', channel: null, duration: null, url: null, lang: 'EN', videoId: 'v', tldr: null, takeaways: [],
  sections: [{ numeral: '1', title: 'Intro', prose: 'body', timeRange: null }], sourceMd: 'v.md',
});

/** Fake session client: only `.rpc()` is used by resolveMagazineModel. `reserve_serve_model` is a
 *  `returns table(status, release_token)` RPC, so supabase-js `.rpc()` yields a row ARRAY — the caller
 *  reads `data[0].status` (Task 5). Wrap the scripted status in the single-row shape. */
function fakeSupabase(rpcData: string): SupabaseClient {
  return {
    rpc: jest.fn(async () => ({ data: [{ status: rpcData, release_token: null }], error: null })),
  } as unknown as SupabaseClient;
}

/** Fake BlobStore whose `.get()` answers come from a per-call queue (index 0 = the initial
 *  existing-cache check; index 1 = the in_flight re-read, when reached). Running past the queue
 *  returns null. `.put()` is recorded so the 'reserved' seam test can assert an upsert happened. */
function fakeBlobStore(getQueue: Array<Buffer | null>): BlobStore & { getMock: jest.Mock; putMock: jest.Mock } {
  let i = 0;
  const getMock = jest.fn(async () => (i < getQueue.length ? getQueue[i++] : null));
  const putMock = jest.fn(async () => {});
  return {
    getMock, putMock,
    get: getMock,
    put: putMock,
    exists: jest.fn(async () => false),
    delete: jest.fn(async () => {}),
    putStaged: jest.fn(async (p: Principal, key: string) => ({ principal: p, tempKey: key, finalKey: key })),
    promote: jest.fn(async () => {}),
    deletePrefix: jest.fn(async () => {}),
    list: jest.fn(async () => []),
  };
}

function freshEnvelopeBuffer(lead: string): Buffer {
  return Buffer.from(JSON.stringify({
    sourceMd: 'v.md',
    generatedAt: '2026-01-01T00:00:00.000Z',
    sourceSections: ['Intro'], // must match parsed().sections titles for isFresh() to accept it
    generatorVersion: GENERATOR_VERSION,
    model: { sections: [{ lead, bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] }] },
  }), 'utf-8');
}

const baseArgs = (supabaseClient: SupabaseClient, blobStore: BlobStore) => ({
  supabaseClient, blobStore, principal,
  playlistId: 'p1', videoId: 'v1', base: 'v1', parsed: parsed(), language: 'en' as const,
});

beforeEach(() => { (generateMagazineModel as jest.Mock).mockClear(); });

describe('resolveMagazineModel — reserve_serve_model status mapping (seam)', () => {
  it('denied → {status:"denied"}, generateMagazineModel NOT called', async () => {
    const blobStore = fakeBlobStore([null]); // no cache → falls through to the reserve RPC
    const res = await resolveMagazineModel(baseArgs(fakeSupabase('denied'), blobStore));
    expect(res).toEqual({ status: 'denied' });
    expect(generateMagazineModel).not.toHaveBeenCalled();
  });

  it('attempts_exhausted → {status:"attempts_exhausted"}, generateMagazineModel NOT called', async () => {
    const blobStore = fakeBlobStore([null]);
    const res = await resolveMagazineModel(baseArgs(fakeSupabase('attempts_exhausted'), blobStore));
    expect(res).toEqual({ status: 'attempts_exhausted' });
    expect(generateMagazineModel).not.toHaveBeenCalled();
  });

  it('in_flight, model NOT landed on re-read → {status:"busy"}, generateMagazineModel NOT called', async () => {
    // Both the initial check and the in_flight re-read see no cache — lease is held elsewhere.
    const blobStore = fakeBlobStore([null, null]);
    const res = await resolveMagazineModel(baseArgs(fakeSupabase('in_flight'), blobStore));
    expect(res).toEqual({ status: 'busy' });
    expect(generateMagazineModel).not.toHaveBeenCalled();
    expect(blobStore.getMock).toHaveBeenCalledTimes(2); // proves the re-read actually happened
  });

  it('in_flight, model LANDED meanwhile on re-read → {status:"ok", model}, generateMagazineModel NOT called', async () => {
    // Initial check misses; the in_flight re-read finds a fresh envelope another attempt just wrote.
    const blobStore = fakeBlobStore([null, freshEnvelopeBuffer('LANDED')]);
    const res = await resolveMagazineModel(baseArgs(fakeSupabase('in_flight'), blobStore));
    expect(res.status).toBe('ok');
    if (res.status === 'ok') expect(res.model.sections[0].lead).toBe('LANDED'); // served from the re-read, not regenerated
    expect(generateMagazineModel).not.toHaveBeenCalled();
  });

  it('reserved → generateMagazineModel IS called, model upserted, {status:"ok"} (bonus: only "reserved" generates)', async () => {
    const blobStore = fakeBlobStore([null]); // no cache → reserve → reserved
    const res = await resolveMagazineModel(baseArgs(fakeSupabase('reserved'), blobStore));
    expect(res.status).toBe('ok');
    expect(generateMagazineModel).toHaveBeenCalledTimes(1);
    if (res.status === 'ok') expect(res.model.sections[0].lead).toBe('GEN'); // the generated (mock) model, not a cache
    expect(blobStore.putMock).toHaveBeenCalledTimes(1); // writeModelEnvelope persisted the new model
  });
});
