import type { DocVersion } from '@/lib/doc-version';
import type { ProgressPhase } from '@/lib/job-queue/progress-phase';

export type JobKind = 'summary' | 'dig';
export type JobStatus = 'queued' | 'active' | 'completed' | 'failed' | 'dead_letter' | 'cancelled';

export interface JobKey { playlistId: string; videoId: string; sectionId: number; kind: JobKind; version: string; }
export interface EnqueueResult { jobId: string; status: JobStatus; joined: boolean; }
export interface LeasedJob {
  id: string; ownerId: string; playlistId: string; videoId: string; sectionId: number;
  kind: JobKind; version: string; payload: unknown; attempts: number; leaseToken: string;
}
export interface JobRecord {
  id: string; status: JobStatus; cancelRequested: boolean; result: unknown; error: string | null;
}

export interface JobQueue {
  enqueue(key: JobKey, payload: unknown): Promise<EnqueueResult>;
  getStatus(jobId: string): Promise<JobRecord | null>;
  requestCancel(jobId: string): Promise<{ requested: number }>;
  claim(workerId: string, leaseSeconds: number, videoId?: string | null): Promise<LeasedJob | null>;
  heartbeat(jobId: string, workerId: string, leaseToken: string, leaseSeconds: number): Promise<{ ok: boolean }>;
  complete(jobId: string, workerId: string, leaseToken: string, result: unknown): Promise<{ ok: boolean }>;
  fail(jobId: string, workerId: string, leaseToken: string, error: string, opts: { retryable: boolean }):
    Promise<{ ok: boolean; status: JobStatus | null }>;
  sweepExpired(): Promise<number>;
  setProgressPhase(jobId: string, workerId: string, leaseToken: string, phase: ProgressPhase): Promise<{ ok: boolean }>;
}

export function docVersionKey(v: DocVersion): string { return `${v.major}.${v.minor}`; }
