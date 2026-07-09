import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs, ensureGuardrailHeadroom } from './helpers/clients';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
import { SupabaseEnqueuer } from '@/lib/job-queue/enqueuer';
import { runWorkerLoop, sleep } from '@/worker/main';
import type { JobHandler } from '@/lib/job-queue/worker-runner';
import type { JobQueue } from '@/lib/storage/job-queue';
jest.setTimeout(20_000);
beforeAll(() => ensureGuardrailHeadroom(adminClient()));

async function seedPlaylist(client: any, ownerId: string): Promise<string> {
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: `k-${randomUUID()}`, playlist_url: `https://x/${randomUUID()}` })
    .select('id').single();
  if (error) throw error;
  return data.id as string;
}

const key = (playlistId: string, videoId: string) =>
  ({ playlistId, videoId, sectionId: -1, kind: 'summary' as const, version: '3.3' });

test('runWorkerLoop processes exactly one queued job to completed, then exits on shutdown', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const userQ = new SupabaseJobQueue(client);
  const workerQ = new SupabaseJobQueue(adminClient());
  const pl = await seedPlaylist(client, userId);
  const vid = randomUUID();
  // T13: SupabaseJobQueue.enqueue is dropped — enqueue via the service-role SupabaseEnqueuer.
  const enqueuer = new SupabaseEnqueuer(adminClient());
  const enq = await enqueuer.enqueue({ ownerId: userId, enqueueIp: null }, key(pl, vid), { hi: 1, durationSeconds: 100 } as never);

  const ac = new AbortController();
  const stubHandler: JobHandler = async (job) => {
    // The shared local Supabase stack can carry leftover 'queued' jobs from earlier
    // integration test files (e.g. job-queue-producer.test.ts intentionally leaves some
    // unclaimed). runWorkerLoop has no videoFilter (by design — the real worker drains
    // any job), so the loop may process other jobs first; only request shutdown once
    // we've handled the job this test actually cares about.
    if (job.id === enq.jobId) ac.abort();
    return { ok: true };
  };

  await runWorkerLoop({
    queue: workerQ,
    handler: stubHandler,
    shutdownSignal: ac.signal,
    workerId: 'worker-main-test',
  });

  const st = await userQ.getStatus(enq.jobId);
  expect(st?.status).toBe('completed');
});

// --- loop resilience: a throwing sweepExpired/claim (outside runOnce's try/catch) must NOT
//     kill the long-lived worker. Deterministic stub queue via DI; abort after recovery. ---
test('runWorkerLoop survives a throwing claim and continues until shutdown', async () => {
  const ac = new AbortController();
  let claimCalls = 0;
  let sweepCalls = 0;
  const stubQueue = {
    sweepExpired: async () => { sweepCalls++; return 0; },
    claim: async () => {
      claimCalls++;
      if (claimCalls === 1) throw new Error('transient queue error'); // first iteration blows up
      ac.abort(); // recovered — request clean shutdown so the loop exits
      return null; // idle
    },
  } as unknown as JobQueue;
  const stubHandler: JobHandler = async () => ({ ok: true });

  // Must NOT reject even though claim threw on the first iteration.
  await expect(
    runWorkerLoop({ queue: stubQueue, handler: stubHandler, shutdownSignal: ac.signal, workerId: 'resilience-test' }),
  ).resolves.toBeUndefined();

  expect(claimCalls).toBeGreaterThanOrEqual(2); // recovered and ran at least one more iteration
  expect(sweepCalls).toBeGreaterThanOrEqual(2);
});

// --- abort-aware idle sleep (the idle-backoff path runWorkerLoop uses between polls) ---

test('sleep resolves PROMPTLY when the signal aborts mid-wait (SIGTERM during idle backoff)', async () => {
  const ac = new AbortController();
  const start = Date.now();
  const p = sleep(10_000, ac.signal); // would block ~10s without the abort
  setTimeout(() => ac.abort(), 20);
  await p;
  expect(Date.now() - start).toBeLessThan(1_000); // did not wait out the 10s
});

test('sleep resolves IMMEDIATELY when the signal is already aborted on entry', async () => {
  const ac = new AbortController();
  ac.abort();
  const start = Date.now();
  await sleep(10_000, ac.signal);
  expect(Date.now() - start).toBeLessThan(200);
});

test('sleep removes its abort listener on the normal timeout path (no per-poll leak)', async () => {
  const ac = new AbortController();
  const removeSpy = jest.spyOn(ac.signal, 'removeEventListener');
  await sleep(20, ac.signal); // let it time out normally
  // The process-lifetime signal must not accumulate one dead 'abort' listener per idle poll.
  expect(removeSpy).toHaveBeenCalledWith('abort', expect.any(Function));
  removeSpy.mockRestore();
});
