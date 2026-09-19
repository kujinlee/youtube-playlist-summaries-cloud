import { makeWorkerWake, workerWakeFromEnv, WORKER_WAKE_URL_ENV } from '@/lib/job-queue/worker-wake';

// Backlog #142. The worker machine is STOPPED when nobody is using the site. Fly Proxy starts a
// stopped machine when a request is routed to it — but only via Flycast, because `.internal` does
// not go through the proxy at all ("Machines can't be automatically stopped or started by Fly
// Proxy"). So enqueueing a job pokes the worker's Flycast address to wake it.
//
// ⭐ THE POKE IS AN OPTIMISATION, NOT A CORRECTNESS REQUIREMENT, and every test here exists to keep
// it that way. The job is durably in Postgres before the poke is sent, so a poke that fails costs
// LATENCY — the job waits for the next wake — and never costs work. That is what makes it safe to
// fire at a machine that may be stopped, mid-boot, or misconfigured.

describe('makeWorkerWake', () => {
  // Break this catches: making the wake mandatory. Local dev, every test, and any deploy without
  // Flycast configured have no URL — and must be completely unaffected, not merely tolerant.
  test('is a no-op when no URL is configured — it must not reach the network at all', async () => {
    const fetchImpl = jest.fn();
    await makeWorkerWake(undefined, { fetchImpl: fetchImpl as unknown as typeof fetch })();
    await makeWorkerWake('', { fetchImpl: fetchImpl as unknown as typeof fetch })();
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  test('POSTs to the configured URL when one is set', async () => {
    const fetchImpl = jest.fn(async () => new Response(null, { status: 200 }));
    await makeWorkerWake('http://w.flycast/wake', { fetchImpl: fetchImpl as unknown as typeof fetch })();

    expect(fetchImpl).toHaveBeenCalledTimes(1);
    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('http://w.flycast/wake');
    expect(init.method).toBe('POST');
  });

  // ⭐ Break this catches: letting the wake reject. It is called on the enqueue path, so a throw
  // here would fail a request whose job is ALREADY COMMITTED — turning a latency optimisation into
  // a user-visible error on work that will in fact get done.
  test('resolves even when the request rejects — a failed wake must never fail an enqueue', async () => {
    const fetchImpl = jest.fn(async () => { throw new Error('ECONNREFUSED: machine still booting'); });
    await expect(
      makeWorkerWake('http://w.flycast/wake', { fetchImpl: fetchImpl as unknown as typeof fetch })(),
    ).resolves.toBeUndefined();
  });

  test('resolves on a non-2xx response too', async () => {
    const fetchImpl = jest.fn(async () => new Response('nope', { status: 503 }));
    await expect(
      makeWorkerWake('http://w.flycast/wake', { fetchImpl: fetchImpl as unknown as typeof fetch })(),
    ).resolves.toBeUndefined();
  });

  // Break this catches: an unbounded await. A stopped machine that is slow to boot would otherwise
  // hold the user's enqueue request open for as long as Fly takes to start it.
  test('gives up after its timeout rather than holding the enqueue open', async () => {
    const fetchImpl = jest.fn((_u: string, init: RequestInit) => new Promise<Response>((_res, rej) => {
      init.signal?.addEventListener('abort', () => rej(new Error('aborted')), { once: true });
    }));
    const started = Date.now();
    await expect(
      makeWorkerWake('http://w.flycast/wake', {
        timeoutMs: 40, fetchImpl: fetchImpl as unknown as typeof fetch,
      })(),
    ).resolves.toBeUndefined();
    expect(Date.now() - started).toBeLessThan(2_000); // did not wait on a hung boot
  });

  // Break this catches: passing no signal, which would make the timeout above decorative — the
  // promise would resolve while the request kept running.
  test('passes an abort signal so the underlying request is actually cancelled', async () => {
    let seen: AbortSignal | null | undefined;
    const fetchImpl = jest.fn(async (_u: string, init: RequestInit) => {
      seen = init.signal;
      return new Response(null, { status: 200 });
    });
    await makeWorkerWake('http://w.flycast/wake', { fetchImpl: fetchImpl as unknown as typeof fetch })();
    expect(seen).toBeInstanceOf(AbortSignal);
  });
});

// --- the other half of the wake path: something for Fly Proxy to route AT ---
//
// ⭐ The listener does no work. Its entire job is to EXIST, so the worker process group has a
// service the proxy can route to — which is what makes the machine autostart. The request that
// wakes the machine is discarded; the poll loop that boots alongside it is what picks up the job.
// A listener that tried to do the work would be a second, racier path to the same queue.
describe('startWakeListener', () => {
  test('answers a wake request, and closes so the process can still exit', async () => {
    const { startWakeListener } = await import('@/worker/main');
    const server = await startWakeListener(0); // port 0 = let the OS pick, so tests never collide

    const res = await fetch(`http://127.0.0.1:${server.port}/wake`, { method: 'POST' });
    expect(res.status).toBe(200);

    // Break this catches: a listener that keeps the event loop alive. The worker's whole exit
    // strategy is `process exits 0 -> Fly machine returns to stopped`; an open handle defeats it
    // and the machine bills forever while looking idle.
    await expect(server.close()).resolves.toBeUndefined();
  }, 15_000);

  test('answers any path and method — it is a doorbell, not an API', async () => {
    const { startWakeListener } = await import('@/worker/main');
    const server = await startWakeListener(0);
    try {
      expect((await fetch(`http://127.0.0.1:${server.port}/`)).status).toBe(200);
      expect((await fetch(`http://127.0.0.1:${server.port}/anything`, { method: 'PUT' })).status).toBe(200);
    } finally {
      await server.close();
    }
  }, 15_000);
});

// --- the enqueue side: the ordering that makes the poke safe ---
describe('SupabaseEnqueuer wakes the worker', () => {
  const rpcOk = () => ({ rpc: jest.fn(async () => ({ data: [{ job_id: 'j1', status: 'queued', joined: false }], error: null })) });
  const key = { playlistId: 'p', videoId: 'v', sectionId: -1, kind: 'summary' as const, version: '3.3' };
  const ctx = { ownerId: 'o', enqueueIp: null };

  test('pokes the worker after a successful enqueue', async () => {
    const { SupabaseEnqueuer } = await import('@/lib/job-queue/enqueuer');
    const wake = jest.fn(async () => {});
    const client = rpcOk();
    const r = await new SupabaseEnqueuer(client as never, wake).enqueue(ctx, key, {} as never);

    expect(r.jobId).toBe('j1');
    expect(wake).toHaveBeenCalledTimes(1);
  });

  // ⭐ THE ORDERING IS THE SAFETY ARGUMENT. The job must be durable BEFORE anyone is told to come
  // and do it; otherwise a wake could race a row that does not exist yet.
  test('pokes only AFTER the job row is committed, never before', async () => {
    const { SupabaseEnqueuer } = await import('@/lib/job-queue/enqueuer');
    const order: string[] = [];
    const client = { rpc: jest.fn(async () => { order.push('enqueue'); return { data: [{ job_id: 'j1', status: 'queued', joined: false }], error: null }; }) };
    const wake = jest.fn(async () => { order.push('wake'); });

    await new SupabaseEnqueuer(client as never, wake).enqueue(ctx, key, {} as never);
    expect(order).toEqual(['enqueue', 'wake']);
  });

  // Break this catches: a failing enqueue that still pokes. Nothing was queued, so waking a machine
  // to find an empty queue burns a boot for nothing.
  test('does not poke when the enqueue itself failed', async () => {
    const { SupabaseEnqueuer } = await import('@/lib/job-queue/enqueuer');
    const wake = jest.fn(async () => {});
    const client = { rpc: jest.fn(async () => ({ data: null, error: { message: 'boom', code: 'XX000' } })) };

    await expect(new SupabaseEnqueuer(client as never, wake).enqueue(ctx, key, {} as never)).rejects.toBeDefined();
    expect(wake).not.toHaveBeenCalled();
  });
});

// --- coalescing: one poke starts a machine; the rest are waste ---
//
// ⭐ Review round 1 measured the shape this exists for: `enqueuePlaylist` loops sequentially over up
// to 50 videos (MAX_VIDEOS_PER_ENQUEUE), and the original code awaited a 1500ms-bounded POST on each
// one — up to ~75s added to a single user-facing request. Not awaiting removed the LATENCY; these
// cases remove the REQUESTS. The job-status poll is the second caller, firing every ~2s while
// anything is queued, so without suppression "wake the worker" would mean a poke every 2s forever.
describe('makeWorkerWake coalesces', () => {
  const clock = (start = 1_000) => { let t = start; return { now: () => t, advance: (ms: number) => { t += ms; } }; };

  // ⭐ ISOLATES THE IN-FLIGHT JOIN, and it has to work this hard for a reason worth writing down.
  //
  // The obvious version of this test — fire two calls back to back and assert one request — PASSES
  // WITH THE IN-FLIGHT CHECK DELETED. Measured: that mutation survived a 38-case run. `lastSentAt`
  // is set BEFORE the request begins and the default window (10s) outlasts the request timeout
  // (1.5s), so while a poke is on the wire the SUPPRESSION check always returns first. The naive
  // test proves suppression and merely takes credit for coalescing.
  //
  // So the window is made shorter than the request and then advanced past: suppression has expired,
  // the first request is still open, and only the in-flight join can prevent a second one. That is
  // also the configuration in which the branch genuinely earns its place — tune `suppressMs` below
  // the request duration and without it a slow Flycast would get one request per call again.
  test('joins an in-flight poke even after the suppression window has expired', async () => {
    const c = clock();
    let release: () => void = () => {};
    const gate = new Promise<Response>((res) => { release = () => res(new Response(null, { status: 200 })); });
    const fetchImpl = jest.fn(() => gate);
    const wake = makeWorkerWake('http://w.flycast/wake', {
      fetchImpl: fetchImpl as unknown as typeof fetch, suppressMs: 10, now: c.now,
    });

    const a = wake();
    c.advance(11);      // suppression is no longer protecting us...
    const b = wake();   // ...and the first request has NOT come back yet
    release();
    await Promise.all([a, b]);

    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });

  // ⭐ THE 50-VIDEO PLAYLIST, which is the case the finding was about.
  test('50 sequential calls — the playlist fan-out — send exactly ONE request', async () => {
    const fetchImpl = jest.fn(async () => new Response(null, { status: 200 }));
    const wake = makeWorkerWake('http://w.flycast/wake', { fetchImpl: fetchImpl as unknown as typeof fetch });

    for (let i = 0; i < 50; i++) await wake();

    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });

  // Break this catches: dropping the suppression window, which would restore a poke per poll.
  test('a call after the first completes but inside the window is dropped', async () => {
    const c = clock();
    const fetchImpl = jest.fn(async () => new Response(null, { status: 200 }));
    const wake = makeWorkerWake('http://w.flycast/wake', {
      fetchImpl: fetchImpl as unknown as typeof fetch, suppressMs: 10_000, now: c.now,
    });

    await wake();
    c.advance(9_999);
    await wake();

    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });

  // ⚠ And the other direction, which is the one that matters for correctness: suppression must
  // EXPIRE. A window that never reopens would mean the worker can be woken once per process and
  // never again — every later job stranded, silently, with the wake looking configured and healthy.
  test('once the window has passed, it pokes again', async () => {
    const c = clock();
    const fetchImpl = jest.fn(async () => new Response(null, { status: 200 }));
    const wake = makeWorkerWake('http://w.flycast/wake', {
      fetchImpl: fetchImpl as unknown as typeof fetch, suppressMs: 10_000, now: c.now,
    });

    await wake();
    c.advance(10_001);
    await wake();

    expect(fetchImpl).toHaveBeenCalledTimes(2);
  });

  // A failed poke must not poison the window either — but it must still count as "sent", because the
  // machine may well be booting; that is the most likely reason the request failed.
  test('a rejected poke still resolves and still opens a suppression window', async () => {
    const c = clock();
    const fetchImpl = jest.fn(async () => { throw new Error('ECONNREFUSED: still booting'); });
    const wake = makeWorkerWake('http://w.flycast/wake', {
      fetchImpl: fetchImpl as unknown as typeof fetch, suppressMs: 10_000, now: c.now,
    });

    await expect(wake()).resolves.toBeUndefined();
    c.advance(5_000);
    await wake();

    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });
});

// --- the shared instance, which is what makes suppression reach across requests ---
describe('workerWakeFromEnv', () => {
  const ORIGINAL = process.env[WORKER_WAKE_URL_ENV];
  afterEach(() => {
    if (ORIGINAL === undefined) delete process.env[WORKER_WAKE_URL_ENV];
    else process.env[WORKER_WAKE_URL_ENV] = ORIGINAL;
  });

  // ⭐ Break this catches building a fresh wake per call. Both call sites construct per request — a
  // route handler makes a new SupabaseEnqueuer, and the status GET calls this directly — so a new
  // instance each time would carry an empty suppression window every time and coalesce NOTHING.
  // The sharing is not an optimisation; it is the mechanism.
  test('returns the SAME instance for the same URL, so the window is shared across requests', () => {
    process.env[WORKER_WAKE_URL_ENV] = 'http://w.flycast/wake';
    expect(workerWakeFromEnv()).toBe(workerWakeFromEnv());
  });

  // ...and the cache must not outlive the value it was keyed on. This is also why no test-only reset
  // hook is needed: changing the env var is enough to invalidate it.
  test('returns a NEW instance when the URL changes', () => {
    process.env[WORKER_WAKE_URL_ENV] = 'http://a.flycast/wake';
    const first = workerWakeFromEnv();
    process.env[WORKER_WAKE_URL_ENV] = 'http://b.flycast/wake';
    expect(workerWakeFromEnv()).not.toBe(first);
  });

  test('unset URL yields a wake that reaches no network', async () => {
    delete process.env[WORKER_WAKE_URL_ENV];
    const fetchImpl = jest.fn();
    await workerWakeFromEnv({ fetchImpl: fetchImpl as unknown as typeof fetch })();
    expect(fetchImpl).not.toHaveBeenCalled();
  });
});
