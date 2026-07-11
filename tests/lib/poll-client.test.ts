import { rollup, pollUntilTerminal } from '@/lib/job-queue/poll-client';
import type { PlaylistJobRow } from '@/lib/storage/job-queue';

const row = (status: string): PlaylistJobRow =>
  ({ jobId: 'j', videoId: 'v', status: status as any, progressPhase: null, attempts: 0, error: null });

describe('rollup', () => {
  it('empty set is not terminal', () => {
    const r = rollup([]); expect(r.total).toBe(0); expect(r.terminal).toBe(false);
  });
  it('all-terminal is terminal; counts by status', () => {
    const r = rollup([row('completed'), row('failed'), row('dead_letter'), row('cancelled')]);
    expect(r.total).toBe(4); expect(r.terminal).toBe(true);
    expect(r.completed).toBe(1); expect(r.failed).toBe(1);
  });
  it('any active keeps it non-terminal', () => {
    expect(rollup([row('completed'), row('active')]).terminal).toBe(false);
  });
  it('queued status is counted and not terminal', () => {
    const r = rollup([row('queued'), row('completed')]);
    expect(r.queued).toBe(1);
    expect(r.terminal).toBe(false);
  });
});

describe('pollUntilTerminal', () => {
  const noSleep = () => Promise.resolve();
  it('resolves done when rows reach terminal', async () => {
    let n = 0;
    const fetchRows = async () => (n++ < 1 ? [row('active')] : [row('completed')]);
    const res = await pollUntilTerminal(fetchRows, { sleep: noSleep });
    expect(res).toMatchObject({ done: true });
  });
  it('keeps polling while total is 0, then completes', async () => {
    let n = 0;
    const fetchRows = async () => (n++ < 2 ? [] : [row('completed')]);
    const res = await pollUntilTerminal(fetchRows, { sleep: noSleep });
    expect(res).toMatchObject({ done: true });
  });
  it('fails after maxConsecutiveErrors (3 errors in a row)', async () => {
    const fetchRows = async () => { throw new Error('boom'); };
    const res = await pollUntilTerminal(fetchRows, { sleep: noSleep, maxConsecutiveErrors: 3 });
    expect(res).toMatchObject({ failed: true });
  });
  it('resets the consecutive-error counter on a successful fetch (non-consecutive errors never fail)', async () => {
    // 3 throws total, but each is immediately followed by a success, so the
    // error streak never reaches 2-in-a-row, let alone maxConsecutiveErrors.
    // If the implementation counted TOTAL errors instead of resetting on
    // success, the 3rd throw below would hit maxConsecutiveErrors (3) and
    // resolve {failed} before ever reaching the terminal row.
    const steps: Array<'active' | 'throw' | 'completed'> = [
      'active', 'throw', 'active', 'throw', 'active', 'throw', 'active', 'completed',
    ];
    let i = 0;
    const fetchRows = async () => {
      const step = steps[i++];
      if (step === 'throw') throw new Error('boom');
      return [row(step)];
    };
    const res = await pollUntilTerminal(fetchRows, { sleep: noSleep, maxConsecutiveErrors: 3 });
    expect(i).toBe(steps.length); // every step was consumed; no early bail-out
    expect(res).toMatchObject({ done: true });
  });
  it('times out if never terminal', async () => {
    let clock = 0;
    const res = await pollUntilTerminal(async () => [row('active')], {
      sleep: async () => { clock += 3000; }, timeoutMs: 5000, now: () => clock,
    });
    expect(res).toMatchObject({ timedOut: true });
  });
  it('backs off geometrically to the cap (behavior #9)', async () => {
    const delays: number[] = []; let clock = 0; let polls = 0;
    await pollUntilTerminal(
      async () => (polls++ < 5 ? [row('active')] : [row('completed')]),
      { intervalMs: 2000, maxIntervalMs: 10000, timeoutMs: 10 ** 9,
        now: () => clock, sleep: async (ms) => { delays.push(ms); clock += ms; } });
    expect(delays.slice(0, 4)).toEqual([2000, 4000, 8000, 10000]); // doubles, then clamps at cap
  });
});

describe('pollUntilTerminal extensions', () => {
  const row = (status: string) =>
    ({ jobId: 'j', videoId: 'v', status, progressPhase: null, attempts: 0, error: null }) as any;
  const fast = { intervalMs: 1, maxIntervalMs: 1, sleep: async () => {}, now: () => 0 };

  it('fires onProgress after each successful fetch incl. terminal', async () => {
    const seq = [[row('queued')], [row('active')], [row('completed')]];
    let i = 0;
    const totals: number[] = [];
    const res = await pollUntilTerminal(async () => seq[i++], { ...fast, onProgress: (s) => totals.push(s.rollup.total) });
    expect(res).toMatchObject({ done: true });
    expect(totals).toEqual([1, 1, 1]);
  });

  it('does not fire onProgress on a failed fetch', async () => {
    const fetchRows = jest.fn().mockRejectedValueOnce(new Error('net')).mockResolvedValueOnce([row('completed')]);
    const onProgress = jest.fn();
    await pollUntilTerminal(fetchRows, { ...fast, maxConsecutiveErrors: 5, onProgress });
    expect(onProgress).toHaveBeenCalledTimes(1);
  });

  it('an onProgress that throws does not count as a fetch error', async () => {
    const seq = [[row('active')], [row('completed')]];
    let i = 0;
    const res = await pollUntilTerminal(async () => seq[i++], { ...fast, maxConsecutiveErrors: 1, onProgress: () => { throw new Error('boom'); } });
    expect(res).toMatchObject({ done: true }); // not { failed }
  });

  it('isFatal stops immediately with fatal:true and no retry', async () => {
    class Fatal extends Error {}
    const fetchRows = jest.fn().mockRejectedValue(new Fatal('401'));
    const res = await pollUntilTerminal(fetchRows, { ...fast, maxConsecutiveErrors: 5, isFatal: (e) => e instanceof Fatal });
    expect(res).toEqual({ failed: true, error: expect.any(String), fatal: true });
    expect(fetchRows).toHaveBeenCalledTimes(1); // no retry
  });

  it('non-fatal errors still retry to failure', async () => {
    const fetchRows = jest.fn().mockRejectedValue(new Error('net'));
    const res = await pollUntilTerminal(fetchRows, { ...fast, maxConsecutiveErrors: 3, isFatal: () => false });
    expect(res).toMatchObject({ failed: true });
    expect((res as any).fatal).toBeUndefined();
    expect(fetchRows).toHaveBeenCalledTimes(3);
  });

  // Abort tests use an INCREMENTING `now` + finite `timeoutMs` so the RED run (current
  // code has no signal handling) terminates via timeout instead of hanging forever
  // (R2 Medium). On the implemented code, abort wins before timeout.
  const abortable = () => { let t = 0; return { intervalMs: 1, maxIntervalMs: 1, timeoutMs: 500, sleep: async () => {}, now: () => (t += 50) }; };

  it('aborts via signal and resolves { aborted: true }', async () => {
    const ac = new AbortController();
    let calls = 0;
    const fetchRows = jest.fn(async () => { calls++; if (calls === 2) ac.abort(); return [row('active')]; });
    const res = await pollUntilTerminal(fetchRows, { ...abortable(), signal: ac.signal });
    expect(res).toEqual({ aborted: true });
  });

  it('a pre-aborted signal never fetches', async () => {
    const ac = new AbortController(); ac.abort();
    const fetchRows = jest.fn(async () => [row('active')]);
    const res = await pollUntilTerminal(fetchRows, { ...abortable(), signal: ac.signal });
    expect(res).toEqual({ aborted: true });
    expect(fetchRows).not.toHaveBeenCalled();
  });

  it('aborting during the wait resolves { aborted: true } without another fetch', async () => {
    const ac = new AbortController();
    let resolveSleep!: () => void;
    const sleep = () => new Promise<void>((r) => { resolveSleep = r; });
    const fetchRows = jest.fn(async () => [row('active')]);
    let t = 0;
    const p = pollUntilTerminal(fetchRows, { intervalMs: 1, maxIntervalMs: 1, timeoutMs: 500, sleep, now: () => (t += 10), signal: ac.signal });
    await Promise.resolve(); await Promise.resolve(); // let fetch #1 run and the loop park on sleep
    ac.abort();
    resolveSleep();
    const res = await p;
    expect(res).toEqual({ aborted: true });
    expect(fetchRows).toHaveBeenCalledTimes(1); // no fetch after abort
  });

  it('works with none of the new options (backward compatible)', async () => {
    const res = await pollUntilTerminal(async () => [row('completed')], fast);
    expect(res).toMatchObject({ done: true });
  });
});
