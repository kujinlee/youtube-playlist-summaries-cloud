import os from 'node:os';
import { randomUUID } from 'node:crypto';
import { createClient } from '@supabase/supabase-js';
import type { JobQueue } from '@/lib/storage/job-queue';
import type { JobHandler } from '@/lib/job-queue/worker-runner';
import { runOnce } from '@/lib/job-queue/worker-runner';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
import { makeSummaryHandler } from '@/lib/job-queue/summary-handler';
import { getSupabaseEnv, getServiceRoleKey } from '@/lib/supabase/env';
import { validateStorageEnv } from '@/lib/supabase/storage-env';

const POLL_MS = 2000;

/** Abort-aware sleep: resolves early if `signal` fires mid-wait, so a SIGTERM during
 *  idle backoff doesn't block shutdown for up to POLL_MS. Always resolves, never rejects.
 *  Cleans up BOTH the timer and the abort listener on every path — `signal` is the
 *  process-lifetime controller, so a listener leaked per idle poll would grow unbounded. */
export function sleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    if (signal.aborted) return resolve(); // already shutting down — don't wait a full POLL_MS
    const onAbort = () => { clearTimeout(t); resolve(); };
    const t = setTimeout(() => { signal.removeEventListener('abort', onAbort); resolve(); }, ms);
    signal.addEventListener('abort', onAbort, { once: true });
  });
}

export async function runWorkerLoop(deps: {
  queue: JobQueue;
  handler: JobHandler;
  shutdownSignal: AbortSignal;
  workerId: string;
}): Promise<void> {
  while (!deps.shutdownSignal.aborted) {
    const r = await runOnce(deps.queue, deps.handler, {
      workerId: deps.workerId,
      shutdownSignal: deps.shutdownSignal,
    });
    if (r === 'idle') await sleep(POLL_MS, deps.shutdownSignal);
  }
}

export async function main(): Promise<void> {
  validateStorageEnv();
  const missing = ['GEMINI_API_KEY', 'YOUTUBE_API_KEY', 'SUPABASE_SERVICE_ROLE_KEY']
    .filter((name) => !process.env[name]);
  if (missing.length) {
    throw new Error(`Missing required env var(s): ${missing.join(', ')}`);
  }

  const { url } = getSupabaseEnv();
  const client = createClient(url, getServiceRoleKey(), {
    auth: { autoRefreshToken: false, persistSession: false },
  });

  const queue = new SupabaseJobQueue(client);
  const handler = makeSummaryHandler(client);
  const workerId = `${os.hostname()}-${process.pid}-${randomUUID().slice(0, 8)}`;

  const ac = new AbortController();
  process.on('SIGTERM', () => ac.abort());
  process.on('SIGINT', () => ac.abort());

  await runWorkerLoop({ queue, handler, shutdownSignal: ac.signal, workerId });
}

if (require.main === module) {
  main().catch((e) => {
    console.error(e);
    process.exit(1);
  });
}
