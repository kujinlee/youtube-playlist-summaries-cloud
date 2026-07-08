import type { SupabaseClient } from '@supabase/supabase-js';
import type { JobQueue, JobKey, EnqueueResult, LeasedJob, JobRecord, JobStatus } from '@/lib/storage/job-queue';
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
      .from('jobs').select('id,status,cancel_requested,result,error').eq('id', jobId).maybeSingle();
    if (error) throw error;
    if (!data) return null;
    return { id: data.id, status: data.status, cancelRequested: data.cancel_requested, result: data.result, error: data.error };
  }

  async requestCancel(jobId: string): Promise<void> {
    const { error } = await this.client.rpc('request_cancel_job', { p_job_id: jobId });
    if (error) throw error;
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
