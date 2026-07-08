import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
import { runWorkerLoop, sleep } from '@/worker/main';
import type { JobHandler } from '@/lib/job-queue/worker-runner';
jest.setTimeout(20_000);

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
  const enq = await userQ.enqueue(key(pl, vid), { hi: 1 });

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
