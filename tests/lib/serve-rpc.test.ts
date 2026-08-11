import { callRpcBounded } from '@/lib/serve-rpc';
import { fakeRpcBuilder } from '../support/fake-rpc';

describe('callRpcBounded', () => {
  // The timeout branch warns by design; capture it so the suite output stays pristine AND the
  // operator-facing log is asserted rather than merely tolerated.
  let warn: jest.SpyInstance;
  beforeEach(() => { warn = jest.spyOn(console, 'warn').mockImplementation(() => {}); });
  afterEach(() => { warn.mockRestore(); });

  it('returns ok with the data when the call settles in time', async () => {
    const out = await callRpcBounded(
      (s) => fakeRpcBuilder({ data: [{ status: 'reserved' }], error: null }).abortSignal(s),
      1_000, 'reserve');
    expect(out).toEqual({ ok: true, data: [{ status: 'reserved' }] });
  });

  // The case the first plan draft got wrong: postgrest RETURNS the abort, it does not throw.
  it('reports timeout when the call outlives the budget, even though the client never throws', async () => {
    const out = await callRpcBounded(
      (s) => fakeRpcBuilder<never>(() => new Promise(() => {})).abortSignal(s),
      20, 'settle');
    expect(out).toEqual({ ok: false, reason: 'timeout' });
    expect(warn).toHaveBeenCalledWith('[serve-rpc] settle exceeded 20ms');
  });

  it('distinguishes a returned RPC error from a timeout', async () => {
    const cause = { message: 'boom', code: 'P0001' };
    const out = await callRpcBounded(
      (s) => fakeRpcBuilder({ data: null, error: cause }).abortSignal(s), 1_000, 'reserve');
    expect(out).toEqual({ ok: false, reason: 'error', cause });
  });

  it('folds a builder that THROWS into the union rather than letting it escape', async () => {
    // Task 6's callers branch on `!ok`; an escaping exception would bypass every one of them.
    const boom = new Error('network down');
    const out = await callRpcBounded<never>(() => { throw boom; }, 1_000, 'reserve');
    expect(out).toEqual({ ok: false, reason: 'error', cause: boom });
  });

  it('aborts the underlying request on timeout so it does not leak', async () => {
    let seen: AbortSignal | undefined;
    await callRpcBounded((s) => { seen = s; return fakeRpcBuilder<never>(() => new Promise(() => {})).abortSignal(s); },
      20, 'settle');
    expect(seen!.aborted).toBe(true);
  });
});
