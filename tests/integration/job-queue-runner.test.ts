import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
import { runOnce, echoHandler } from '@/lib/job-queue/worker-runner';
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

test('runOnce processes a queued job to completed with the echo stub', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const userQ = new SupabaseJobQueue(client);
  const workerQ = new SupabaseJobQueue(adminClient());
  const pl = await seedPlaylist(client, userId);
  const vid = randomUUID();
  const enq = await userQ.enqueue(key(pl, vid), { hi: 1 });

  const outcome = await runOnce(workerQ, echoHandler, { workerId: 'w1', videoFilter: vid });
  expect(outcome).toBe('done');
  const st = await userQ.getStatus(enq.jobId);
  expect(st?.status).toBe('completed');
  expect(st?.result).toEqual({ echoed: { hi: 1 } });
});

test('runOnce returns idle when the scoped queue is empty', async () => {
  const workerQ = new SupabaseJobQueue(adminClient());
  const outcome = await runOnce(workerQ, echoHandler, { workerId: 'w-empty', videoFilter: randomUUID() });
  expect(outcome).toBe('idle');
});

test('a handler that observes cancellation ends the job cancelled', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const userQ = new SupabaseJobQueue(client);
  const workerQ = new SupabaseJobQueue(adminClient());
  const pl = await seedPlaylist(client, userId);
  const vid = randomUUID();
  const enq = await userQ.enqueue(key(pl, vid), {});

  const cancelDuringHandler: JobHandler = async (job, ctx) => {
    expect(job.id).toBe(enq.jobId);          // scoped claim guarantees we got our job
    await userQ.requestCancel(job.id);       // request cancel mid-run (job is 'active' now)
    if (await ctx.isCancelled()) throw new Error('cancelled by request');
    return {};
  };
  const outcome = await runOnce(workerQ, cancelDuringHandler, { workerId: 'w2', videoFilter: vid });
  expect(outcome).toBe('cancelled');
  expect((await userQ.getStatus(enq.jobId))?.status).toBe('cancelled');
});
