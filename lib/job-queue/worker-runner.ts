import type { JobQueue, LeasedJob } from '@/lib/storage/job-queue';

export type JobHandler = (job: LeasedJob, ctx: { isCancelled(): Promise<boolean> }) => Promise<unknown>;
export interface RunnerOpts { workerId: string; leaseSeconds?: number; videoFilter?: string | null }

export const echoHandler: JobHandler = async (job) => ({ echoed: job.payload });

// NOTE: no heartbeat loop — the 1E-a stub completes instantly, well within the lease.
// A periodic heartbeat around the handler is REQUIRED before 1E-b swaps in the real
// (long-running) ingestion handler; that's a 1E-b task, not this one.
export async function runOnce(
  queue: JobQueue, handler: JobHandler, opts: RunnerOpts,
): Promise<'idle' | 'done' | 'failed' | 'cancelled' | 'lost'> {
  await queue.sweepExpired();
  const job = await queue.claim(opts.workerId, opts.leaseSeconds ?? 120, opts.videoFilter ?? null);
  if (!job) return 'idle';

  const ctx = { isCancelled: async () => (await queue.getStatus(job.id))?.cancelRequested ?? false };
  try {
    const result = await handler(job, ctx);
    const { ok } = await queue.complete(job.id, opts.workerId, job.leaseToken, result);
    return ok ? 'done' : 'lost';
  } catch (e) {
    const { ok, status } = await queue.fail(
      job.id, opts.workerId, job.leaseToken, e instanceof Error ? e.message : String(e), { retryable: true });
    if (!ok) return 'lost';
    return status === 'cancelled' ? 'cancelled' : 'failed';
  }
}
