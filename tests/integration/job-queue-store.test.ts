// tests/integration/job-queue-store.test.ts
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
jest.setTimeout(20_000);

const key = (videoId: string) => ({ videoId, sectionId: -1, kind: 'summary' as const, version: '3.3' });

test('enqueue → claim(video) → complete round-trip through the store', async () => {
  const u = await newUser();
  const userQ = new SupabaseJobQueue((await signInAs(u.email, u.password)).client);
  const workerQ = new SupabaseJobQueue(adminClient());
  const vid = randomUUID();
  const enq = await userQ.enqueue(key(vid), { n: 1 });
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
  const userQ = new SupabaseJobQueue((await signInAs(u.email, u.password)).client);
  const workerQ = new SupabaseJobQueue(adminClient());
  const vid = randomUUID();
  const enq = await userQ.enqueue(key(vid), {});
  const leased = await workerQ.claim('w', 120, vid);
  const r = await workerQ.fail(leased!.id, 'w', leased!.leaseToken, 'boom', { retryable: false });
  expect(r.ok).toBe(true);
  expect(r.status).toBe('failed');
});
