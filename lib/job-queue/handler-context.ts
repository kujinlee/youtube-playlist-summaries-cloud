import type { LeasedJob } from '@/lib/storage/job-queue';
import type { ProgressPhase } from '@/lib/job-queue/progress-phase';
import type { BillingLatch } from '@/lib/job-queue/billing-latch';

export interface HandlerCtx {
  isCancelled(): Promise<boolean>;
  signal: AbortSignal;
  setPhase(p: ProgressPhase): Promise<void>;
  billing: BillingLatch;   // job-scoped metering latch (design spec §3.1)
}

export type JobHandler = (job: LeasedJob, ctx: HandlerCtx) => Promise<unknown>;
