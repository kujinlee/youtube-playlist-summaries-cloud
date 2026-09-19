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
// happens to visit the site. `hasUnfinishedWork()` is what distinguishes the two, and every case below
// is about getting that distinction right.

const handler: JobHandler = async () => ({ ok: true });

/** A queue that is always idle to `claim`, with `hasUnfinishedWork` under the test's control. */
function idleQueue(hasQueued: () => Promise<boolean>) {
  const calls = { claims: 0, hasUnfinished: 0 };
  const queue = {
    sweepExpired: async () => 0,
    claim: async () => { calls.claims++; return null; },
    hasUnfinishedWork: async () => { calls.hasUnfinished++; return hasQueued(); },
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
    expect(calls.hasUnfinished).toBeGreaterThan(0); // it ASKED before leaving
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
    expect(calls.hasUnfinished).toBeGreaterThan(1);
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

    expect(calls.hasUnfinished).toBeGreaterThan(1);
    expect(ac.signal.aborted).toBe(true);
  }, 15_000);

  // Break this catches: an idle timer that never resets, so a BUSY worker exits mid-stream the
  // moment its total uptime passes the window.
  test('does not exit while it is getting work — the idle clock restarts on every job', async () => {
    const ac = new AbortController();
    let claims = 0;
    let hasUnfinishedCalls = 0;
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
      hasUnfinishedWork: async () => { hasUnfinishedCalls++; return false; },
    } as unknown as JobQueue;

    await runWorkerLoop({
      queue, handler, shutdownSignal: ac.signal,
      workerId: 'busy', pollMs: 1, idleExitMs: 20,
    });

    expect(claims).toBeGreaterThanOrEqual(6);
    expect(hasUnfinishedCalls).toBe(0); // never even considered leaving while work kept arriving
  }, 15_000);

  // ⭐ THE COST OF STAYING ALIVE, and the reason this is an assertion about a COUNT rather than a
  // behaviour. Once the idle window has first elapsed, `now - idleSince >= idleExitMs` stays true
  // forever unless the clock is restarted — so the drain COUNT query re-ran on EVERY poll, every
  // 2s in production, ~43,200/day, on a predicate no index serves. PR #318 landed three weeks
  // earlier precisely because idle polling was 100% of this project's Supabase traffic; this would
  // have quietly rebuilt a slice of it, while the interface docstring claimed "once per idle window".
  //
  // ⚠ Written with a wide margin on purpose. With the reset, ~4 calls fit in this run; without it,
  // ~300 do. Anything in between is still a pass, so the case cannot go red from timing jitter — it
  // goes red only if the clock stops being restarted.
  test('asks once per idle WINDOW, not once per poll, while work stays pending', async () => {
    const ac = new AbortController();
    const { queue, calls } = idleQueue(async () => true); // permanently pending work
    const log = jest.spyOn(console, 'log').mockImplementation(() => {});
    setTimeout(() => ac.abort(), 400);

    await runWorkerLoop({
      queue, handler, shutdownSignal: ac.signal,
      workerId: 'window-cost', pollMs: 1, idleExitMs: 100,
    });

    expect(calls.hasUnfinished).toBeGreaterThan(0);   // it did ask
    expect(calls.hasUnfinished).toBeLessThan(50);     // but NOT once per 1ms poll

    // And it said why it was staying — r1 F7's real defect was silence, not the behaviour: a machine
    // that never stops, for a correct reason nobody can see.
    expect(log).toHaveBeenCalledWith(expect.stringContaining('staying alive'));
    log.mockRestore();
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

    expect(calls.hasUnfinished).toBe(0); // the question is never even asked
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
describe('the Fly config the wake path depends on', () => {
  const read = async (f: string) => (await import('node:fs')).readFileSync(`${process.cwd()}/${f}`, 'utf-8');

  /** The body of a table, found by an ANCHORED HEADER LINE rather than a substring.
   *
   *  ⚠ This is not fussiness. The first version of these tests used `toml.split('[http_service]')`
   *  and matched a COMMENT that mentions `[http_service]` by name, so it read the wrong region of
   *  the file and two assertions failed for a reason that had nothing to do with the config. A
   *  header is a line that IS the header; anything else is prose about it. */
  const tableBody = (toml: string, header: string): string | undefined => {
    const lines = toml.split('\n');
    const at = lines.findIndex((l) => l.trim() === header);
    if (at === -1) return undefined;
    const rest = lines.slice(at + 1);
    const next = rest.findIndex((l) => /^\s*\[/.test(l));
    return (next === -1 ? rest : rest.slice(0, next)).join('\n');
  };

  /** Does a real table header for `header` exist? (A comment naming it does not count.) */
  const hasTable = (toml: string, header: string) =>
    toml.split('\n').some((l) => l.trim() === header);

  // Fly's three valid restart policies, from its configuration reference. The branch originally
  // wrote "no" — not one of these — and `fly config validate` refused the ENTIRE config, so it
  // could never have deployed. A test asserted the literal "no", which meant the suite DEFENDED the
  // defect: 2860 green tests over an undeployable file. Pinning the allowed SET is what turns this
  // from "matches what the author typed" into "matches what Fly accepts".
  const FLY_RESTART_POLICIES = ['always', 'never', 'on-failure'];

  test('the worker service internal_port === WAKE_PORT', async () => {
    const { WAKE_PORT } = await import('@/worker/main');
    const toml = await read('fly.worker.toml');
    const blocks = toml.split('[[services]]').slice(1);
    const workerBlock = blocks.find((b) => /processes\s*=\s*\[\s*"worker"\s*\]/.test(b));
    expect(workerBlock).toBeDefined(); // CANNOT RUN if the service block is gone — fail, don't pass

    const port = Number(/internal_port\s*=\s*(\d+)/.exec(workerBlock as string)?.[1]);
    expect(port).toBe(WAKE_PORT);
  });

  // ⭐ Break this catches the defect that shipped: a [[services]] block with no [[services.ports]].
  // `internal_port` says where the process listens INSIDE the machine; it does not open a door.
  // Fly's reference: "At least one `services.ports` entry is required for each `services` section."
  // ⚠ `fly config validate` only WARNS about this, so its green is not a substitute for this test.
  test('the worker service exposes a port — without one it accepts nothing and the slice is inert', async () => {
    const toml = await read('fly.worker.toml');
    const workerBlock = toml.split('[[services]]').slice(1)
      .find((b) => /processes\s*=\s*\[\s*"worker"\s*\]/.test(b));
    expect(workerBlock).toBeDefined();
    expect(workerBlock as string).toContain('[[services.ports]]');

    // Port 80 + the http handler, because Flycast is HTTP-only and WORKER_WAKE_URL is
    // `http://yps-worker.flycast/wake` — port 80 implicitly. These two must agree.
    const ports = (workerBlock as string).split('[[services.ports]]')[1];
    expect(/port\s*=\s*80\b/.test(ports)).toBe(true);
    expect(/handlers\s*=\s*\[\s*"http"\s*\]/.test(ports)).toBe(true);
  });

  // ⭐ Review r2 (Codex): flipping `auto_start_machines` to false left all 13 cases green AND passed
  // `fly config validate` — a silent, total disabling of wake-on-visit with no symptom anywhere.
  // Autostart is the entire mechanism: without it the poke reaches a proxy that will not start the
  // Machine, and jobs queue behind a worker that never wakes.
  //
  // `min_machines_running = 0` is the matching half. At 1 the Machine is pinned up and the
  // idle-exit is pointless — the same defect backlog #141 filed against the web app.
  test('the worker service can be auto-STARTED and is not pinned up', async () => {
    const toml = await read('fly.worker.toml');
    const workerBlock = toml.split('[[services]]').slice(1)
      .find((b) => /processes\s*=\s*\[\s*"worker"\s*\]/.test(b));
    expect(workerBlock).toBeDefined();

    expect(/auto_start_machines\s*=\s*true/.test(workerBlock as string)).toBe(true);
    expect(/min_machines_running\s*=\s*0/.test(workerBlock as string)).toBe(true);

    // ⚠ And NOT auto_stop: the worker stops itself by exiting. Fly's autostop reference says
    // nothing about an in-flight request blocking a stop, so the proxy must never make that call.
    expect(/auto_stop_machines/.test(workerBlock as string)).toBe(false);
  });

  // Break this catches: an invalid policy (what shipped), and `never`, which would silently throw
  // away crash recovery. Under `on-failure` a clean exit 0 still leaves the machine `stopped` —
  // identical to `never` for the idle-exit — while a crash is still restarted.
  test('the worker restart policy is one Fly accepts, and is on-failure', async () => {
    const toml = await read('fly.worker.toml');
    const workerBlock = toml.split('[[restart]]').slice(1)
      .find((b) => /processes\s*=\s*\[\s*"worker"\s*\]/.test(b));
    expect(workerBlock).toBeDefined();

    const policy = /policy\s*=\s*"([^"]*)"/.exec(workerBlock as string)?.[1];
    expect(FLY_RESTART_POLICIES).toContain(policy);   // would have caught "no"
    expect(policy).toBe('on-failure');                // and pins the one this design needs
  });

  // ⭐ THE ONE A REGEX ALONE CANNOT ANSWER, which is why it is written as a position test.
  // In TOML a bare `key = value` belongs to the LAST table header above it. `kill_signal` and
  // `kill_timeout` sat below `[http_service]`, so they were `http_service.*` — not app settings at
  // all, and the worker's advertised 120s graceful drain had NEVER been in effect. Nothing was red;
  // a substring search for "kill_timeout" passes either way. The decidable property is POSITION:
  // an app-level key must appear before the FIRST table header in the file.
  for (const file of ['fly.toml', 'fly.worker.toml']) {
    test(`${file}: kill_signal/kill_timeout are app-level, i.e. above the first [table]`, async () => {
      const lines = (await read(file)).split('\n');
      const firstTable = lines.findIndex((l) => /^\s*\[/.test(l));
      expect(firstTable).toBeGreaterThan(-1); // CANNOT RUN on a file with no tables

      for (const key of ['kill_signal', 'kill_timeout']) {
        const at = lines.findIndex((l) => new RegExp(`^\\s*${key}\\s*=`).test(l));
        expect(at).toBeGreaterThan(-1);        // present at all
        expect(at).toBeLessThan(firstTable);   // and NOT swallowed by a table
      }

      // ⚠ AND THE VALUES, not only the position (review r2 Medium 3). Pinning where the keys live
      // left `SIGTERM -> SIGKILL` free to pass the suite AND `fly config validate` — removing the
      // graceful drain entirely while the test that exists for the drain stayed green. A signal the
      // worker does not trap is not a drain; it is a kill with extra steps.
      const whole = lines.join('\n');
      expect(/^\s*kill_signal\s*=\s*"SIGTERM"/m.test(whole)).toBe(true);
      expect(/^\s*kill_timeout\s*=\s*"120s"/m.test(whole)).toBe(true);
    });
  }

  // backlog #141 — the armed trap. The live web machine has said 0 since 2026-09-18; if this file
  // says 1, the next deploy silently reverts it and ~$5/mo comes back with no symptom.
  test('fly.toml lets the web machine actually suspend (min_machines_running = 0)', async () => {
    const http = tableBody(await read('fly.toml'), '[http_service]');
    expect(http).toBeDefined();   // CANNOT RUN if the web service is gone — fail, don't pass
    expect(/min_machines_running\s*=\s*0/.test(http as string)).toBe(true);
  });

  // ⭐ Break this catches putting the worker's service back into the PUBLIC app. Fly's docs: "Fly
  // Proxy doesn't know about process groups; it load-balances requests among all Machines with a
  // service configured on the requested port." youtube-playlist-summaries has public IPs, so any
  // service there is internet-reachable and any stranger could autostart the worker — which cannot
  // be defended in code, because the proxy boots the machine before our process sees the request.
  test('fly.toml declares NO worker service — the doorbell lives in the app with no public IP', async () => {
    const toml = await read('fly.toml');
    expect(hasTable(toml, '[[services]]')).toBe(false);   // a comment ABOUT it is fine; a table is not
    const httpService = tableBody(toml, '[http_service]') ?? '';
    expect(/processes\s*=\s*\[\s*"web"\s*\]/.test(httpService)).toBe(true); // web only
  });
});
