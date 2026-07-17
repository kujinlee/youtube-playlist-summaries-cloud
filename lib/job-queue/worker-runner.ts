import type { JobQueue } from '@/lib/storage/job-queue';
import type { HandlerCtx, JobHandler } from './handler-context';
import type { BillingLatch } from '@/lib/job-queue/billing-latch';
import { classifyGeminiFailure, releaseGateOpen, isNonRetryable } from '@/lib/gemini-failure';

export type { JobHandler } from './handler-context';

export interface RunnerOpts {
  workerId: string;
  leaseSeconds?: number;
  videoFilter?: string | null;
  shutdownSignal?: AbortSignal;
  wallClockMs?: number;
}

export const echoHandler: JobHandler = async (job) => ({ echoed: job.payload });

// Long-running-safe job runner: heartbeats the lease while the handler runs, composes a
// single AbortSignal from wall-clock/lease-loss/shutdown sources, and guarantees exactly
// one terminal write (complete or fail) with clean timer teardown on every exit path.
export async function runOnce(
  queue: JobQueue, handler: JobHandler, opts: RunnerOpts,
): Promise<'idle' | 'done' | 'failed' | 'cancelled' | 'lost'> {
  await queue.sweepExpired();
  const job = await queue.claim(opts.workerId, opts.leaseSeconds ?? 120, opts.videoFilter ?? null);
  if (!job) return 'idle';

  const leaseSeconds = opts.leaseSeconds ?? 120;
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
