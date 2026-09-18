import { runWorkerLoop } from '@/worker/main';
import type { JobQueue } from '@/lib/storage/job-queue';
import type { JobHandler } from '@/lib/job-queue/worker-runner';

// Backlog #142. The worker stops ITSELF when its queue is empty: it exits 0, and with
// `[[restart]] policy = "no"` the Fly machine returns to `stopped`, where CPU and RAM bill nothing.
//
// ⭐ WHY THE WORKER AND NOT THE PROXY. Fly's autostop reference documents `soft_limit` concurrency
// and says NOTHING about an in-flight request blocking a stop. A design that held an HTTP request
// open to look "busy" would rest on behaviour Fly never promised — the shape that cost PR #318 four
// review rounds. The worker already knows whether its queue is empty; the proxy fundamentally
// cannot. So the proxy is only ever allowed to START it.
//
// ⚠ THE DANGER THIS FILE EXISTS FOR: exiting while work is still pending. A job that is `queued`
// but not yet CLAIMABLE — `run_after` in the future after a retry backoff — makes `claim()` return
// null, which looks exactly like an empty queue. Exiting then strands that job until somebody
// happens to visit the site. `hasQueuedWork()` is what distinguishes the two, and every case below
// is about getting that distinction right.

const handler: JobHandler = async () => ({ ok: true });

/** A queue that is always idle to `claim`, with `hasQueuedWork` under the test's control. */
function idleQueue(hasQueued: () => Promise<boolean>) {
  const calls = { claims: 0, hasQueued: 0 };
  const queue = {
    sweepExpired: async () => 0,
    claim: async () => { calls.claims++; return null; },
    hasQueuedWork: async () => { calls.hasQueued++; return hasQueued(); },
  } as unknown as JobQueue;
  return { queue, calls };
}

describe('the worker exits when it has nothing to do', () => {
  // Break this catches: no idle exit at all — the machine runs forever, which is the ~$10.60/mo
  // this slice exists to remove.
  test('exits on its own once the idle window has passed and the queue is truly empty', async () => {
    const { queue, calls } = idleQueue(async () => false);

    await runWorkerLoop({
      queue, handler, shutdownSignal: new AbortController().signal,
      workerId: 'idle-exit', pollMs: 1, idleExitMs: 20,
    });

    expect(calls.claims).toBeGreaterThan(0);
    expect(calls.hasQueued).toBeGreaterThan(0); // it ASKED before leaving
  }, 15_000);

  // ⭐ THE ONE THAT MATTERS. A backed-off job is `queued` but unclaimable, so `claim()` returns
  // null exactly as an empty queue does. Exiting here strands real work with no symptom.
  test('does NOT exit while a job is queued but not yet claimable', async () => {
    const ac = new AbortController();
    const { queue, calls } = idleQueue(async () => true); // something IS queued, just not due yet
    setTimeout(() => ac.abort(), 250); // the test, not the loop, ends this run

    await runWorkerLoop({
      queue, handler, shutdownSignal: ac.signal,
      workerId: 'not-idle', pollMs: 1, idleExitMs: 20,
    });

    // It kept polling instead of leaving: it asked repeatedly and never acted on a false "empty".
    expect(calls.hasQueued).toBeGreaterThan(1);
    expect(ac.signal.aborted).toBe(true); // proof the TEST stopped it, not an idle exit
  }, 15_000);

  // Break this catches: treating a failed check as "nothing queued". ⚠ The two failure directions
  // are not symmetric — a worker that stays up costs a few cents; a worker that exits with work
  // pending strands a user's job silently. Fail toward staying up.
  test('does NOT exit when it cannot tell whether work is queued', async () => {
    const ac = new AbortController();
    const { queue, calls } = idleQueue(async () => { throw new Error('transient PostgREST failure'); });
    setTimeout(() => ac.abort(), 250);

    const err = jest.spyOn(console, 'error').mockImplementation(() => {});
    await runWorkerLoop({
      queue, handler, shutdownSignal: ac.signal,
      workerId: 'cannot-tell', pollMs: 1, idleExitMs: 20,
    });
    err.mockRestore();

    expect(calls.hasQueued).toBeGreaterThan(1);
    expect(ac.signal.aborted).toBe(true);
  }, 15_000);

  // Break this catches: an idle timer that never resets, so a BUSY worker exits mid-stream the
  // moment its total uptime passes the window.
  test('does not exit while it is getting work — the idle clock restarts on every job', async () => {
    const ac = new AbortController();
    let claims = 0;
    let hasQueuedCalls = 0;
    const queue = {
      sweepExpired: async () => 0,
      // Always hands back a job, so the worker is never idle.
      claim: async () => {
        claims++;
        if (claims >= 6) ac.abort();
        return { id: `j${claims}`, leaseToken: 't', ownerId: 'o', playlistId: 'p', videoId: 'v',
                 payload: {}, attempts: 1 };
      },
      complete: async () => ({ ok: true }),
      getStatus: async () => ({ cancelRequested: false }),
      setProgressPhase: async () => ({ ok: true }),
      heartbeat: async () => ({ ok: true }),
      hasQueuedWork: async () => { hasQueuedCalls++; return false; },
    } as unknown as JobQueue;

    await runWorkerLoop({
      queue, handler, shutdownSignal: ac.signal,
      workerId: 'busy', pollMs: 1, idleExitMs: 20,
    });

    expect(claims).toBeGreaterThanOrEqual(6);
    expect(hasQueuedCalls).toBe(0); // never even considered leaving while work kept arriving
  }, 15_000);

  // Break this catches: defaulting idleExitMs to something finite, which would make the CURRENT
  // production worker start exiting before the Fly-side wake path exists to bring it back.
  // ⚠ Enabling the exit is a fly.toml + Flycast change, not a code default.
  test('never exits on its own when no idle window is configured', async () => {
    const ac = new AbortController();
    const { queue, calls } = idleQueue(async () => false);
    setTimeout(() => ac.abort(), 200);

    await runWorkerLoop({
      queue, handler, shutdownSignal: ac.signal, workerId: 'no-exit', pollMs: 1,
    }); // NO idleExitMs

    expect(calls.hasQueued).toBe(0); // the question is never even asked
    expect(ac.signal.aborted).toBe(true);
  }, 15_000);
});

// ⭐ A DECISION BECOMES A GATE BY ASSERTING THE WORLD STILL MATCHES IT (CLAUDE.md).
//
// The wake path only works if fly.toml's worker service routes to the port the worker actually
// binds. Those are two literals in two files, joined by a comment — the exact shape that let
// SWEEP_MS drift to 30 minutes against a 120s lease with every gate green, earlier on this branch's
// predecessor. A mismatch here is worse than slow: Fly Proxy would route to a dead port, the wake
// would fail silently (the poke is best-effort BY DESIGN and swallows it), the machine would never
// start, and jobs would queue forever with nothing red anywhere.
describe('the wake port fly.toml routes to is the port the worker binds', () => {
  test('fly.toml worker service internal_port === WAKE_PORT', async () => {
    const { readFileSync } = await import('node:fs');
    const { WAKE_PORT } = await import('@/worker/main');

    const toml = readFileSync(`${process.cwd()}/fly.toml`, 'utf-8');
    // The worker's [[services]] block, identified by its own processes line rather than position.
    const blocks = toml.split('[[services]]').slice(1);
    const workerBlock = blocks.find((b) => /processes\s*=\s*\[\s*"worker"\s*\]/.test(b));
    expect(workerBlock).toBeDefined(); // CANNOT RUN if the service block is gone — fail, don't pass

    const port = Number(/internal_port\s*=\s*(\d+)/.exec(workerBlock as string)?.[1]);
    expect(port).toBe(WAKE_PORT);
  });

  // Break this catches: deleting the restart policy, which would turn every idle-exit into an
  // instant restart — a boot loop that bills more than never exiting at all.
  test('fly.toml gives the worker restart policy "no", so exiting means stopped', async () => {
    const { readFileSync } = await import('node:fs');
    const toml = readFileSync(`${process.cwd()}/fly.toml`, 'utf-8');
    const blocks = toml.split('[[restart]]').slice(1);
    const workerBlock = blocks.find((b) => /processes\s*=\s*\[\s*"worker"\s*\]/.test(b));
    expect(workerBlock).toBeDefined();
    expect(/policy\s*=\s*"no"/.test(workerBlock as string)).toBe(true);
  });

  // backlog #141 — the armed trap. The live web machine has said 0 since 2026-09-18; if this file
  // says 1, the next deploy silently reverts it and ~$5/mo comes back with no symptom.
  test('fly.toml lets the web machine actually suspend (min_machines_running = 0)', async () => {
    const { readFileSync } = await import('node:fs');
    const toml = readFileSync(`${process.cwd()}/fly.toml`, 'utf-8');
    const http = toml.split('[http_service]')[1]?.split('\n[[')[0];
    expect(http).toBeDefined();
    expect(/min_machines_running\s*=\s*0/.test(http as string)).toBe(true);
  });
});
