import os from 'node:os';
import { randomUUID } from 'node:crypto';
import { createClient } from '@supabase/supabase-js';
import type { JobQueue } from '@/lib/storage/job-queue';
import type { JobHandler } from '@/lib/job-queue/worker-runner';
import { runOnce } from '@/lib/job-queue/worker-runner';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
import { makeSummaryHandler } from '@/lib/job-queue/summary-handler';
import { makeDigHandler } from '@/lib/job-queue/dig-handler';
import { makeJobHandler } from '@/lib/job-queue/dispatch';
import { getSupabaseEnv, getServiceRoleKey } from '@/lib/supabase/env';
import { validateStorageEnv } from '@/lib/supabase/storage-env';

const POLL_MS = 2000;

/** How often the worker sweeps for expired leases. Deliberately DECOUPLED from POLL_MS.
 *
 *  MEASURED 2026-09-18 against prod (plan=free): the worker was 100% of the project's Supabase
 *  traffic at ~79,800 requests/day — an exact 25/25 pair of `sweep_expired_leases` and
 *  `claim_next_job` per sampled window, costing 1.5-2.2 GB/month of a 5 GB egress allowance while
 *  the queue sat empty. Half of that was the sweep, and a lease is 120s, so it was looking for
 *  expiries sixty times more often than one could occur.
 *
 *  Kept well under the 120s lease so an expiry is still reclaimed promptly. The cost of the
 *  change is bounded and worth stating: a job stranded by a crashed worker is now picked up up to
 *  SWEEP_MS later than before — a 120s lease becomes up to ~180s to recovery. Nothing on the
 *  job-start path is affected; claim_next_job still runs every POLL_MS. */
const SWEEP_MS = 60_000;

/** Time-gated predicate: returns true at most once per `intervalMs`, whatever the call rate.
 *
 *  ⚠ The cursor advances ONLY when the gate opens. Advancing it on every call would mean
 *  `now - last` is perpetually one poll interval under a fast caller, never reaching `intervalMs`,
 *  and the sweep would never run again for the life of the process — lease reclamation silently
 *  dead, with nothing to report it. `tests/lib/lease-sweep-cadence.test.ts` pins that property.
 *
 *  `now` is injected so the cadence is testable without waiting out a real minute. The initial
 *  cursor is -Infinity, so a freshly started worker sweeps immediately rather than ignoring
 *  whatever the previous machine's SIGTERM drain may have stranded. */
export function makeSweepGate(intervalMs: number, now: () => number = Date.now): () => boolean {
  let lastSweptAt = -Infinity;
  return () => {
    const t = now();
    if (t - lastSweptAt < intervalMs) return false;
    lastSweptAt = t;
    return true;
  };
}

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
  /** Idle backoff between polls. Overridable so cadence tests need not run in real time. */
  pollMs?: number;
  /** Sweep cadence. Defaults to one gate per loop — note it is built HERE, once, not per
   *  iteration: a gate constructed inside the while would reset its cursor every poll and
   *  open every time, which is the pre-2026-09-18 behaviour wearing a gate's clothes. */
  sweepGate?: () => boolean;
}): Promise<void> {
  const pollMs = deps.pollMs ?? POLL_MS;
  const shouldSweep = deps.sweepGate ?? makeSweepGate(SWEEP_MS);
  while (!deps.shutdownSignal.aborted) {
    try {
      const r = await runOnce(deps.queue, deps.handler, {
        workerId: deps.workerId,
        shutdownSignal: deps.shutdownSignal,
        shouldSweep,
      });
      if (r === 'idle') await sleep(pollMs, deps.shutdownSignal);
    } catch (e) {
      // A transient queue/network error (e.g. sweepExpired/claim throwing) must NOT kill the
      // long-lived worker — log, back off, and continue until shutdown is requested.
      console.error('[worker] loop iteration error (continuing):', e);
      await sleep(pollMs, deps.shutdownSignal);
    }
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
  const handler = makeJobHandler({
    summary: makeSummaryHandler(client),
    dig: makeDigHandler(client),
  });
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
