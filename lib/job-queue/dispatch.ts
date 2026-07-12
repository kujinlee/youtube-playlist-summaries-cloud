import type { JobHandler } from '@/lib/job-queue/handler-context';
import type { JobKind } from '@/lib/storage/job-queue';
import { NonRetryableError } from '@/lib/job-queue/errors';

/** Pure kind→handler dispatch. A single JobHandler the worker loop can register, that fans
 *  a leased job to the right handler by kind. Unknown kinds are non-retryable (bad data, not
 *  a transient failure) so the runner dead-letters instead of looping. */
export function makeJobHandler(handlers: Record<JobKind, JobHandler>): JobHandler {
  return async (job, ctx) => {
    const h = handlers[job.kind];
    if (!h) throw new NonRetryableError(`no handler for kind ${job.kind}`);
    return h(job, ctx);
  };
}
