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
import { fakeRpcBuilder } from '../../support/fake-rpc';
import { GoogleGenerativeAIFetchError } from '@google/generative-ai';

// Jest's default per-test timeout is 5000ms and this repo sets no override — the SAME number as the
// real SERVE_*_RPC_TIMEOUT_MS. A hanging-RPC test would race Jest itself. Shrink the two RPC budgets
// for this file only; the real values stay asserted by tests/lib/serve-budget.test.ts and by the
// migration pin. This file tests the PLUMBING, not the numbers.
jest.mock('@/lib/serve-budget', () => ({
  ...jest.requireActual('@/lib/serve-budget'),
  SERVE_RESERVE_RPC_TIMEOUT_MS: 20,
  SERVE_SETTLE_RPC_TIMEOUT_MS: 20,
}));

jest.mock('@/lib/gemini', () => {
  const LEAD = 'GEN';
  const generateMagazineModel = jest.fn(async (sections: Array<{ title: string }>) => ({
    sections: sections.map(() => ({ lead: LEAD, bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] })),
  }));
  return {
    generateMagazineModel,
    // Delegates, so existing assertions on generateMagazineModel — including
    // mockImplementationOnce overrides — still fire.
    generateMagazineModelForServe: jest.fn((sections: unknown, language: unknown, _budget: unknown, opts: unknown) =>
      (generateMagazineModel as unknown as (a: unknown, b: unknown, c: unknown) => unknown)(sections, language, opts)),
  };
});
import { generateMagazineModel, generateMagazineModelForServe } from '@/lib/gemini';

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
    // A chainable thenable, not a bare async fn: production calls `.abortSignal(signal)` before
    // awaiting, and a plain promise has no such method.
    rpc: jest.fn(() => fakeRpcBuilder({ data: [{ status: rpcData, release_token: null }], error: null })),
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
    // The money guard probes tryGet before reserving. These are RESERVE-STATUS MAPPING tests, so the
    // fake reports provable absence: the guard is a no-op here and every case still reaches the RPC
    // exactly as before. Deliberately NOT delegating to getMock — that would consume a scripted call
    // and shift every subsequent answer. Unreadable behaviour is covered in
    // tests/integration/serve-model-unreadable.test.ts.
    tryGet: jest.fn(async () => ({ ok: false as const, reason: 'absent' as const })),
    put: putMock,
    exists: jest.fn(async () => false),
    delete: jest.fn(async () => {}),
    putStaged: jest.fn(async (p: Principal, key: string) => ({ principal: p, tempKey: key, finalKey: key })),
    promote: jest.fn(async () => {}),
    deletePrefix: jest.fn(async () => {}),
    list: jest.fn(async () => []),
    // Unused by these reserve-status mapping tests. A plain stub for the same reason tryGet above
    // is one: delegating to copyBlob would consume scripted `get` answers and shift every
    // subsequent case. The copy contract is covered in tests/lib/storage/blob-store-copy.contract.test.ts.
    copy: jest.fn(async () => ({ ok: true as const, already: false })),
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

beforeEach(() => {
  (generateMagazineModel as jest.Mock).mockClear();
  // Clear the wrapper too, or it stays dirty across tests and `not.toHaveBeenCalled()`
  // becomes order-dependent.
  (generateMagazineModelForServe as jest.Mock).mockClear();
});

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

describe('resolveMagazineModel — bounded RPCs (#46)', () => {
  /** A fake whose reserve/settle behaviour is scripted per RPC name. */
  function scriptedSupabase(script: (fn: string) => ReturnType<typeof fakeRpcBuilder>): SupabaseClient {
    return { rpc: jest.fn((fn: string) => script(fn)) } as unknown as SupabaseClient;
  }
  const reserved = () =>
    fakeRpcBuilder({ data: [{ status: 'reserved', release_token: 'tok' }], error: null });
  const hangs = () => fakeRpcBuilder<never>(() => new Promise(() => {}));

  // Restore the release gate or it leaks into every later test in this worker.
  // Mirrors tests/integration/serve-doc-materialize.test.ts and gemini-failure.test.ts.
  const prevGate = process.env.CLOUD_GEMINI_RELEASE_VERIFIED;
  afterEach(() => { process.env.CLOUD_GEMINI_RELEASE_VERIFIED = prevGate; });

  // The bounded paths log by design; capture so the suite output stays pristine.
  let errorLog: jest.SpyInstance;
  let warnLog: jest.SpyInstance;
  beforeEach(() => {
    errorLog = jest.spyOn(console, 'error').mockImplementation(() => {});
    warnLog = jest.spyOn(console, 'warn').mockImplementation(() => {});
  });
  afterEach(() => { errorLog.mockRestore(); warnLog.mockRestore(); });

  it('a reserve TIMEOUT returns busy and makes no Gemini call', async () => {
    const client = scriptedSupabase(() => hangs());
    const res = await resolveMagazineModel(baseArgs(client, fakeBlobStore([null])));
    expect(res).toEqual({ status: 'busy' });
    // The empty-paid-lease state: charged, an attempt burned, and NO producer. Loud on purpose.
    expect(generateMagazineModelForServe).not.toHaveBeenCalled();
    expect(errorLog).toHaveBeenCalledWith('[serve-model] reserve timed out — possible empty paid lease');
  });

  it('a reserve ERROR still throws, exactly as today', async () => {
    const client = scriptedSupabase(() => fakeRpcBuilder({ data: null, error: { message: 'nope' } }));
    await expect(resolveMagazineModel(baseArgs(client, fakeBlobStore([null]))))
      .rejects.toMatchObject({ message: 'nope' });
  });

  it('retries the settle ONCE when the release-path settle times out', async () => {
    let settles = 0;
    const client = scriptedSupabase((fn) => {
      if (fn === 'reserve_serve_model') return reserved();
      settles++;
      return settles === 1 ? hangs() : fakeRpcBuilder({ data: true, error: null });
    });
    (generateMagazineModelForServe as jest.Mock).mockImplementationOnce(async () => {
      throw new GoogleGenerativeAIFetchError('overloaded', 503, 'Service Unavailable');
    });
    process.env.CLOUD_GEMINI_RELEASE_VERIFIED = 'true';   // else releaseGateOpen() is false
    await expect(resolveMagazineModel(baseArgs(client, fakeBlobStore([null])))).rejects.toThrow();
    expect(settles).toBe(2);
  });

  it('does NOT retry the settle on the kept path', async () => {
    let settles = 0;
    const client = scriptedSupabase((fn) => {
      if (fn === 'reserve_serve_model') return reserved();
      settles++;
      return hangs();   // hangs every time
    });
    const res = await resolveMagazineModel(baseArgs(client, fakeBlobStore([null])));
    expect(res.status).toBe('ok');                        // a lost keep does not fail the request
    expect(settles).toBe(1);   // a lost keep is benign; only a lost refund is money
  });
});
