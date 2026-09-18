import os from 'node:os';
import { randomUUID } from 'node:crypto';
import { createClient } from '@supabase/supabase-js';
import type { JobQueue } from '@/lib/storage/job-queue';
import type { JobHandler, SweepPolicy } from '@/lib/job-queue/worker-runner';
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
 *  `claim_next_job` per sampled window, while the queue sat empty. Half of that was the sweep,
 *  and a lease is 120s, so it was looking for expiries sixty times more often than one could occur.
 *
 *  ⚠ THE EGRESS RANGE, STATED WITH ITS ASSUMPTION, because the first version of this comment gave
 *  a span that could not be derived from its own evidence (r1 Low, Codex). A response was measured
 *  at 919 B of headers + a 2 B body = 921 B. Over the six full days sampled (76,040-81,313 req/day)
 *  that is 2.13-2.28 GB/month decimal, i.e. 43-46% of the Free plan's 5 GB. That measurement came
 *  from a FRESH TLS connection, which always receives the ~295 B `set-cookie: __cf_bm`; if the
 *  worker's keep-alive client does not get it per response the figure is ~1.45-1.55 GB (29-31%).
 *  Which of the two holds is UNMEASURED — 43-46% is what the evidence directly supports.
 *
 *  (Month length 30.44 days — the mean. Recomputing with 30 gives 2.10-2.25 and looks like a
 *  discrepancy.)
 *
 *  Kept well under the DEFAULT_LEASE_SECONDS lease so an expiry is still reclaimed promptly.
 *
 *  ⚠ THE COST, DERIVED FROM THE SQL RATHER THAN ASSERTED — r1 Medium (Claude half 3), and the
 *  earlier "~180s to recovery" in this comment was wrong in a way no `~` covers.
 *
 *  What SWEEP_MS delays is the REQUEUE, not the re-run: ~122s -> ~182s. What happens next is
 *  decided by `sweep_expired_leases` (0009:68-73), which branches on attempts vs max_attempts and,
 *  on the retry branch, sets `run_after = now() + 10 * 4^(attempts-1)` seconds — and
 *  `claim_next_job` (0008:106) will not touch the row until `run_after <= now()`. `attempts` is
 *  already >= 1, incremented at claim time (0008:104).
 *
 *  MEASURED against prod 2026-09-18 — `guardrail_config` is `summary_max_attempts = 1`,
 *  `dig_max_attempts = 2`, and all 15 jobs ever run carry `max_attempts = 1`, `max(attempts) = 1`:
 *
 *    summary (max_attempts 1): a first crash has attempts(1) >= max_attempts(1), so the sweep
 *      sets 'dead_letter' and leaves run_after alone. THE JOB IS NEVER RETRIED — "recovery" does
 *      not happen at all, and this change only delays the dead-lettering, ~122s -> ~182s.
 *    dig (max_attempts 2): a first crash requeues with a 10s backoff, so ~134s -> ~192s.
 *      A second crash dead-letters.
 *
 *  So the 40s and 160s rungs of that exponential are UNREACHABLE at the current configuration,
 *  and would only matter if max_attempts were raised. In every reachable case the DELTA this
 *  change adds is the same: up to SWEEP_MS. That delta is what the branch claims credit for; the
 *  absolute "~180s to recovery" was never a thing the code did.
 *
 *  Nothing on the job-start path is affected; claim_next_job still runs every POLL_MS.
 *
 *  ⚠ "Well under the lease" IS THE INVARIANT EVERY BOUND HERE RESTS ON, and until r1 it was prose
 *  connecting two literals in two modules: raising this to 30 minutes left tsc clean and every
 *  gate green while ~180s silently became ~32 minutes. It is now asserted against
 *  DEFAULT_LEASE_SECONDS in tests/lib/lease-sweep-cadence.test.ts — a decision became a gate. */
export const SWEEP_MS = 60_000;

/** Time-gated sweep cadence: due at most once per `intervalMs`, whatever the call rate.
 *
 *  ⚠ The cursor advances ONLY in onSwept(), never in due(). Advancing it on every DUE CHECK
 *  would mean `now - last` is perpetually one poll interval under a fast caller, never reaching
 *  `intervalMs`, and the sweep would never run again for the life of the process — lease
 *  reclamation silently dead, with nothing to report it.
 *
 *  ⚠ And onSwept() is called only after the sweep RESOLVES (see runOnce). Spending the window on
 *  an attempt that threw would push worst-case crash recovery from ~180s to ~240s on a single
 *  transient failure, and further when blips land on window boundaries — r1 Medium, found by
 *  Codex. Both properties are pinned in tests/lib/lease-sweep-cadence.test.ts.
 *
 *  The clock is MONOTONIC (`performance.now()`), not wall-clock: an NTP step backwards makes a
 *  `Date.now()` delta negative, which compares as "inside the window" and suppresses sweeps until
 *  the host catches up — r1 Low. The negative delta is ALSO floored below, so the gate fails safe
 *  (sweeps sooner) even if a caller injects a wall clock, which the tests do.
 *
 *  ⚠ The period runs from COMPLETION, not from the due-check: onSwept() re-samples the clock after
 *  the sweep has returned, so the effective cadence is SWEEP_MS + the sweep's own latency (r1 Low).
 *  That is deliberate — it is the right semantics for a rate limiter, since measuring from the
 *  due-check would let a slow link issue overlapping sweeps — but it means the stated ~180s bound
 *  is really ~180s + one RPC round trip. At a healthy ~50ms that is noise.
 *
 *  `now` is injected so the cadence is testable without waiting out a real minute. ⚠ That makes the
 *  DEFAULT the only clock production ever uses and the one nothing exercised — `performance.now()
 *  -> Date.now()` survived the entire suite until r1. It is now pinned by a case that steps the
 *  WALL clock backwards and asserts this gate does not notice.
 *
 *  The initial cursor is -Infinity, so a freshly started worker sweeps immediately rather than
 *  ignoring whatever the previous machine's SIGTERM drain may have stranded. */
export function makeSweepGate(
  intervalMs: number,
  now: () => number = () => performance.now(),
): SweepPolicy {
  let lastSweptAt = -Infinity;
  return {
    due: () => {
      const elapsed = now() - lastSweptAt;
      return !(elapsed >= 0 && elapsed < intervalMs);
    },
    onSwept: () => { lastSweptAt = now(); },
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
   *  iteration: a gate constructed inside the while would reset its cursor every poll and be
   *  due every time, which is the pre-2026-09-18 behaviour wearing a gate's clothes. */
  sweepGate?: SweepPolicy;
}): Promise<void> {
  const pollMs = deps.pollMs ?? POLL_MS;
  const sweepPolicy = deps.sweepGate ?? makeSweepGate(SWEEP_MS);
  while (!deps.shutdownSignal.aborted) {
    try {
      const r = await runOnce(deps.queue, deps.handler, {
        workerId: deps.workerId,
        shutdownSignal: deps.shutdownSignal,
        sweepPolicy,
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
