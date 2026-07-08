import type { SupabaseClient } from '@supabase/supabase-js';
import type { JobQueue, JobKey, EnqueueResult, LeasedJob, JobRecord, JobStatus, PlaylistJobRow } from '@/lib/storage/job-queue';
import type { ProgressPhase } from '@/lib/job-queue/progress-phase';

export class SupabaseJobQueue implements JobQueue {
  constructor(private client: SupabaseClient) {}

  async enqueue(key: JobKey, payload: unknown): Promise<EnqueueResult> {
    const { data, error } = await this.client.rpc('enqueue_job', {
      p_playlist_id: key.playlistId, p_video_id: key.videoId, p_section_id: key.sectionId, p_job_kind: key.kind,
      p_job_version: key.version, p_payload: payload });
    if (error) throw error;
    const row = data[0];
    return { jobId: row.job_id, status: row.status, joined: row.joined };
  }

  async getStatus(jobId: string): Promise<JobRecord | null> {
    const { data, error } = await this.client
      .from('jobs').select('id,status,cancel_requested,result,error,progress_phase,attempts,updated_at')
      .eq('id', jobId).maybeSingle();
    if (error) throw error;
    if (!data) return null;
    return { id: data.id, status: data.status, cancelRequested: data.cancel_requested,
      result: data.result, error: data.error, progressPhase: data.progress_phase,
      attempts: data.attempts, updatedAt: data.updated_at };
  }

  /**
   * RLS-dependent: owner confinement (`owner_id = auth.uid()`) comes entirely from Postgres RLS
   * on the caller's session client — this method MUST NOT be called on a service_role-constructed
   * SupabaseJobQueue (service_role bypasses RLS and would leak cross-owner rows).
   */
  async listByPlaylist(playlistId: string): Promise<PlaylistJobRow[]> {
    const { data, error } = await this.client
      .from('jobs')
      .select('id,video_id,status,progress_phase,attempts,error,created_at')
      .eq('playlist_id', playlistId).eq('job_kind', 'summary')
      .order('created_at', { ascending: true }).order('video_id', { ascending: true });
    if (error) throw error;
    // The idempotency index (`jobs_idem_active`) excludes failed/cancelled/dead_letter, so
    // re-submitting a partially-failed playlist creates a SECOND row for the same videoId (a
    // stale terminal row plus a fresh queued one). Dedupe to the latest row per videoId: iterate
    // in ascending created_at order and let a later row overwrite an earlier one in the Map, so
    // callers (rollup, the polling client) never see a phantom duplicate or a stale `failed`.
    const latestByVideo = new Map<string, PlaylistJobRow>();
    for (const r of data ?? []) {
      latestByVideo.set(r.video_id, { jobId: r.id, videoId: r.video_id, status: r.status,
        progressPhase: r.progress_phase, attempts: r.attempts, error: r.error });
    }
    return Array.from(latestByVideo.values());
  }

  async requestCancel(jobId: string): Promise<{ requested: number }> {
    const { data, error } = await this.client.rpc('request_cancel_job', { p_job_id: jobId });
    if (error) throw error;
    return { requested: (data as number) ?? 0 };
  }

  async claim(workerId: string, leaseSeconds: number, videoId: string | null = null): Promise<LeasedJob | null> {
    const { data, error } = await this.client.rpc('claim_next_job', {
      p_worker_id: workerId, p_lease_seconds: leaseSeconds, p_video_id: videoId });
    if (error) throw error;
    if (!data || data.length === 0) return null;
    const r = data[0];
    return {
      id: r.id, ownerId: r.owner_id, playlistId: r.playlist_id, videoId: r.video_id, sectionId: r.section_id,
      kind: r.job_kind, version: r.job_version, payload: r.payload, attempts: r.attempts, leaseToken: r.lease_token };
  }

  async heartbeat(jobId: string, workerId: string, leaseToken: string, leaseSeconds: number): Promise<{ ok: boolean }> {
    const { data, error } = await this.client.rpc('heartbeat_job', {
      p_job_id: jobId, p_worker_id: workerId, p_lease_token: leaseToken, p_lease_seconds: leaseSeconds });
    if (error) throw error;
    return { ok: data === true };
  }

  async complete(jobId: string, workerId: string, leaseToken: string, result: unknown): Promise<{ ok: boolean }> {
    const { data, error } = await this.client.rpc('complete_job', {
      p_job_id: jobId, p_worker_id: workerId, p_lease_token: leaseToken, p_result: result });
    if (error) throw error;
    return { ok: data === true };
  }

  async fail(
    jobId: string, workerId: string, leaseToken: string, err: string, opts: { retryable: boolean },
  ): Promise<{ ok: boolean; status: JobStatus | null }> {
    const { data, error } = await this.client.rpc('fail_job', {
      p_job_id: jobId, p_worker_id: workerId, p_lease_token: leaseToken, p_error: err, p_retryable: opts.retryable });
    if (error) throw error;
    return { ok: data !== null, status: data };
  }

  async sweepExpired(): Promise<number> {
    const { data, error } = await this.client.rpc('sweep_expired_leases');
    if (error) throw error;
    return data as number;
  }

  async setProgressPhase(
    jobId: string, workerId: string, leaseToken: string, phase: ProgressPhase,
  ): Promise<{ ok: boolean }> {
    const { data, error } = await this.client.rpc('set_progress_phase', {
      p_job_id: jobId, p_worker_id: workerId, p_lease_token: leaseToken, p_phase: phase });
    if (error) throw error;
    return { ok: data === true };
  }
}
