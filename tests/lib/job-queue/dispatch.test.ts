import { makeJobHandler } from '@/lib/job-queue/dispatch';
import { NonRetryableError } from '@/lib/job-queue/errors';

const ctx = { isCancelled: async () => false, signal: new AbortController().signal, setPhase: async () => {} };
const mkJob = (kind: string) => ({ id: 'j', ownerId: 'o', playlistId: 'p', videoId: 'v', sectionId: -1, kind, version: 'x', payload: {}, attempts: 0, leaseToken: 't' });

it('routes by job.kind', async () => {
  const summary = jest.fn(async () => 'S');
  const dig = jest.fn(async () => 'D');
  const h = makeJobHandler({ summary, dig });
  expect(await h(mkJob('summary') as any, ctx as any)).toBe('S');
  expect(await h(mkJob('dig') as any, ctx as any)).toBe('D');
  expect(summary).toHaveBeenCalledTimes(1);
  expect(dig).toHaveBeenCalledTimes(1);
});

it('throws NonRetryableError for an unknown kind', async () => {
  const h = makeJobHandler({ summary: jest.fn(), dig: jest.fn() });
  // Assert the CLASS, not just the message: the dead-letter-vs-retry distinction depends on it
  // being NonRetryableError (worker-runner.ts classifies retryable = !(e instanceof NonRetryableError)).
  // A plain Error with the same message would silently become a retry loop.
  const err = await h(mkJob('bogus') as any, ctx as any).catch((e) => e);
  expect(err).toBeInstanceOf(NonRetryableError);
  expect(err.message).toMatch(/no handler for kind/);
});
