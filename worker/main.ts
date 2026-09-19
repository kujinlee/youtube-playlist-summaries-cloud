import os from 'node:os';
import http from 'node:http';
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
  /** Stop the worker after this long with nothing to do, so the Fly machine can return to
   *  `stopped` and bill nothing (backlog #142).
   *
   *  ⚠ UNSET MEANS NEVER EXIT, and that default is deliberate: a worker that exits before the
   *  Flycast wake path exists has no way to come back, so enabling this is a fly.toml change and
   *  not a code default. */
  idleExitMs?: number;
  /** Idle backoff between polls. Overridable so cadence tests need not run in real time. */
  pollMs?: number;
  /** Sweep cadence. Defaults to one gate per loop — note it is built HERE, once, not per
   *  iteration: a gate constructed inside the while would reset its cursor every poll and be
   *  due every time, which is the pre-2026-09-18 behaviour wearing a gate's clothes. */
  sweepGate?: SweepPolicy;
}): Promise<void> {
  const pollMs = deps.pollMs ?? POLL_MS;
  const sweepPolicy = deps.sweepGate ?? makeSweepGate(SWEEP_MS);
  let idleSince: number | null = null;
  while (!deps.shutdownSignal.aborted) {
    try {
      const r = await runOnce(deps.queue, deps.handler, {
        workerId: deps.workerId,
        shutdownSignal: deps.shutdownSignal,
        sweepPolicy,
      });
      if (r !== 'idle') {
        idleSince = null; // got work — the idle clock restarts, so a busy worker never leaves
      } else if (deps.idleExitMs !== undefined) {
        idleSince ??= Date.now();
        if (Date.now() - idleSince >= deps.idleExitMs) {
          if (await queueIsDrained(deps.queue)) return;
          // ⭐ NOT DRAINED → RESTART THE IDLE CLOCK, and this one line is the whole of review r1 F6.
          // Without it `now - idleSince >= idleExitMs` stays true forever once it first holds, so
          // the drain COUNT query above re-runs on every poll — every 2s, ~43,200/day — for as
          // long as anything is queued-but-unclaimable. (An earlier version of this comment added
          // "on a predicate no index serves". Review r2 found `jobs_claim` and `jobs_sweep` are
          // partial indexes that between them cover `status in ('queued','active')`, so a BitmapOr
          // is available; neither of us ran EXPLAIN, so the clause is cut rather than reversed. The
          // round-trip count carries the argument without it.) PR #318
          // landed three weeks ago precisely because idle polling was 100% of this project's
          // Supabase traffic; this would have quietly rebuilt a slice of it. Resetting makes the
          // interface's own "cost is once per idle window" docstring TRUE rather than wishful.
          idleSince = Date.now();
          // ⭐ AND SAY SO. Staying alive while work is genuinely pending is CORRECT — exiting would
          // leave a backed-off job asleep until a visitor happened by. The defect r1 F7 named is
          // that it was SILENT: a machine that never stops, for a good reason nobody can see. One
          // line per idle window is cheap and makes "why is this still running?" answerable.
          console.log(`[worker] staying alive: unfinished work in the queue; next check in ${deps.idleExitMs}ms`);
        }
      }
      if (r === 'idle') await sleep(pollMs, deps.shutdownSignal);
    } catch (e) {
      // A transient queue/network error (e.g. sweepExpired/claim throwing) must NOT kill the
      // long-lived worker — log, back off, and continue until shutdown is requested.
      console.error('[worker] loop iteration error (continuing):', e);
      await sleep(pollMs, deps.shutdownSignal);
    }
  }
}

/** Port the worker's wake listener binds. Must match `internal_port` of the worker service in
 *  **fly.worker.toml** — the `yps-worker` app. NOT fly.toml, which now deliberately declares no
 *  worker service at all (review r1 F2). If they disagree, Fly Proxy has nowhere to route and the
 *  machine never autostarts. Asserted by a test, because two literals in two files joined by a
 *  comment is the shape that let SWEEP_MS drift on this branch's predecessor. */
export const WAKE_PORT = 8081;

/** Env var holding the idle window, in ms. ⚠ ABSENT = NEVER EXIT, and that is the safe default:
 *  a worker that exits before the Flycast wake path is deployed has no way to come back. Turning
 *  this on is a fly.toml change, made in the same commit as the service block that can wake it. */
export const IDLE_EXIT_MS_ENV = 'WORKER_IDLE_EXIT_MS';

/** Parses the idle window, refusing anything that is not a positive number rather than silently
 *  treating it as 0 — which would make the worker exit on its very first idle poll. */
export function idleExitMsFromEnv(env: NodeJS.ProcessEnv = process.env): number | undefined {
  const raw = env[IDLE_EXIT_MS_ENV];
  if (raw === undefined || raw.trim() === '') return undefined;
  const n = Number(raw);
  if (!Number.isFinite(n) || n <= 0) {
    console.error(`[worker] ignoring invalid ${IDLE_EXIT_MS_ENV}=${JSON.stringify(raw)} — staying alive`);
    return undefined;
  }
  return n;
}

/** A doorbell, not an API.
 *
 *  ⭐ This server exists ONLY so the worker process group HAS a service, because that is what lets
 *  Fly Proxy autostart a stopped machine: *"Requests to apps without services configured … don't
 *  get routed through Fly Proxy and so Machines can't be automatically stopped or started."* The
 *  request itself is discarded — the poll loop booting alongside it is what claims the job.
 *
 *  ⚠ Deliberately does NO work. A listener that claimed or enqueued would be a second, racier path
 *  into the same queue, and the queue's concurrency guarantees are the ones PR #318 spent four
 *  review rounds establishing on ONE path. */
export interface WakeListener {
  port: number;
  close: () => Promise<void>;
  /** ⚠ Exposed ONLY so tests can emit a post-bind `error`, which is otherwise unreachable from
   *  outside — and an unreachable failure path is one nobody can prove works. Production code must
   *  not touch this. */
  server: http.Server;
}

/** ⭐ `onFatal` IS REQUIRED, AND THE ORDER OF THESE PARAMETERS IS WHY (review r2).
 *
 *  It was optional, with `main()` passing `() => ac.abort()`. Reverting that one call site to
 *  `startWakeListener()` compiled cleanly and left all 35 cases green — a mutation that silently
 *  restored the exact defect Codex had just filed, because the tests inject `onFatal` themselves and
 *  therefore prove the MECHANISM while saying nothing about the CALL SITE. That is the same shape as
 *  the original bug: the handler existed and nothing used it.
 *
 *  Making it required moves the failure from "a test might catch it" to "it does not compile", and
 *  `port` follows it so the common caller can still omit the port. */
export function startWakeListener(onFatal: () => void, port: number = WAKE_PORT): Promise<WakeListener> {
  const server = http.createServer((_req, res) => { res.writeHead(200); res.end('awake\n'); });
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    // ⚠ NO HOST ARGUMENT, AND THIS IS A DECLINED FINDING, NOT AN OVERSIGHT (review r1, Codex
    // Medium 3; r2 Medium 2 caught that it had been dropped silently). Codex read Fly's "bind to
    // 0.0.0.0" guidance and filed the omitted host as a risk. The Claude half then MEASURED it:
    // `listen(port)` with no host binds `::` dual-stack (`node -e` reported
    // `{ address: '::', family: 'IPv6' }`), and Flycast traffic is IPv6, so it arrives. Passing
    // '0.0.0.0' would bind IPv4 ONLY and is the change that would actually break this path.
    // Left as-is deliberately; reversing it needs a measurement, not the doc sentence.
    server.listen(port, () => {
      // ⚠ RE-ARM THE ERROR HANDLER AFTER LISTENING (review r1 F10). The `once('error', reject)`
      // above only covers failure to bind: past this point the promise is settled, so a later
      // server error would have rejected an already-resolved promise — i.e. vanished. The doorbell
      // could then die while the machine still looked healthy, leaving it permanently unwakeable
      // with nothing logged.
      //
      // ⭐ AND `onFatal` IS WHAT MAKES THAT MORE THAN A LOG LINE (review r2, Codex Medium 1). The
      // first version of this handler set `process.exitCode = 1` and closed the server — but
      // `main()` is awaiting `runWorkerLoop()`, and nothing told the loop to stop. So the process
      // did NOT exit: it kept polling with the doorbell shut, unwakeable, and with no idle window
      // configured it would never have restarted at all. Setting an exit code only decides what
      // the code will be IF the process exits; it cannot cause the exit. `onFatal` aborts the
      // shutdown signal, so the loop stops and the non-zero exit brings the machine back under
      // `on-failure`.
      //
      // ⛔ AND IT DOES NOT LET THE IN-FLIGHT JOB FINISH. The first version of this comment said it
      // did; review r2 drove the real path and measured otherwise — `ac.signal` IS the handler's
      // signal (`worker-runner.ts` folds `shutdownSignal` in via `AbortSignal.any`), so the handler
      // is ABORTED: `handlerSawAbort=true, handlerFinished=false`, then
      // `fail_job(..., billableSucceeded: true)`, and with the live `summary_max_attempts = 1` that
      // is `dead_letter` on the first occurrence WITH THE SPEND KEPT. That is open backlog #139,
      // which had three known triggers; this is a FOURTH, and it needs no deploy.
      //
      // Accepted deliberately, because every alternative available today loses the same job: a bare
      // `process.exit(1)` abandons the `active` row, and `sweep_expired_leases` dead-letters it at
      // `attempts >= max_attempts` too. The better behaviour — stop claiming, let the current job
      // finish, then exit non-zero — needs a second controller, which is exactly the design call
      // #139 is holding open. An unwakeable Machine is worse than a lost job, so this ships.
      server.on('error', (e) => {
        console.error('[worker] wake listener failed after binding — shutting down so Fly restarts us:', e);
        process.exitCode = 1;
        onFatal();
      });
      const addr = server.address();
      resolve({
        server,
        port: typeof addr === 'object' && addr ? addr.port : port,
        // Closing matters: the exit path is `process exits 0 -> machine returns to stopped`, and a
        // live handle would hold the event loop open and bill forever while looking idle.
        // ⚠ IDEMPOTENT, and NOT because the fatal path closes the server — it no longer does; it
        // only aborts. The real second caller is an ordinary one: `main()` closes this in a
        // `finally`, and any other close (a test's, a future caller's) makes that the second. Node
        // answers a second `close()` with
        // `ERR_SERVER_NOT_RUNNING`, which would have turned a recovery into a rejection out of the
        // `finally` block — losing the original error.
        close: () => new Promise<void>((res2, rej2) => {
          if (!server.listening) return res2();
          server.close((e) => (e ? rej2(e) : res2()));
        }),
      });
    });
  });
}

/** True only when we are CERTAIN there is nothing left to do.
 *
 *  ⚠ THE TWO FAILURE DIRECTIONS ARE NOT SYMMETRIC, which is the whole reason this is a named
 *  function rather than an inline `await`. A worker that stays up too long costs a few cents. A
 *  worker that exits with a job still queued strands that job until somebody happens to visit the
 *  site — silently, with no error anywhere. So an unanswerable question resolves to "not drained".
 *
 *  ⚠ And `claim()` returning null is NOT this question: a job whose retry backoff has not elapsed
 *  is `queued` and unclaimable at the same time. */
async function queueIsDrained(queue: JobQueue): Promise<boolean> {
  try {
    return !(await queue.hasUnfinishedWork());
  } catch (e) {
    console.error('[worker] could not determine whether work is queued (staying alive):', e);
    return false;
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

  // The listener is what Fly Proxy routes at to START this machine; the loop is what does the work.
  // Started BEFORE the loop so a wake arriving during boot is answered rather than refused.
  const listener = await startWakeListener(() => ac.abort());
  try {
    await runWorkerLoop({
      queue, handler, shutdownSignal: ac.signal, workerId,
      idleExitMs: idleExitMsFromEnv(),
    });
  } finally {
    // Must close, or the process cannot exit 0 and the machine never returns to `stopped`.
    await listener.close();
  }
}

if (require.main === module) {
  main().catch((e) => {
    console.error(e);
    process.exit(1);
  });
}
