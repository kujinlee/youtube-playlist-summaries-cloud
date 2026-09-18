import type { JobQueue } from '@/lib/storage/job-queue';
import type { HandlerCtx, JobHandler } from './handler-context';
import type { BillingLatch } from '@/lib/job-queue/billing-latch';
import { classifyGeminiFailure, releaseGateOpen, isNonRetryable } from '@/lib/gemini-failure';

export type { JobHandler } from './handler-context';

/** Cadence control for the pre-claim lease sweep — ONE method, so a caller cannot get it wrong.
 *
 *  ⚠ THE HONEST CLAIM, after r1 said the first two versions of this comment were both overstated.
 *  Codex refuted "unwritable"; the Claude half then measured that scoping it to "unwritable by
 *  callers" was close to vacuous, because the mistake was reproducible in three lines inside
 *  `makeSweepGate` — the only policy this repo ships — and because the branch had briefly made
 *  things WORSE: master wrote each rule once, in `runOnce`, while an interface of two dumb methods
 *  meant no implementation could hold a rule wrongly. An interface of one smart method obliged every
 *  future implementer to re-derive two non-obvious rules, and three copies of one of them already
 *  existed.
 *
 *  What is true now: the rules are written EXACTLY ONCE, in `sweepPolicyFrom` below, and no
 *  implementation holds either. That restores master's single-copy property while giving callers a
 *  one-method interface and taking cadence logic out of `runOnce` entirely. The `finally` mistake is
 *  writable in exactly one function — the minimum, not zero. */
export interface SweepPolicy {
  /** Runs `sweep` if one is due, commits the cadence window ONLY if it resolves, and NEVER rejects.
   *
   *  ⚠ "Never rejects" is load-bearing: the caller reaches `queue.claim` immediately afterwards, and
   *  a rejection escaping here would starve job intake — measured at 40 sweeps / 0 claims before
   *  PR #318 fixed it. `runOnce` keeps a defence-in-depth catch anyway, because this is a declared
   *  contract rather than an enforced one and the consequence of breaking it is silent.
   *
   *  ⚠ Do NOT justify this by runOnce's "never sees an unhandled rejection" comment below — r1
   *  Medium 2 measured that claim as false (`queue.claim` sits outside every `try`, which is why
   *  `runWorkerLoop` needs its own catch). Pre-existing and not this change's to fix, but it is not
   *  a premise to lean on. */
  run(sweep: () => Promise<unknown>): Promise<void>;
}

/** A bare cadence cursor. Deliberately DUMB: it answers "is one due?" and records "one landed", and
 *  it holds NEITHER the commit-on-resolve rule NOR the never-reject rule. That is the whole point —
 *  an implementer supplies clock arithmetic and cannot get the protocol wrong, because it does not
 *  have the protocol. */
export interface SweepCursor {
  /** True when a sweep is due. Must not record anything — the window is spent by a sweep that
   *  LANDED, not by one that was contemplated. */
  due(): boolean;
  /** Record that a sweep resolved. `sweepPolicyFrom` calls this only on the resolve path. */
  commit(): void;
}

/** ⭐ THE ONLY PLACE THE TWO RULES ARE WRITTEN (backlog #140, r1 High 1).
 *
 *  `commit()` is inside the `try` and after the `await`, so a sweep that THREW does not spend the
 *  window and the next poll retries it (PR #318 r1 Medium). The `catch` does not rethrow, so a
 *  broken sweep cannot starve `queue.claim` (PR #318 r1 High — measured 40 sweeps / 0 claims).
 *
 *  ⚠ A `finally` here — or dropping the `return` from the sweep's catch — would silently undo the
 *  first rule. This is the one function where that edit is possible, and it fails THREE tests
 *  (measured 2026-09-18; control green): `a sweep that THROWS does not spend the window`,
 *  `does NOT acknowledge a sweep that threw`, and `keeps sweeping AND keeps claiming when every
 *  sweep throws`. Every other route was deleted by moving the rules here rather than into each
 *  implementation.
 *
 *  Verified by grep: `makeSweepGate`, `ALWAYS_SWEEP` and the test double are all built from this
 *  combinator and hold neither rule. ⚠ ONE hand-rolled `run` remains, at
 *  `tests/lib/lease-sweep-cadence.test.ts`'s `rejecting` double — it exists precisely TO break the
 *  never-rejects contract, so that `runOnce`'s defence-in-depth catch has something to defend
 *  against. A deliberate violator is not a second copy of the rule. */
export function sweepPolicyFrom(cursor: SweepCursor): SweepPolicy {
  return {
    async run(sweep) {
      // ⚠ THREE STAGES, THREE DIAGNOSTICS (r2 Low 1). The first version wrapped only the sweep, so
      // a throwing `due()` REJECTED out of `run` — breaking the never-rejects clause this interface
      // advertises — and a throwing `commit()` was reported as `sweepExpired failed`, which is a
      // FALSE diagnostic and precisely the class r1 High 2 was filed about: the one log line that
      // distinguishes "the database call is broken" from "the cadence is broken" naming the wrong
      // one, on the failure this whole branch exists for.
      // ⚠ FAIL SAFE, AND THE DIRECTION IS THE WHOLE POINT (r2 Medium 1). The first version
      // `return`ed here, treating a broken cadence check as "not due" — measured at ZERO sweeps
      // across 100 polls, each with a log line reading "continuing to claim", which reads like
      // reassurance. That is the catastrophe worker/main.ts names in its own docblock ("the sweep
      // would never run again for the life of the process — lease reclamation silently dead"),
      // reached by a different route. This file already states the rule fifteen lines below, on
      // ALWAYS_SWEEP: *sweeping too often is cheap; never sweeping strands crashed jobs.*
      //
      // So a broken cursor degrades to sweeping on EVERY poll — costly, loud in the logs, and
      // correct — rather than silently never sweeping again.
      let due = true;
      try {
        due = cursor.due();
      } catch (e) {
        console.error('[worker] sweep cadence check failed (sweeping anyway):', e);
      }
      if (!due) return;

      try {
        await sweep();
      } catch (e) {
        console.error('[worker] sweepExpired failed (continuing to claim):', e);
        return; // ⚠ the window is NOT committed — the next poll retries (PR #318 r1 Medium)
      }

      try {
        cursor.commit();
      } catch (e) {
        // Fail-safe FOR RECLAMATION: the next poll sweeps again. ⚠ Not fail-safe for COST, and
        // r2 Low 4 measured the difference — a persistently throwing commit never advances the
        // window, so the gate degrades to per-poll sweeping: the ~40,000 requests/day of egress
        // this whole branch exists to remove, restored silently behind a log line.
        console.error('[worker] sweep cadence commit failed (continuing to claim):', e);
      }
    },
  };
}

/** The fail-safe default when no cadence is supplied: always sweep, never record a window.
 *
 *  Sweeping too often is cheap; never sweeping strands crashed jobs. ⟳ This used to claim callers
 *  DEPEND on it; PR #318 r2 enumerated every call site by grep and found none do. Keep the default,
 *  not the reason. ⟳⟳ It used to carry its OWN try/catch, a second copy of the never-reject rule
 *  that r1 High 2 measured as guarded by nothing — deleting it left the suite 25/25 green. Built
 *  from the shared combinator now, so there is no second copy to leave untested. */
export const ALWAYS_SWEEP: SweepPolicy = sweepPolicyFrom({ due: () => true, commit: () => {} });

export interface RunnerOpts {
  workerId: string;
  leaseSeconds?: number;
  videoFilter?: string | null;
  shutdownSignal?: AbortSignal;
  wallClockMs?: number;
  /** Cadence for the pre-claim lease sweep. Defaults to always-sweep as a FAIL-SAFE — sweeping
   *  too often is cheap, never sweeping strands crashed jobs — not because anything depends on it.
   *
   *  ⟳ r2 Medium: this comment used to claim "every other caller depends on runOnce reclaiming
   *  expired leases for it", and that was MEASURABLY FALSE. Every call site was enumerated by grep
   *  and opened: the integration suites either enqueue a fresh `queued` job or use a fully mocked
   *  queue whose `sweepExpired` stub is never asserted; the only genuine reclamation in the repo
   *  calls `sweep_expired_leases` DIRECTLY (reservation-release.test.ts). No caller relies on this.
   *
   *  ⚠ Why the correction matters more than the sentence: the false version is exactly what a
   *  future reader would cite to decline moving the sweep out of runOnce. Keep the default; do not
   *  keep the reason. */
  sweepPolicy?: SweepPolicy;
}

/** The lease a claim takes when the caller does not specify one. Exported and named because the
 *  sweep cadence in worker/main.ts must stay well inside it, and that relationship was previously
 *  a fact about two bare literals in two modules that only prose connected — mutation-proven, by
 *  BOTH r1 Claude halves, to survive being raised to thirty minutes with every gate green. */
export const DEFAULT_LEASE_SECONDS = 120;

export const echoHandler: JobHandler = async (job) => ({ echoed: job.payload });

// Long-running-safe job runner: heartbeats the lease while the handler runs, composes a
// single AbortSignal from wall-clock/lease-loss/shutdown sources, and guarantees exactly
// one terminal write (complete or fail) with clean timer teardown on every exit path.
export async function runOnce(
  queue: JobQueue, handler: JobHandler, opts: RunnerOpts,
): Promise<'idle' | 'done' | 'failed' | 'cancelled' | 'lost'> {
  // The sweep reclaims leases that expired; it is NOT part of claiming, and the two ran at the
  // same rate only because they were written on the same line. See makeSweepGate in worker/main.ts.
  //
  // ⭐ THE SWEEP IS ISOLATED IN BOTH DIRECTIONS, and getting only one of them is what r1 cost:
  //
  //  1. The policy commits its cadence window ONLY after `sweep()` resolves, so a sweep that threw
  //     does not spend the 60s window and the next poll retries it (PR #318 r1 Medium, Codex).
  //     ⚠ That rule now lives inside `sweepPolicyFrom`, not here and not in `makeSweepGate` —
  //     see backlog #140.
  //  2. The catch does NOT rethrow, so a broken sweep cannot stop the CLAIM below (r1 High).
  //     sweep_expired_leases and claim_next_job are separate functions with separate grants and
  //     separate signatures, so one can break alone — a migration replacing it, a stale PostgREST
  //     schema cache, a revoked execute. MEASURED at the previous commit: 40 sweep attempts and
  //     ZERO claims, indefinitely, with the only symptom a log line saying the loop was fine.
  //
  // Lease reclamation degrades while the sweep is broken; job intake does not. That is the whole
  // point of decoupling them — cadence alone was never enough, the FAILURE DOMAIN had to split too.
  try {
    await (opts.sweepPolicy ?? ALWAYS_SWEEP).run(() => queue.sweepExpired());
  } catch (e) {
    // DEFENCE IN DEPTH. SweepPolicy.run declares it never rejects and the shipped policies honour
    // that — but a declared contract is not an enforced one, and the consequence of breaking it is
    // the r1 High: total, silent claim starvation with a log line saying the loop is fine.
    console.error('[worker] sweep policy rejected (continuing to claim):', e);
  }
  // ⚠ SHUTDOWN CAN ARRIVE DURING THE SWEEP, and claiming after it is how a good job dies (r2
  // Medium, Codex). claim_next_job increments `attempts` at claim time (0008:104); with
  // summary_max_attempts = 1 that consumes the job's ONLY attempt, so a worker that is already
  // draining can lease a fresh job and push it straight to dead_letter.
  //
  // Before the r1 High fix a throwing sweep escaped to runWorkerLoop's catch, `sleep()` returned
  // immediately on the aborted signal, and the loop exited without claiming — the exit was
  // ACCIDENTAL, and swallowing the error removed it. This guard makes it deliberate, and covers
  // the SUCCESSFUL-sweep race too, which was never protected by that accident.
  if (opts.shutdownSignal?.aborted) return 'idle';

  const job = await queue.claim(opts.workerId, opts.leaseSeconds ?? DEFAULT_LEASE_SECONDS, opts.videoFilter ?? null);
  if (!job) return 'idle';

  const leaseSeconds = opts.leaseSeconds ?? DEFAULT_LEASE_SECONDS;
  const wallClock = new AbortController();
  const leaseLost = new AbortController();
  const signal = AbortSignal.any(
    [wallClock.signal, leaseLost.signal, opts.shutdownSignal].filter((s): s is AbortSignal => Boolean(s)),
  );

  const billing: BillingLatch = { metered: false };
  const ctx: HandlerCtx = {
    isCancelled: async () => (await queue.getStatus(job.id))?.cancelRequested ?? false,
    signal,
    // Phase writes are ADVISORY (progress hints only) — swallow a transient failure so it can
    // never fail an otherwise-succeeding job. Second .then handler consumes any rejection.
    setPhase: (p) => queue.setProgressPhase(job.id, opts.workerId, job.leaseToken, p).then(() => {}, () => {}),
    billing,
  };

  const wct = setTimeout(() => wallClock.abort(), opts.wallClockMs ?? 600_000);
  wct.unref?.();

  const hb = setInterval(() => {
    queue.heartbeat(job.id, opts.workerId, job.leaseToken, leaseSeconds)
      .then(r => { if (!r.ok) leaseLost.abort(); })
      .catch(() => leaseLost.abort()); // a throwing heartbeat ⇒ treat as lease-loss, never an unhandled rejection
  }, Math.floor((leaseSeconds * 1000) / 3));

  let settled = false;
  try {
    const result = await handler(job, ctx);
    if (settled) return 'lost';
    settled = true;
    const { ok } = await queue.complete(job.id, opts.workerId, job.leaseToken, result);
    return ok ? 'done' : 'lost';
  } catch (e) {
    if (settled) return 'lost';
    settled = true;
    try {
      // RELEASE only on a positively-not-metered class-A failure, gated by the live-verification flag.
      const release = releaseGateOpen()
        && classifyGeminiFailure(e, signal) === 'release'
        && !billing.metered;
      const { ok, status } = await queue.fail(
        job.id, opts.workerId, job.leaseToken, e instanceof Error ? e.message : String(e),
        // isNonRetryable walks the cause chain — a WRAPPED NonRetryableError is still non-retryable,
        // so a pre-send class-A failure sets BOTH retryable=false and billableSucceeded=false (H1);
        // otherwise it would requeue and fail_job would refuse to release a queued transition.
        // metered is reported on EVERY fail — terminal AND requeue — so a metered attempt-1 that
        // requeues persists jobs.ever_metered durably before attempt-2 ever runs (Task 13/H1).
        { retryable: !isNonRetryable(e), billableSucceeded: !release, metered: billing.metered });
      if (!ok) return 'lost';
      return status === 'cancelled' ? 'cancelled' : 'failed';
    } catch {
      // The terminal fail RPC itself threw (e.g. transient DB error). Resolve to 'lost' rather than
      // rejecting out of runOnce — the declared outcome contract must be uniform so the long-lived
      // worker loop (Task 8) never sees an unhandled rejection from runOnce.
      return 'lost';
    }
  } finally {
    clearInterval(hb);
    clearTimeout(wct);
  }
}
