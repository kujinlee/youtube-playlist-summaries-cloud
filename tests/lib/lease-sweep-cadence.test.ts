import { runOnce, echoHandler, DEFAULT_LEASE_SECONDS } from '@/lib/job-queue/worker-runner';
import { runWorkerLoop, makeSweepGate, SWEEP_MS } from '@/worker/main';
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

/** A queue whose SWEEP is broken while CLAIM is perfectly healthy — the asymmetry that makes the
 *  r1 High bite. sweep_expired_leases and claim_next_job are separate functions with separate
 *  grants and separate signatures, so one can break alone. */
const throwingSweepQueue = () => ({
  sweepExpired: jest.fn(async () => { throw new Error('transient PostgREST failure'); }),
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
  test('comes due immediately if an INJECTED clock steps backwards', () => {
    const t = { now: 1_000_000 };
    const gate = makeSweepGate(60_000, () => t.now);
    sweepCycle(gate);
    expect(gate.due()).toBe(false);

    t.now -= 300_000; // NTP corrects the host five minutes backwards
    expect(gate.due()).toBe(true);
  });

  // r1 Medium (Claude half 1). ⚠ EVERY other case here INJECTS a clock, so the default parameter
  // — the only clock production ever uses — was exercised by nothing, and the mutation
  // `performance.now() -> Date.now()` SURVIVED the whole 2,831-test suite. A fix bought in one
  // review round could be undone in the next by anyone tidying a default argument, with green CI.
  //
  // This case kills it: it moves the WALL clock backwards and asserts the gate does not notice.
  // A monotonic clock is unaffected and stays not-due; Date.now() would see a negative delta,
  // hit the fail-safe floor above, and flip to due. The floor is good defence AND is precisely
  // why nothing else can tell the two apart.
  test('the DEFAULT clock is monotonic — a wall-clock step backwards does not move it', () => {
    const gate = makeSweepGate(60_000); // no injected clock: the production path
    sweepCycle(gate);
    expect(gate.due()).toBe(false);

    const realDateNow = Date.now;
    Date.now = () => realDateNow() - 3_600_000; // host wall clock jumps back an hour
    try {
      expect(gate.due()).toBe(false); // still inside the window — monotonic time did not move
    } finally {
      Date.now = realDateNow;
    }
  });

  test('the DEFAULT clock still advances, so the gate really does re-open in real time', async () => {
    const gate = makeSweepGate(2); // 2ms window
    sweepCycle(gate);
    expect(gate.due()).toBe(false);
    await new Promise((r) => setTimeout(r, 20));
    expect(gate.due()).toBe(true);
  });
});

// r1 Medium (BOTH Claude halves, independently). Every safety claim on this branch rests on one
// relationship — the sweep interval is shorter than the lease it guards — and that relationship
// lived only in prose, in two literals in two modules. MEASURED: SWEEP_MS 60s -> 600s survived;
// 60s -> 30 MINUTES also survived, tsc clean, all gates green, while the documented "~180s to
// recovery" silently became ~32 minutes.
//
// CLAUDE.md: "A decision becomes a gate by asserting the world still matches it." This is that
// assertion. It fails if someone raises SWEEP_MS to shave the last of the egress — which the
// dashboard entry's own "Not attempted here" section invites — or shortens the lease to detect
// heartbeat loss sooner, which needs no new plumbing since leaseSeconds is already a RunnerOpts
// field.
describe('the sweep interval stays inside the lease it guards', () => {
  test('SWEEP_MS is at most half the default lease — the invariant every bound here rests on', () => {
    expect(SWEEP_MS).toBeLessThanOrEqual((DEFAULT_LEASE_SECONDS * 1000) / 2);
  });

  test('runOnce actually uses DEFAULT_LEASE_SECONDS, so the constant above is the real one', async () => {
    const q = idleQueue();
    await runOnce(q, echoHandler, { workerId: 'w1' });
    expect(q.claim).toHaveBeenCalledWith('w1', DEFAULT_LEASE_SECONDS, null);
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
  // before awaiting it, or a `try { … } finally { onSwept() }` that acknowledges anyway. A sweep
  // that threw reclaimed nothing, so it must not spend the window — the next poll has to retry.
  //
  // ⚠ `finally` is the tempting wrong fix and this case is what kills it.
  test('does NOT acknowledge a sweep that threw', async () => {
    const q = throwingSweepQueue();
    const p = policy(true);

    const err = jest.spyOn(console, 'error').mockImplementation(() => {});
    await runOnce(q, echoHandler, { workerId: 'w1', sweepPolicy: p });
    err.mockRestore();
    expect(p.onSwept).not.toHaveBeenCalled();
  });

  // r1 High (Claude half 2, MEASURED: 40 sweep attempts / 0 claims at HEAD vs 1 / 20 before the
  // fold). Break this catches: letting sweepExpired's rejection escape runOnce, which skips
  // `queue.claim` entirely. `sweep_expired_leases` can break ALONE — a migration replacing its
  // signature, a stale PostgREST schema cache, a revoked execute grant — while claim_next_job is
  // perfectly healthy. The worker would then claim NOTHING, indefinitely, and the only symptom is
  // a log line whose own comment says the loop is fine.
  //
  // ⭐ This is the finding the branch is named for: decoupling the CADENCE while leaving the
  // FAILURE DOMAIN shared is not decoupling.
  test('still claims when the sweep throws — a broken sweep must not gate job intake', async () => {
    const q = throwingSweepQueue();

    const err = jest.spyOn(console, 'error').mockImplementation(() => {});
    const outcome = await runOnce(q, echoHandler, { workerId: 'w1', sweepPolicy: policy(true) });
    err.mockRestore();

    expect(q.sweepExpired).toHaveBeenCalledTimes(1);
    expect(q.claim).toHaveBeenCalledTimes(1); // reached DESPITE the sweep failing
    expect(outcome).toBe('idle');
  });

  // r1 Low (Claude half 2). runOnce's own contract comment at worker-runner.ts says the outcome
  // union must be uniform so the long-lived loop never sees an unhandled rejection. A sweep that
  // escaped made that comment false. Break this catches: re-introducing the escape.
  test('never rejects out of runOnce, even when the sweep fails — the declared contract', async () => {
    const err = jest.spyOn(console, 'error').mockImplementation(() => {});
    await expect(
      runOnce(throwingSweepQueue(), echoHandler, { workerId: 'w1', sweepPolicy: policy(true) }),
    ).resolves.toBe('idle');
    err.mockRestore();
  });

  // r2 Medium (Codex) — and this is the FOURTH consecutive finding introduced by the previous
  // round's fix, which is the pattern worth naming more than the bug.
  //
  // Before the r1 High fix, a sweep rejection escaped to runWorkerLoop's catch, `sleep()` returned
  // at once on the aborted signal, and the loop exited WITHOUT claiming. Swallowing the error
  // removed that accidental exit, so a SIGTERM landing mid-sweep now falls straight through to
  // queue.claim — leasing a fresh job during shutdown. claim_next_job increments `attempts` at
  // claim time (0008:104), and with summary_max_attempts = 1 that consumes the job's only attempt,
  // so an already-aborting worker can push a perfectly good job to dead_letter.
  test('does not claim a new job when shutdown arrived while the sweep was failing', async () => {
    const ac = new AbortController();
    const q = {
      sweepExpired: jest.fn(async () => { ac.abort(); throw new Error('transient PostgREST failure'); }),
      claim: jest.fn(async () => null),
    } as unknown as JobQueue & { sweepExpired: jest.Mock; claim: jest.Mock };

    const err = jest.spyOn(console, 'error').mockImplementation(() => {});
    const outcome = await runOnce(q, echoHandler, {
      workerId: 'w1', shutdownSignal: ac.signal, sweepPolicy: policy(true),
    });
    err.mockRestore();

    expect(q.claim).not.toHaveBeenCalled();
    expect(outcome).toBe('idle');
  });

  // ⭐ THE CLASS, not the instance. Codex's scenario needs a throwing sweep, but the race does not:
  // a SIGTERM landing during a perfectly successful sweep reaches the same claim. That half was
  // pre-existing rather than introduced here, and a guard written only for the throw path would
  // have left it — the repeated "instance-not-class" defect this repo keeps paying for.
  test('does not claim a new job when shutdown arrived during a SUCCESSFUL sweep either', async () => {
    const ac = new AbortController();
    const q = {
      sweepExpired: jest.fn(async () => { ac.abort(); return 0; }),
      claim: jest.fn(async () => null),
    } as unknown as JobQueue & { sweepExpired: jest.Mock; claim: jest.Mock };

    const outcome = await runOnce(q, echoHandler, {
      workerId: 'w1', shutdownSignal: ac.signal, sweepPolicy: policy(true),
    });

    expect(q.sweepExpired).toHaveBeenCalledTimes(1); // the sweep itself is still worth doing
    expect(q.claim).not.toHaveBeenCalled();
    expect(outcome).toBe('idle');
  });

  // Break this catches: a shutdown guard so eager it stops the worker doing its ordinary job.
  test('still claims normally when no shutdown signal is supplied at all', async () => {
    const q = idleQueue();
    await runOnce(q, echoHandler, { workerId: 'w1', sweepPolicy: policy(true) });
    expect(q.claim).toHaveBeenCalledTimes(1);
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
  // r1 Medium (Codex) AND r1 High (Claude half 2) meet here, and the pair of assertions at the
  // bottom is what keeps them from cancelling each other out:
  //   - sweepAttempts climbing  => a failed sweep did NOT spend the 60s window (Codex's Medium)
  //   - claims === sweepAttempts => a failed sweep did NOT block job intake (the High)
  // Satisfying either alone is easy; the earlier versions of this branch each did exactly that,
  // in opposite directions.
  //
  // ⟳ Bounded by a COUNTER, not a 50ms wall-clock timeout (r1 Low, Claude half 2): every other
  // cadence assertion in this file runs on an injected clock, which is the stated reason these
  // tests can live in tests/lib/ at all. Counting makes it deterministic and pins a number.
  test('keeps sweeping AND keeps claiming when every sweep throws', async () => {
    const ac = new AbortController();
    let sweepAttempts = 0;
    let claims = 0;
    const queue = {
      // ⟳ The abort fires from the CLAIM, not the sweep. Aborting mid-sweep would trip the r2
      // shutdown guard and legitimately skip that iteration's claim, so the counters would differ
      // by one for a reason that has nothing to do with what this test is about.
      // ⚠ BACKSTOP (r2 Low): the primary stop condition lives in `claim`, which sits BEHIND the
      // shutdown guard. A guard that wrongly fires would mean claim is never reached, `ac` never
      // aborts, and runWorkerLoop spins forever — measured: jest HANGS past 150s rather than
      // failing, and CI runs `jest` with no --forceExit, so that stalls the job instead of
      // reddening it. This abort runs BEFORE the guard on every iteration, so the test always
      // terminates no matter what the guard does.
      sweepExpired: async () => {
        sweepAttempts++;
        if (sweepAttempts >= 50) ac.abort();
        throw new Error('transient PostgREST failure');
      },
      claim: async () => { claims++; if (claims >= 5) ac.abort(); return null; },
    } as unknown as JobQueue;
    const handler: JobHandler = async () => ({ ok: true });

    const err = jest.spyOn(console, 'error').mockImplementation(() => {});
    await runWorkerLoop({ queue, handler, shutdownSignal: ac.signal, workerId: 'sweep-retry', pollMs: 1 });
    err.mockRestore();

    expect(sweepAttempts).toBe(5);     // NOT stuck at 1 for a whole 60s window
    expect(claims).toBe(sweepAttempts); // every poll still reached the claim
  });

  // r1 Low (Claude half 2). Break this catches: `const pollMs = deps.pollMs;` losing its default.
  // The natural form is caught by tsc (sleep(ms: number) rejects number|undefined), but an
  // explicit cast survives — and the failure mode is severe in the ironic direction:
  // setTimeout(fn, undefined) fires at ~1ms, turning the worker into a ~1000 req/s busy-spin
  // against the database. A 2000x INCREASE in exactly the traffic this branch exists to remove.
  //
  // Deliberately spends ~2s of suite time: the only honest way to observe a real poll interval
  // is to let one elapse.
  test('defaults to the real POLL_MS when none is injected, rather than busy-spinning', async () => {
    const ac = new AbortController();
    let claims = 0;
    const queue = {
      sweepExpired: async () => 0,
      claim: async () => { claims++; if (claims >= 2) ac.abort(); return null; },
    } as unknown as JobQueue;

    const started = Date.now();
    await runWorkerLoop({
      queue,
      handler: (async () => ({ ok: true })) as JobHandler,
      shutdownSignal: ac.signal,
      workerId: 'poll-default',
    }); // NO pollMs — production's path
    const elapsed = Date.now() - started;

    expect(claims).toBe(2);
    expect(elapsed).toBeGreaterThan(1_500); // one real ~2s backoff happened between the two polls
  }, 15_000);
});
