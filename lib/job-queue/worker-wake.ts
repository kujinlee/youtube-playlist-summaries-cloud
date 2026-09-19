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
 *
 * ⭐ AND CALLERS DO NOT AWAIT IT. All the poke has to achieve is that Fly Proxy *receives* a
 * request; the proxy starts the Machine whether or not anyone waits for the reply, and the reply
 * carries no information (the listener is a doorbell that answers 200 to everything). The web
 * process is a long-lived `node server.js`, so an un-awaited promise runs to completion — this is
 * not a serverless runtime that discards work after the response. Review round 1 filed an
 * `await`-per-video enqueue path as adding up to ~75s to one user request; not awaiting removes
 * that cost entirely rather than shrinking it.
 */

export type WorkerWake = () => Promise<void>;

/** Env var holding the worker's Flycast URL, e.g. `http://yps-worker.flycast/wake`. Absent in
 *  local dev, in tests, and on any deploy where the wake path is not set up — all of which must
 *  behave exactly as they did before this existed. */
export const WORKER_WAKE_URL_ENV = 'WORKER_WAKE_URL';

/** Bounded: a stopped machine can take seconds to boot, and we are not waiting for that. We only
 *  need the proxy to RECEIVE the request. */
const DEFAULT_TIMEOUT_MS = 1_500;

/** ⭐ ONE POKE STARTS A MACHINE; THE SECOND ONE BUYS NOTHING. After a poke has been sent, further
 *  pokes are dropped for this long. Two callers make this necessary rather than merely tidy:
 *  `enqueuePlaylist` enqueues up to 50 videos in a loop, and the job-status poll fires every ~2s
 *  while a job is queued. Without suppression, "wake the worker" would mean up to 50 requests per
 *  enqueue and one per poll forever. */
const DEFAULT_SUPPRESS_MS = 10_000;

export interface WakeOpts {
  timeoutMs?: number;
  suppressMs?: number;
  fetchImpl?: typeof fetch;
  /** Injectable clock — the suppression window is time-based and tests must not sleep for it. */
  now?: () => number;
}

export function makeWorkerWake(url: string | undefined, opts: WakeOpts = {}): WorkerWake {
  // Not configured → a true no-op. Deliberately not "try and fail quietly": nothing should reach
  // the network, so local dev and the test suite are untouched rather than merely tolerant.
  if (!url) return async () => {};

  const timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const suppressMs = opts.suppressMs ?? DEFAULT_SUPPRESS_MS;
  const doFetch = opts.fetchImpl ?? fetch;
  const now = opts.now ?? Date.now;

  // Coalescing state. Per-instance, which is why the production instance is shared — see
  // `workerWakeFromEnv`. A fresh instance per request would suppress nothing.
  let inFlight: Promise<void> | null = null;
  let lastSentAt: number | null = null;

  async function send(): Promise<void> {
    const ac = new AbortController();
    const timer = setTimeout(() => ac.abort(), timeoutMs);
    try {
      // The signal is what makes the timeout real rather than decorative — without it the promise
      // would settle while the request kept running.
      await doFetch(url as string, { method: 'POST', signal: ac.signal });
    } catch {
      // Swallowed on purpose, and this is the load-bearing line. The job is already committed;
      // a boot in progress, a missing Flycast address, or a network blip must not surface as an
      // error on a request whose work WILL get done. It is also what lets callers not await: a
      // promise that cannot reject cannot become an unhandled rejection.
    } finally {
      clearTimeout(timer);
    }
  }

  return () => {
    // Already on the wire → join it. The 2nd..50th caller in an enqueue loop gets this.
    if (inFlight) return inFlight;
    // Sent recently → the machine is already starting. Drop it.
    if (lastSentAt !== null && now() - lastSentAt < suppressMs) return Promise.resolve();

    lastSentAt = now();
    const p = send();
    inFlight = p;
    // ⚠ `.catch()` on the FINALLY chain, not just on `p` (review r3 Low 4). `.finally()` returns a
    // NEW promise that adopts the rejection, and voiding it means the caller's own `.catch()` — which
    // guards the promise IT holds — does not cover this one.
    //
    // ⚠ NO UNIT TEST CAN KILL THE REMOVAL OF THIS `.catch()`, and that is stated rather than hidden:
    // the rejection source is unreachable while `send()` swallows everything, so a single-line
    // mutation cannot express the hazard. Demonstrated with a TWO-factor probe instead, run in the
    // real image base (`node:22-bookworm-slim`, v22.23.2), with the caller's own `.catch()` attached
    // exactly as in enqueuer.ts — which is the point, since it is present in BOTH runs:
    //
    //     send() rejects + this .catch() present  -> "clean — no unhandled rejection"
    //     send() rejects + this .catch() removed  -> "UNHANDLED REJECTION: send() rejected", exit 3
    //
    // So it is load-bearing exactly when `send()` stops swallowing — i.e. it defends a future edit,
    // which is why it ships despite being latent. Leaning on "send() cannot reject" is the dependency
    // r2 Medium 4 decided this codebase should stop having; applying that decision to the two call
    // sites and not to the module itself is half a fix (review r3 Low 4).
    void p.finally(() => { if (inFlight === p) inFlight = null; }).catch(() => {});
    return p;
  };
}

/** The shared production wake, keyed on the URL it was built for. */
let shared: { url: string | undefined; wake: WorkerWake } | null = null;

/**
 * The production wake. `process.env` is read on every call — so a deploy can turn the wake on by
 * setting a secret, with no code change — and the resulting instance is SHARED across calls.
 *
 * ⚠ The sharing is not an optimisation, it is what makes suppression work. Coalescing state lives
 * in the closure, and both call sites build their wake per request (`new SupabaseEnqueuer(...)` in
 * a route handler, and the job-status GET). A fresh instance each time would have an empty
 * suppression window every time and would coalesce nothing.
 *
 * Passing `opts` opts out of sharing and returns a private instance: tests must not inherit each
 * other's suppression state. Nothing needs a reset hook, because the cache is keyed on the URL —
 * changing `WORKER_WAKE_URL` yields a fresh instance on the next call.
 */
export function workerWakeFromEnv(opts?: WakeOpts): WorkerWake {
  const url = process.env[WORKER_WAKE_URL_ENV];
  if (opts) return makeWorkerWake(url, opts);
  if (!shared || shared.url !== url) shared = { url, wake: makeWorkerWake(url) };
  return shared.wake;
}
