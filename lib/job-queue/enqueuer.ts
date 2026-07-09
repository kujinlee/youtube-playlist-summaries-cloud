import type { JobKey, EnqueueResult } from '@/lib/storage/job-queue';
import type { IngestionPayload } from '@/lib/job-queue/ingestion-payload';

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

/**
 * Service-role enqueue/preflight surface. Deliberately has NO read/list/status
 * method — the two-client split (session for reads, service for
 * enqueue+preflight) forbids a tenant-read path from ever running under
 * service-role, which would bypass RLS and risk a cross-owner leak.
 */
export interface Enqueuer {
  enqueue(ctx: EnqueueCtx, key: JobKey, payload: IngestionPayload): Promise<EnqueueResult>;
  preflight(ip: string | null, ownerId: string): Promise<PreflightVerdict>;
  getGuardrailConfig(): Promise<GuardrailConfigView>;
}
