import { runOnce, echoHandler } from '@/lib/job-queue/worker-runner';
import { runWorkerLoop, makeSweepGate } from '@/worker/main';
import type { JobQueue } from '@/lib/storage/job-queue';
import type { JobHandler } from '@/lib/job-queue/worker-runner';

// MEASURED 2026-09-18 against prod (`uykwcybxqgewmbltroxf`, plan=free): the worker emitted
// ~79,800 REST requests/day and they were ONE HUNDRED PERCENT of the project's traffic — an
// exact 25/25 pair of `sweep_expired_leases` and `claim_next_job` in every sampled window, with
// auth/realtime/storage all at zero. At a measured 921 bytes per response (919 B headers + 2 B
// body) that is 2.13-2.28 GB a month, i.e. 43-46% of a 5 GB free egress allowance, spent on an
// empty queue. (See worker/main.ts's SWEEP_MS comment for the keep-alive caveat on that range.)
//
// Half of it bought nothing. A lease is 120s (`RunnerOpts.leaseSeconds ?? 120`), so sweeping on
// every 2s poll looked for expiries SIXTY TIMES more often than one can occur. This suite pins
// the sweep to its own cadence while leaving the claim poll untouched, so job-start latency is
// unchanged.
//
// These live in tests/lib/ ON PURPOSE: jest.config.ts's testMatch covers tests/lib but NOT
// tests/integration, so only this location is guarded by the `verify` check in CI. The gate is
// pure by design (a predicate over an injected clock) precisely so it can be tested there.

const idleQueue = () => ({
  sweepExpired: jest.fn(async () => 0),
  claim: jest.fn(async () => null),
}) as unknown as JobQueue & { sweepExpired: jest.Mock; claim: jest.Mock };

// A sweep that is due, performed, and acknowledged — the ordinary cycle, written once so the
// cadence tests below read as cadence rather than as protocol.
function sweepCycle(policy: { due: () => boolean; onSwept: () => void }): boolean {
  if (!policy.due()) return false;
  policy.onSwept();
  return true;
}

describe('makeSweepGate', () => {
  // Breaks this catches: initialising the cursor to `now()` instead of "never swept". That
  // would make a freshly deployed worker skip its first sweep — exactly the moment the previous
  // machine's SIGTERM drain may have stranded a lease, so it is the worst possible time to wait.
  test('is due on the very first call, so a just-started worker sweeps immediately', () => {
    const t = { now: 1_000_000 };
    const gate = makeSweepGate(60_000, () => t.now);
    expect(gate.due()).toBe(true);
  });

  // Breaks this catches: a gate that is always due (the `if` removed, or the comparison
  // inverted) — i.e. the egress regression this whole change exists to remove.
  test('stops being due for the rest of the interval once a sweep is acknowledged', () => {
    const t = { now: 1_000_000 };
    const gate = makeSweepGate(60_000, () => t.now);
    sweepCycle(gate);
    t.now += 2_000;   // one 2s claim poll later
    expect(gate.due()).toBe(false);
    t.now += 55_000;  // 57s in total — still short of the interval
    expect(gate.due()).toBe(false);
  });

  // ⚠ THE DANGEROUS ONE. If the cursor advanced on every DUE CHECK rather than on an
  // acknowledged sweep, then under a 2s poll `now - last` is forever 2s, never reaches 60s, and
  // the sweep NEVER RUNS AGAIN for the life of the process. Lease reclamation would be silently
  // dead and nothing would report it — a crashed job would simply hang.
  test('becomes due again once the interval elapses, even when polled rapidly throughout', () => {
    const t = { now: 1_000_000 };
    const gate = makeSweepGate(60_000, () => t.now);
    let swept = 0;
    for (let elapsed = 0; elapsed <= 180_000; elapsed += 2_000) { // 3 minutes of 2s polls
      if (sweepCycle(gate)) swept++;
      t.now += 2_000;
    }
    // t=0 (first call) plus t=60s, t=120s, t=180s. Hand-derived, not computed by the gate.
    expect(swept).toBe(4);
  });

  test('a shorter interval comes due proportionally more often', () => {
    const t = { now: 0 };
    const gate = makeSweepGate(10_000, () => t.now);
    let swept = 0;
    for (let elapsed = 0; elapsed <= 60_000; elapsed += 2_000) {
      if (sweepCycle(gate)) swept++;
      t.now += 2_000;
    }
    expect(swept).toBe(7); // 0s, 10s, 20s, 30s, 40s, 50s, 60s
  });

  // r1 Medium (Codex). Break this catches: advancing the cursor on `due()` instead of on
  // `onSwept()`. A sweep that THROWS would then consume the whole 60s window without having
  // reclaimed anything, so one transient network blip pushes worst-case crash recovery from
  // ~180s to ~240s, and blips landing on window boundaries stretch it further. Asking twice
  // without acknowledging must stay due — the window is spent by a sweep, not by an intention.
  test('stays due until a sweep is ACKNOWLEDGED, not merely attempted', () => {
    const t = { now: 1_000_000 };
    const gate = makeSweepGate(60_000, () => t.now);

    expect(gate.due()).toBe(true);
    t.now += 2_000;
    expect(gate.due()).toBe(true);  // the attempt failed; the window must not have been spent
    t.now += 2_000;
    expect(gate.due()).toBe(true);

    gate.onSwept();                 // now one actually landed
    expect(gate.due()).toBe(false);
  });

  // r1 Low (Codex). Break this catches: `t - lastSweptAt < intervalMs` with no floor. An NTP
  // step backwards makes that delta NEGATIVE, so it compares as "inside the window" and sweeps
  // are suppressed until the wall clock catches up — potentially minutes past the promised
  // bound. A backwards jump must fail SAFE (sweep sooner), never silent (sweep later).
  test('comes due immediately if the clock steps backwards', () => {
    const t = { now: 1_000_000 };
    const gate = makeSweepGate(60_000, () => t.now);
    sweepCycle(gate);
    expect(gate.due()).toBe(false);

    t.now -= 300_000; // NTP corrects the host five minutes backwards
    expect(gate.due()).toBe(true);
  });
});

describe('runOnce honours the sweep policy', () => {
  const policy = (due: boolean) => ({ due: () => due, onSwept: jest.fn() });

  // Break this catches: reverting worker-runner.ts to an unconditional `await queue.sweepExpired()`.
  test('skips the sweep when not due, but still claims', async () => {
    const q = idleQueue();
    const outcome = await runOnce(q, echoHandler, { workerId: 'w1', sweepPolicy: policy(false) });

    expect(q.sweepExpired).not.toHaveBeenCalled();
    expect(q.claim).toHaveBeenCalledTimes(1); // gating the sweep must NOT gate the poll
    expect(outcome).toBe('idle');
  });

  test('performs the sweep when due, and acknowledges it', async () => {
    const q = idleQueue();
    const p = policy(true);
    await runOnce(q, echoHandler, { workerId: 'w1', sweepPolicy: p });
    expect(q.sweepExpired).toHaveBeenCalledTimes(1);
    expect(p.onSwept).toHaveBeenCalledTimes(1);
  });

  // r1 Medium (Codex), at the runOnce boundary. Break this catches: acknowledging the sweep
  // before awaiting it, or wrapping it in a try/catch that acknowledges anyway. A sweep that
  // threw reclaimed nothing, so it must not spend the window — the next poll has to retry.
  test('does NOT acknowledge a sweep that threw', async () => {
    const q = {
      sweepExpired: jest.fn(async () => { throw new Error('transient PostgREST failure'); }),
      claim: jest.fn(async () => null),
    } as unknown as JobQueue & { sweepExpired: jest.Mock; claim: jest.Mock };
    const p = policy(true);

    await expect(runOnce(q, echoHandler, { workerId: 'w1', sweepPolicy: p })).rejects.toThrow(
      'transient PostgREST failure',
    );
    expect(p.onSwept).not.toHaveBeenCalled();
  });

  // Break this catches: defaulting the policy to NOT-DUE. Every existing caller — the integration
  // suites, and any future one — relies on runOnce sweeping. A `?? false` here would disable
  // lease reclamation repo-wide while every one of those tests still passed.
  test('sweeps by default when no policy is supplied, preserving the original contract', async () => {
    const q = idleQueue();
    await runOnce(q, echoHandler, { workerId: 'w1' });
    expect(q.sweepExpired).toHaveBeenCalledTimes(1);
  });
});

describe('runWorkerLoop wires the gate in by default', () => {
  // Break this catches: the gate existing but never reaching production — a passing unit test for
  // makeSweepGate proves nothing if worker/main.ts does not actually pass it to runOnce. This is
  // the only test here that measures the thing the egress bill responds to: the RATIO of sweeps
  // to claims over a real run of the shipped loop.
  test('emits far fewer sweeps than claims over a fast idle run, with NO gate injected', async () => {
    const ac = new AbortController();
    let claims = 0;
    let sweeps = 0;
    const queue = {
      sweepExpired: async () => { sweeps++; return 0; },
      claim: async () => {
        claims++;
        if (claims >= 25) ac.abort();
        return null; // idle every time — the state that generated the measured traffic
      },
    } as unknown as JobQueue;
    const handler: JobHandler = async () => ({ ok: true });

    await runWorkerLoop({
      queue,
      handler,
      shutdownSignal: ac.signal,
      workerId: 'cadence-test',
      pollMs: 1, // compress 25 polls into milliseconds; the default 2000 would take ~50s
    });

    expect(claims).toBeGreaterThanOrEqual(25);
    // 25 polls inside a few milliseconds fall well within one 60s sweep window, so the startup
    // sweep is the only one that may fire. Before this change sweeps === claims.
    expect(sweeps).toBe(1);
  });

  // r1 Medium (Codex), end-to-end through the SHIPPED loop rather than the gate in isolation.
  // Break this catches: the loop spending the sweep window on an attempt that failed. A worker
  // whose every sweep throws must keep retrying on each poll, not fall silent for 60s at a time
  // — otherwise a transient outage suspends lease reclamation far past the stated bound while
  // the loop looks perfectly healthy in the logs.
  test('retries the sweep on the next poll when it throws, rather than spending the window', async () => {
    const ac = new AbortController();
    let sweepAttempts = 0;
    let claims = 0;
    const queue = {
      sweepExpired: async () => { sweepAttempts++; throw new Error('transient PostgREST failure'); },
      claim: async () => { claims++; return null; },
    } as unknown as JobQueue;
    const handler: JobHandler = async () => ({ ok: true });

    // The throw escapes runOnce into runWorkerLoop's catch, which logs and backs off; silence
    // the expected noise so the suite output stays pristine.
    const err = jest.spyOn(console, 'error').mockImplementation(() => {});
    const stop = setTimeout(() => ac.abort(), 50);
    await runWorkerLoop({ queue, handler, shutdownSignal: ac.signal, workerId: 'sweep-retry', pollMs: 1 });
    clearTimeout(stop);
    err.mockRestore();

    expect(sweepAttempts).toBeGreaterThan(1); // NOT stuck at 1 for the whole 60s window
    expect(claims).toBe(0); // the throw precedes the claim, so no poll completed
  });
});
