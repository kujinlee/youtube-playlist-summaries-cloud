import { makeWorkerWake } from '@/lib/job-queue/worker-wake';

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
