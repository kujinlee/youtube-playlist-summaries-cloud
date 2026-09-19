import { workerWakeFromEnv, type WorkerWake } from './worker-wake';
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
  /** `wake` nudges a stopped worker machine awake (backlog #142). Injected so tests need no
   *  network and so an unconfigured deploy gets a true no-op. */
  constructor(
    private serviceClient: SupabaseClient,
    private wake: WorkerWake = workerWakeFromEnv(),
  ) {}

  async enqueue(ctx: EnqueueCtx, key: JobKey, payload: IngestionPayload | DigJobPayload): Promise<EnqueueResult> {
    const { data, error } = await this.serviceClient.rpc('enqueue_job', {
      p_owner_id: ctx.ownerId, p_playlist_id: key.playlistId, p_video_id: key.videoId, p_section_id: key.sectionId,
      p_job_kind: key.kind, p_job_version: key.version, p_payload: payload, p_enqueue_ip: ctx.enqueueIp,
    });
    if (error) throw mapEnqueueError(error);
    const row = data[0];
    // ⭐ AFTER the row is committed, never before — that ordering is what makes the wake an
    // optimisation rather than a correctness requirement. If this poke fails (machine mid-boot,
    // Flycast unset, network blip) the job is already durable and simply waits for the next wake.
    //
    // ⭐ AND NOT AWAITED. `enqueuePlaylist` calls this in a sequential loop over up to 50 videos;
    // awaiting a 1500ms-bounded POST each time added up to ~75s to one user request (review r1 F3),
    // and bought nothing — all the poke has to do is reach the proxy, which starts the Machine
    // without anyone waiting for the reply. The web process is a long-lived `node server.js`, so the
    // work is not discarded after the response is sent.
    //
    // ⚠ `.catch()` even though `wake` cannot reject today (worker-wake.ts swallows everything).
    // An earlier version of this comment leaned on that invariant and stopped there. Review r2
    // measured that the test guarding this passed only because it returned before the microtask
    // queue drained — add a 50ms settle and it went red on the real rejection. The invariant was
    // enforced one module away and the guard for it was vacuous. An un-awaited rejection kills the
    // process under Node's default `--unhandled-rejections=throw`; this makes the call site not care.
    void this.wake().catch(() => {});
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
