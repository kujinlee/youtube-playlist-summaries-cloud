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
  /** Is ANY job unfinished — `queued` (including one whose retry backoff has not elapsed) or
   *  `active` (including one abandoned by a worker that died)?
   *
   *  ⚠ Deliberately NOT the same question as `claim()` returning null, in TWO ways, and each was a
   *  separate review finding (backlog #142):
   *
   *  - a job that is `queued` with `run_after` in the future is real pending work that `claim`
   *    cannot see, so treating "claim returned null" as "nothing to do" strands it;
   *  - a job left `active` by a crashed worker is not claimable until its lease expires and
   *    `sweep_expired_leases` requeues it. A worker blind to those rows can finish other work and
   *    exit while one sits there — and nothing sweeps while the machine is stopped, so it is
   *    re-stranded by the very worker that was woken to deal with it (review r1 F8).
   *
   *  Terminal statuses (`completed`, `failed`, `dead_letter`, `cancelled`) are NOT counted: they are
   *  finished, and a dead-lettered job must not pin a machine up forever.
   *
   *  Asked only when the worker is deciding whether to shut itself down — once per idle window, and
   *  that claim is now true rather than aspirational: the caller resets its idle clock whenever this
   *  returns true, so it is not re-asked on every poll (review r1 F6). */
  hasUnfinishedWork(): Promise<boolean>;
  setProgressPhase(jobId: string, workerId: string, leaseToken: string, phase: ProgressPhase): Promise<{ ok: boolean }>;
}

export function docVersionKey(v: DocVersion): string { return `${v.major}.${v.minor}`; }
