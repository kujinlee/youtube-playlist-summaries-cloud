import type { SupabaseClient } from '@supabase/supabase-js';
import { loadSummaryForServe } from '@/lib/html-doc/serve-summary-core';
import { parseSummaryMarkdown } from '@/lib/html-doc/parse';
import { digSectionKey, digJobVersion } from '@/lib/dig/cloud/dig-blob-key';
import type { Enqueuer } from '@/lib/job-queue/enqueuer';
import { QuotaExceededError, DailyCapError, VideoTooLongError } from '@/lib/job-queue/errors';

export interface EnqueueDigDeps {
  supabase: SupabaseClient;   // session client — auth + tenant reads (RLS)
  enqueuer: Enqueuer;         // service-role — enqueue RPC only
  userId: string;
  isAnonymous: boolean;
  videoId: string;
  playlistId: string;
  sectionId: number;
  enqueueIp: string | null;
}

export interface EnqueueDigResult { status: number; body: Record<string, unknown>; }

/** Cloud dig trigger core: authorize + gate (via loadSummaryForServe, which does NOT charge a
 *  magazine model), validate the section, dedup on the current-version blob, preflight, enqueue.
 *  Charge happens once, inside enqueue_job, only on a fresh enqueue. */
export async function enqueueDig(deps: EnqueueDigDeps): Promise<EnqueueDigResult> {
  // Anon dig allowance is 0 → 403, distinct from a registered user's quota-exhausted 429.
  if (deps.isAnonymous) return { status: 403, body: { error: 'dig requires an account' } };

  const load = await loadSummaryForServe(deps.supabase, {
    videoId: deps.videoId, playlistId: deps.playlistId, userId: deps.userId,
  });
  if (!load.ok) return { status: load.status, body: { error: load.error } };

  const parsed = parseSummaryMarkdown(load.mdBytes.toString('utf-8'));
  const section = parsed.sections.find((s) => s.timeRange?.startSec === deps.sectionId);
  if (!section) return { status: 404, body: { error: 'section not found' } };

  // Dedup authority = the current-version blob. Present → done, no enqueue, no charge.
  const key = digSectionKey(load.base, deps.sectionId);
  if (await load.bundle.blobStore.exists(load.principal, key)) {
    return { status: 200, body: { status: 'ready', sectionId: deps.sectionId } };
  }

  const verdict = await deps.enqueuer.preflight(deps.enqueueIp, deps.userId);
  if (verdict.velocityExceeded) return { status: 429, body: { error: 'rate limited' } };
  if (verdict.atCapacity) return { status: 503, body: { error: 'at capacity' } };
  if (!verdict.admitted) return { status: 403, body: { error: 'forbidden' } };

  try {
    const res = await deps.enqueuer.enqueue(
      { ownerId: deps.userId, enqueueIp: deps.enqueueIp },
      { playlistId: deps.playlistId, videoId: deps.videoId, sectionId: deps.sectionId, kind: 'dig', version: digJobVersion() },
      { durationSeconds: load.video.durationSeconds },
    );
    // §9.2: the idempotency index includes 'completed'. If we joined a completed row while the
    // current-version blob was absent above, do NOT promise a job that will never run. Re-check the
    // blob: a concurrent worker may have just promoted it (→ ready), else the blob was lost (→ repair).
    if (res.joined && res.status === 'completed') {
      if (await load.bundle.blobStore.exists(load.principal, key)) {
        return { status: 200, body: { status: 'ready', sectionId: deps.sectionId } };
      }
      return { status: 409, body: { error: 'repair needed', sectionId: deps.sectionId } };
    }
    return { status: 202, body: { status: 'enqueued', jobId: res.jobId, sectionId: deps.sectionId } };
  } catch (e) {
    if (e instanceof QuotaExceededError) return { status: 429, body: { error: 'quota exceeded' } };
    if (e instanceof DailyCapError) return { status: 503, body: { error: 'at capacity' } };
    if (e instanceof VideoTooLongError) return { status: 400, body: { error: 'video too long' } };
    throw e;
  }
}
