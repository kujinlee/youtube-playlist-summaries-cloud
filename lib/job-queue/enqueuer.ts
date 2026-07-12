import type { SupabaseClient } from '@supabase/supabase-js';
import type { JobKey, EnqueueResult } from '@/lib/storage/job-queue';
import type { IngestionPayload } from '@/lib/job-queue/ingestion-payload';
import { mapEnqueueError } from '@/lib/job-queue/errors';

/** Owner/IP context threaded through the service-role enqueue path so
 * `enqueue_job` can enforce per-owner quota/cap without a session client. */
export interface EnqueueCtx {
  ownerId: string;
  enqueueIp: string | null;
}

/** Result of `enqueue_preflight` — an advisory gate checked before fan-out. */
export interface PreflightVerdict {
  admitted: boolean;
  atCapacity: boolean;
  velocityExceeded: boolean;
  challengeRequired: boolean;
}

/** Guardrail config values the producer/handler need to read (subset). */
export interface GuardrailConfigView {
  maxDurationSeconds: number;
}

export interface DigJobPayload { durationSeconds: number; } // enqueue_job reads only durationSeconds (PJ003 backstop)

/**
 * Service-role enqueue/preflight surface. Deliberately has NO read/list/status
 * method — the two-client split (session for reads, service for
 * enqueue+preflight) forbids a tenant-read path from ever running under
 * service-role, which would bypass RLS and risk a cross-owner leak.
 */
export interface Enqueuer {
  enqueue(ctx: EnqueueCtx, key: JobKey, payload: IngestionPayload | DigJobPayload): Promise<EnqueueResult>;
  preflight(ip: string | null, ownerId: string): Promise<PreflightVerdict>;
  getGuardrailConfig(): Promise<GuardrailConfigView>;
}

/**
 * Service-role `Enqueuer`: wires `enqueue_job`/`enqueue_preflight` (both service-role-only
 * RPCs, `returns table(...)` — supabase-js resolves these to an array, unwrap via `data[0]`,
 * matching the existing convention in `lib/storage/supabase/supabase-job-queue.ts`) and reads
 * the singleton `guardrail_config` row.
 */
export class SupabaseEnqueuer implements Enqueuer {
  constructor(private serviceClient: SupabaseClient) {}

  async enqueue(ctx: EnqueueCtx, key: JobKey, payload: IngestionPayload | DigJobPayload): Promise<EnqueueResult> {
    const { data, error } = await this.serviceClient.rpc('enqueue_job', {
      p_owner_id: ctx.ownerId, p_playlist_id: key.playlistId, p_video_id: key.videoId, p_section_id: key.sectionId,
      p_job_kind: key.kind, p_job_version: key.version, p_payload: payload, p_enqueue_ip: ctx.enqueueIp,
    });
    if (error) throw mapEnqueueError(error);
    const row = data[0];
    return { jobId: row.job_id, status: row.status, joined: row.joined };
  }

  async preflight(ip: string | null, ownerId: string): Promise<PreflightVerdict> {
    const { data, error } = await this.serviceClient.rpc('enqueue_preflight', { p_ip: ip, p_owner_id: ownerId });
    if (error) throw mapEnqueueError(error);
    const row = data[0];
    return {
      admitted: row.admitted, atCapacity: row.at_capacity,
      velocityExceeded: row.velocity_exceeded, challengeRequired: row.challenge_required,
    };
  }

  async getGuardrailConfig(): Promise<GuardrailConfigView> {
    const { data, error } = await this.serviceClient
      .from('guardrail_config').select('max_duration_seconds').single();
    if (error) throw error;
    return { maxDurationSeconds: data.max_duration_seconds };
  }
}
