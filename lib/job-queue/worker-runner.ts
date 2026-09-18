import type { JobQueue } from '@/lib/storage/job-queue';
import type { HandlerCtx, JobHandler } from './handler-context';
import type { BillingLatch } from '@/lib/job-queue/billing-latch';
import { classifyGeminiFailure, releaseGateOpen, isNonRetryable } from '@/lib/gemini-failure';

export type { JobHandler } from './handler-context';

/** Cadence control for the pre-claim lease sweep.
 *
 *  Deliberately ONE object rather than two independent callbacks: `due` and `onSwept` are halves
 *  of a single protocol, and a caller who supplied only the first would have a cursor that never
 *  advances — permanently due, silently sweeping on every poll again, with every default-path
 *  test still green. Holding it wrong should not be expressible. */
export interface SweepPolicy {
  /** True when a sweep is due. MUST NOT record the attempt — the window is spent by a sweep that
   *  landed, not by one that was contemplated. */
  due(): boolean;
  /** Called only after `sweepExpired()` RESOLVES. A sweep that threw reclaimed nothing, so it
   *  must leave the window open for the next poll to retry. */
  onSwept(): void;
}

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
  //  1. onSwept() is INSIDE the try and AFTER the await, so a sweep that threw does not spend the
  //     60s window and the next poll retries it (r1 Medium, Codex). ⚠ `finally` is the tempting
  //     wrong shape here — it acknowledges on the throw path and silently undoes this.
  //  2. The catch does NOT rethrow, so a broken sweep cannot stop the CLAIM below (r1 High).
  //     sweep_expired_leases and claim_next_job are separate functions with separate grants and
  //     separate signatures, so one can break alone — a migration replacing it, a stale PostgREST
  //     schema cache, a revoked execute. MEASURED at the previous commit: 40 sweep attempts and
  //     ZERO claims, indefinitely, with the only symptom a log line saying the loop was fine.
  //
  // Lease reclamation degrades while the sweep is broken; job intake does not. That is the whole
  // point of decoupling them — cadence alone was never enough, the FAILURE DOMAIN had to split too.
  if (opts.sweepPolicy?.due() ?? true) {
    try {
      await queue.sweepExpired();
      opts.sweepPolicy?.onSwept();
    } catch (e) {
      console.error('[worker] sweepExpired failed (continuing to claim):', e);
    }
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
