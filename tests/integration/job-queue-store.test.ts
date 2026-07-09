// tests/integration/job-queue-store.test.ts
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs, ensureGuardrailHeadroom } from './helpers/clients';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
import { SupabaseEnqueuer } from '@/lib/job-queue/enqueuer';
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

test('enqueue → claim(video) → complete round-trip through the store', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const userQ = new SupabaseJobQueue(client);
  const workerQ = new SupabaseJobQueue(adminClient());
  const pl = await seedPlaylist(client, userId);
  const vid = randomUUID();
  // T13: SupabaseJobQueue.enqueue is dropped — enqueue via the service-role SupabaseEnqueuer.
  const enqueuer = new SupabaseEnqueuer(adminClient());
  const enq = await enqueuer.enqueue({ ownerId: userId, enqueueIp: null }, key(pl, vid), { n: 1, durationSeconds: 100 } as never);
  expect(enq.joined).toBe(false);

  const leased = await workerQ.claim('w1', 120, vid);   // scoped claim
  expect(leased?.id).toBe(enq.jobId);
  expect(leased?.leaseToken).toBeTruthy();

  const done = await workerQ.complete(leased!.id, 'w1', leased!.leaseToken, { ok: true });
  expect(done.ok).toBe(true);
  expect((await userQ.getStatus(enq.jobId))?.status).toBe('completed');
});

test('claim returns null when the scoped queue is empty', async () => {
  const workerQ = new SupabaseJobQueue(adminClient());
  const leased = await workerQ.claim('w', 120, randomUUID()); // no job for this fresh video id
  expect(leased).toBeNull();
});

test('fail through the store reports the resulting status', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const userQ = new SupabaseJobQueue(client);
  const workerQ = new SupabaseJobQueue(adminClient());
  const pl = await seedPlaylist(client, userId);
  const vid = randomUUID();
  const enqueuer = new SupabaseEnqueuer(adminClient());
  const enq = await enqueuer.enqueue({ ownerId: userId, enqueueIp: null }, key(pl, vid), { durationSeconds: 100 } as never);
  const leased = await workerQ.claim('w', 120, vid);
  const r = await workerQ.fail(leased!.id, 'w', leased!.leaseToken, 'boom', { retryable: false });
  expect(r.ok).toBe(true);
  expect(r.status).toBe('failed');
});
