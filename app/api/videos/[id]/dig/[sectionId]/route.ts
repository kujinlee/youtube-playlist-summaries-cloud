import crypto from 'crypto';
import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { assertOutputFolder, assertVideoId } from '@/lib/index-store';
import { cancelJob, createJob, deleteJob, emitJobEvent, getActiveJob, getJobSignal, releaseJobLock } from '@/lib/job-registry';
import { logError, errorSummary } from '@/lib/dev-logger';
import { digSection } from '@/lib/dig/dig-section';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { createServiceClient } from '@/lib/supabase/service';
import { SupabaseEnqueuer } from '@/lib/job-queue/enqueuer';
import { enqueueDig } from '@/lib/dig/cloud/enqueue-dig-core';
import { parseClientIp } from '@/lib/http/client-ip';
import type { ProgressEvent } from '@/types';

type Params = { params: Promise<{ id: string; sectionId: string }> };

const GRACE_MS = 15_000;
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const RETRY_AFTER_SECONDS = 60;

// A 429 from this route (rate-limited OR quota-exhausted — enqueueDig doesn't distinguish in the
// status code) always carries Retry-After, matching the ingest route (jobs/route.ts:54-57). This
// is a documented simplification: the monthly-quota case is imprecise but harmless with no client
// consuming this header yet.
const json = (body: unknown, status: number) =>
  NextResponse.json(body, { status, headers: status === 429 ? { 'Retry-After': String(RETRY_AFTER_SECONDS) } : undefined });

export async function POST(request: Request, { params }: Params) {
  const { id: videoId, sectionId: sectionIdParam } = await params;

  if ((process.env.STORAGE_BACKEND ?? 'local') === 'supabase') {
    const url = new URL(request.url);
    // 400-before-401 validation
    if (url.searchParams.has('outputFolder')) return json({ error: 'outputFolder not valid on this backend' }, 400);
    const sectionId = Number(sectionIdParam);
    if (!Number.isInteger(sectionId) || sectionId < 0) return json({ error: 'invalid sectionId' }, 400);
    const playlistId = url.searchParams.get('playlist');
    if (!playlistId || !UUID_RE.test(playlistId)) return json({ error: 'invalid playlist' }, 400);
    try { assertVideoId(videoId); } catch { return json({ error: 'invalid videoId' }, 400); }

    const cookieStore = (await cookies()) as unknown as CookieStore;
    const supabase = createServerSupabase(cookieStore);
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return json({ error: 'authentication required' }, 401);

    // Authoritative anon status = profiles.is_anonymous (the SAME column enqueue_job checks at
    // 0011:101), read via the session client under RLS (a user may read their own profile). Do NOT
    // trust user.is_anonymous — it is not guaranteed to be populated in this project's auth config.
    const { data: profile } = await supabase.from('profiles').select('is_anonymous').eq('id', user.id).single();

    // challengeRequired (soft captcha-UX advisory from enqueuer.preflight) is deliberately NOT
    // surfaced here, unlike the ingest route: this is a generation-only slice with no dig
    // frontend yet, and the hard gates (429/503/403) are all honored regardless. Revisit if/when
    // a dig-trigger UI needs to react to it.
    const result = await enqueueDig({
      supabase, enqueuer: new SupabaseEnqueuer(createServiceClient()),
      userId: user.id, isAnonymous: profile?.is_anonymous === true,
      videoId, playlistId, sectionId, enqueueIp: parseClientIp(request),
    });
    return json(result.body, result.status);
  }

  // ---- existing local branch (unchanged) ----
  const body = await request.json().catch(() => null);
  const outputFolder = body?.outputFolder;
  const force = Boolean(body?.force);

  if (!outputFolder) return NextResponse.json({ error: 'outputFolder is required' }, { status: 400 });

  // Validate sectionId: must be a non-empty, non-negative integer
  if (!sectionIdParam || sectionIdParam.trim() === '') {
    return NextResponse.json({ error: 'invalid sectionId' }, { status: 400 });
  }
  const sectionIdInt = Number(sectionIdParam);
  if (!Number.isInteger(sectionIdInt) || sectionIdInt < 0) {
    return NextResponse.json({ error: 'invalid sectionId' }, { status: 400 });
  }

  try {
    assertOutputFolder(outputFolder);
    assertVideoId(videoId);
  } catch {
    return NextResponse.json({ error: 'invalid request' }, { status: 400 });
  }

  const key = `${outputFolder}::${videoId}::${sectionIdInt}`;
  if (!force) {
    const existing = getActiveJob(key);
    if (existing) return NextResponse.json({ jobId: existing });
  } else {
    const existing = getActiveJob(key);
    if (existing) {
      cancelJob(existing);
      releaseJobLock(existing);
    }
  }

  const jobId = crypto.randomUUID();
  createJob(jobId, key);
  const signal = getJobSignal(jobId);
  let finished = false;

  const onTerminal = () => {
    finished = true;
    releaseJobLock(jobId);
    const t = setTimeout(() => deleteJob(jobId), GRACE_MS);
    (t as { unref?: () => void }).unref?.();
  };

  digSection(videoId, sectionIdInt, outputFolder, signal, (event: ProgressEvent) => {
    emitJobEvent(jobId, event);
    if (event.type === 'done' || event.type === 'error') onTerminal();
  }).catch((err) => {
    if (finished) return;
    logError(`dig:${videoId}:${sectionIdInt}`, err);
    emitJobEvent(jobId, { type: 'error', log: errorSummary(err) });
    onTerminal();
  });

  return NextResponse.json({ jobId });
}
