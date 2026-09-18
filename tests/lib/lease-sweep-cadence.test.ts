import { runOnce, echoHandler } from '@/lib/job-queue/worker-runner';
import { runWorkerLoop, makeSweepGate } from '@/worker/main';
import type { JobQueue } from '@/lib/storage/job-queue';
import type { JobHandler } from '@/lib/job-queue/worker-runner';

// MEASURED 2026-09-18 against prod (`uykwcybxqgewmbltroxf`, plan=free): the worker emitted
// ~79,800 REST requests/day and they were ONE HUNDRED PERCENT of the project's traffic — an
// exact 25/25 pair of `sweep_expired_leases` and `claim_next_job` in every sampled window, with
// auth/realtime/storage all at zero. At 919 bytes of response headers apiece that is 1.5-2.2 GB
// a month against a 5 GB free egress allowance, spent on an empty queue.
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

describe('makeSweepGate', () => {
  // Breaks this catches: initialising the cursor to `now()` instead of "never swept". That
  // would make a freshly deployed worker skip its first sweep — exactly the moment the previous
  // machine's SIGTERM drain may have stranded a lease, so it is the worst possible time to wait.
  test('opens on the very first call, so a just-started worker sweeps immediately', () => {
    let t = 1_000_000;
    const gate = makeSweepGate(60_000, () => t);
    expect(gate()).toBe(true);
  });

  // Breaks this catches: a gate that opens every time (the `if` removed, or the comparison
  // inverted) — i.e. the egress regression this whole change exists to remove.
  test('stays shut for the rest of the interval', () => {
    let t = 1_000_000;
    const gate = makeSweepGate(60_000, () => t);
    gate();
    t += 2_000;   // one 2s claim poll later
    expect(gate()).toBe(false);
    t += 55_000;  // 57s in total — still short of the interval
    expect(gate()).toBe(false);
  });

  // ⚠ THE DANGEROUS ONE. If the cursor is advanced on every call rather than only when the gate
  // opens, then under a 2s poll `now - last` is forever 2s, never reaches 60s, and the sweep
  // NEVER RUNS AGAIN for the life of the process. Lease reclamation would be silently dead and
  // nothing would report it — a crashed job would simply hang. A gate that re-opens on schedule
  // under a fast poll is the property that rules that out.
  test('re-opens once the interval has elapsed, even when polled rapidly throughout', () => {
    let t = 1_000_000;
    const gate = makeSweepGate(60_000, () => t);
    let opened = 0;
    for (let elapsed = 0; elapsed <= 180_000; elapsed += 2_000) { // 3 minutes of 2s polls
      if (gate()) opened++;
      t += 2_000;
    }
    // t=0 (first call) plus t=60s, t=120s, t=180s. Hand-derived, not computed by the gate.
    expect(opened).toBe(4);
  });

  test('a shorter interval opens proportionally more often', () => {
    let t = 0;
    const gate = makeSweepGate(10_000, () => t);
    let opened = 0;
    for (let elapsed = 0; elapsed <= 60_000; elapsed += 2_000) {
      if (gate()) opened++;
      t += 2_000;
    }
    expect(opened).toBe(7); // 0s, 10s, 20s, 30s, 40s, 50s, 60s
  });
});

describe('runOnce honours the sweep gate', () => {
  // Break this catches: reverting worker-runner.ts to an unconditional `await queue.sweepExpired()`.
  test('skips the sweep when the gate is shut, but still claims', async () => {
    const q = idleQueue();
    const outcome = await runOnce(q, echoHandler, { workerId: 'w1', shouldSweep: () => false });

    expect(q.sweepExpired).not.toHaveBeenCalled();
    expect(q.claim).toHaveBeenCalledTimes(1); // gating the sweep must NOT gate the poll
    expect(outcome).toBe('idle');
  });

  test('performs the sweep when the gate is open', async () => {
    const q = idleQueue();
    await runOnce(q, echoHandler, { workerId: 'w1', shouldSweep: () => true });
    expect(q.sweepExpired).toHaveBeenCalledTimes(1);
  });

  // Break this catches: defaulting the gate to CLOSED. Every existing caller — the integration
  // suites, and any future one — relies on runOnce sweeping. A `?? false` here would disable
  // lease reclamation repo-wide while every one of those tests still passed.
  test('sweeps by default when no gate is supplied, preserving the original contract', async () => {
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
});
