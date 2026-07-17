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
  progressPhase: ProgressPhase | null; attempts: number; updatedAt: string;
}
export interface PlaylistJobRow {
  jobId: string; videoId: string; status: JobStatus;
  progressPhase: ProgressPhase | null; attempts: number; error: string | null;
}

export interface JobQueue {
  getStatus(jobId: string): Promise<JobRecord | null>;
  listByPlaylist(playlistId: string): Promise<PlaylistJobRow[]>;
  requestCancel(jobId: string): Promise<{ requested: number }>;
  /** Cancel every non-terminal (queued/active) job for a playlist (Task 8) by calling the
   *  SECURITY DEFINER `request_cancel_playlist_jobs` RPC (0019), which self-guards on
   *  `owner_id = auth.uid()` — a non-owner playlistId cancels 0 rows. Added to the
   *  interface (not just the class) because T9's DELETE route consumes it through
   *  `bundle.jobQueue` typed as `JobQueue`; `SupabaseJobQueue` is the sole implementer. */
  requestCancelPlaylist(playlistId: string): Promise<{ cancelled: number }>;
  claim(workerId: string, leaseSeconds: number, videoId?: string | null): Promise<LeasedJob | null>;
  heartbeat(jobId: string, workerId: string, leaseToken: string, leaseSeconds: number): Promise<{ ok: boolean }>;
  complete(jobId: string, workerId: string, leaseToken: string, result: unknown): Promise<{ ok: boolean }>;
  fail(jobId: string, workerId: string, leaseToken: string, error: string, opts: { retryable: boolean; billableSucceeded?: boolean; metered?: boolean }):
    Promise<{ ok: boolean; status: JobStatus | null }>;
  sweepExpired(): Promise<number>;
  setProgressPhase(jobId: string, workerId: string, leaseToken: string, phase: ProgressPhase): Promise<{ ok: boolean }>;
}

export function docVersionKey(v: DocVersion): string { return `${v.major}.${v.minor}`; }
