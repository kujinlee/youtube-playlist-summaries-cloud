import type { LeasedJob } from '@/lib/storage/job-queue';
import type { ProgressPhase } from '@/lib/job-queue/progress-phase';

export interface HandlerCtx {
  isCancelled(): Promise<boolean>;
  signal: AbortSignal;
  setPhase(p: ProgressPhase): Promise<void>;
}

export type JobHandler = (job: LeasedJob, ctx: HandlerCtx) => Promise<unknown>;
