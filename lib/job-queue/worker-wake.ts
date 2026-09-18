/**
 * Waking a stopped worker machine (backlog #142).
 *
 * The worker stops itself when its queue drains, so the machine that would pick up a new job may
 * not be running when one is enqueued. Fly Proxy starts a stopped Machine when a request is routed
 * to it — but ONLY through a service address (Flycast). `.internal` bypasses the proxy entirely:
 * *"Requests to apps without services configured on your private network don't get routed through
 * Fly Proxy and so Machines can't be automatically stopped or started by Fly Proxy."* That is
 * precisely why a queue worker, which only ever polls outbound, cannot wake itself today.
 *
 * ⭐ THE POKE IS AN OPTIMISATION, NOT A CORRECTNESS REQUIREMENT, and everything here follows from
 * that. `enqueue_job` has already committed the row before this is called, so a poke that fails
 * costs LATENCY — the job waits for the next wake — and never costs work. Therefore this function
 * never throws, never blocks for long, and does nothing at all when unconfigured.
 */

export type WorkerWake = () => Promise<void>;

/** Env var holding the worker's Flycast URL, e.g. `http://yps-worker.flycast/wake`. Absent in
 *  local dev, in tests, and on any deploy where the wake path is not set up — all of which must
 *  behave exactly as they did before this existed. */
export const WORKER_WAKE_URL_ENV = 'WORKER_WAKE_URL';

/** Bounded: a stopped machine can take seconds to boot, and the caller is holding a user's request.
 *  We only need the proxy to RECEIVE the request — it starts the machine whether or not we wait for
 *  the reply. */
const DEFAULT_TIMEOUT_MS = 1_500;

export function makeWorkerWake(
  url: string | undefined,
  opts: { timeoutMs?: number; fetchImpl?: typeof fetch } = {},
): WorkerWake {
  // Not configured → a true no-op. Deliberately not "try and fail quietly": nothing should reach
  // the network, so local dev and the test suite are untouched rather than merely tolerant.
  if (!url) return async () => {};

  const timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const doFetch = opts.fetchImpl ?? fetch;

  return async () => {
    const ac = new AbortController();
    const timer = setTimeout(() => ac.abort(), timeoutMs);
    try {
      // The signal is what makes the timeout real rather than decorative — without it the promise
      // would settle while the request kept running.
      await doFetch(url, { method: 'POST', signal: ac.signal });
    } catch {
      // Swallowed on purpose, and this is the load-bearing line. The job is already committed;
      // a boot in progress, a missing Flycast address, or a network blip must not surface as an
      // error on a request whose work WILL get done.
    } finally {
      clearTimeout(timer);
    }
  };
}

/** The production wake, read from the environment at call time so a deploy can turn it on without
 *  a code change. */
export function workerWakeFromEnv(opts?: { timeoutMs?: number; fetchImpl?: typeof fetch }): WorkerWake {
  return makeWorkerWake(process.env[WORKER_WAKE_URL_ENV], opts);
}
