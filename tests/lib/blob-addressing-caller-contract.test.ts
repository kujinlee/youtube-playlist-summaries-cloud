import { runOnce } from '@/lib/job-queue/worker-runner';
import type { JobHandler } from '@/lib/job-queue/worker-runner';
import type { JobQueue, JobStatus, LeasedJob } from '@/lib/storage/job-queue';

/**
 * CONTRACT TEST — the runtime premises the blob-addressing schema is designed on.
 *
 * WHY THIS FILE EXISTS, and it is worth the paragraph.
 *
 * `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md` §12b states one rule:
 *
 *     A worker MUST hold its reservation token for the life of the job.
 *     A worker that cannot present it MUST abandon rather than record.
 *
 * `record_artifact` completes a generation ONLY for `reserved_by = p_token` — no fallback, no
 * recovery path. That is safe only because of how THIS code behaves, and rounds 7 and 9 each built
 * an elaborate SQL fallback for a caller state that the runtime already prevents. Round 10 then
 * measured both fallbacks being usable by a stranger.
 *
 * The structural lesson (round 11): the validation stack was ASYMMETRIC. The schema had 122
 * assertions and 57 mutations; the runtime premises underneath it had nothing at all — one of them
 * ("worker_id is stable config") was simply false, and no gate anywhere could see it. A rule
 * written in prose in a design doc is a rule that depends on remembering.
 *
 * So these are not tests of `worker-runner`'s features — `worker-runner-runtime.test.ts` covers
 * those. They are tests of the exact properties the SQL fence RELIES on, co-located with the code
 * that provides them, so that a future refactor (auto-reconnect, background retry, resuming a job
 * after a restart) fails HERE rather than silently invalidating the schema's core assumption.
 *
 * If one of these ever fails, do not "fix" the test: the schema's fence must be reconsidered,
 * because its premise has changed.
 *
 * MUTATION-CHECKED, because a contract test that cannot fail is worse than none. Removing the abort
 * in `worker-runner.ts` (`.then(r => { if (!r.ok) leaseLost.abort(); })`) turns PREMISE 1 red and
 * leaves 2 and 3 green — measured. So premise 1 is load-bearing; premise 2 pins a property no
 * current code violates; and premise 3 is the weakest of the three — it catches an ADDED re-claim
 * but would not catch resumption implemented some other way. Stated rather than implied, because
 * "3 passing tests" reads as three guarantees and only one of them is currently proven.
 *
 * ⚠ DELIBERATELY IN `tests/lib/` RATHER THAN `tests/integration/`, even though its sibling
 * `worker-runner-runtime.test.ts` lives there. It uses only in-memory fakes, and `docs/dev-process.md`
 * records that `test:integration` is NOT yet wired into CI — a contract test that does not run on
 * every push is the same "rule that depends on remembering" this file exists to replace.
 */

function makeJob(overrides: Partial<LeasedJob> = {}): LeasedJob {
  return {
    id: 'job-1', ownerId: 'w1', playlistId: 'pl-1', videoId: 'vid-1', sectionId: -1,
    kind: 'summary', version: '3.3', payload: { hi: 1 }, attempts: 1, leaseToken: 'tok-1',
    ...overrides,
  } as LeasedJob;
}

function makeQueue(job: LeasedJob, leaseLost = false): jest.Mocked<JobQueue> {
  return {
    enqueue: jest.fn(),
    getStatus: jest.fn(async () => ({ id: job.id, status: 'active' as JobStatus, cancelRequested: false, result: null, error: null })),
    requestCancel: jest.fn(),
    claim: jest.fn(async () => job),
    // ⚠ THE FAKE MODELS THE DB'S FENCING. `complete_job`/`fail_job` filter on
    // `id, locked_by, lease_token, status='active'` (supabase/migrations/0008_jobs_queue.sql), and
    // `sweep_expired_leases` nulls all three — so a terminal write AFTER a lost lease returns
    // ok:false in production. A fake that always answered ok:true hid exactly the property these
    // tests exist to pin, and did so while showing green. Round 12 caught it.
    heartbeat: jest.fn(async () => ({ ok: true })),
    complete: jest.fn(async () => ({ ok: !leaseLost })),
    fail: jest.fn(async () => ({ ok: !leaseLost, status: 'failed' as JobStatus })),
    sweepExpired: jest.fn(async () => 0),
    setProgressPhase: jest.fn(async () => ({ ok: true })),
  } as unknown as jest.Mocked<JobQueue>;
}

afterEach(() => {
  jest.useRealTimers();
  jest.restoreAllMocks();
});

describe('blob-addressing §12b — the caller contract the SQL fence depends on', () => {
  /**
   * PREMISE 1 — a worker that loses its lease STOPS.
   *
   * This is what makes "no recovery path" safe. If a worker could keep running after losing its
   * lease, it would come back holding paid Gemini bytes for a slot another worker now owns, which
   * is precisely the scenario rounds 7 and 9 built (broken) fallbacks for.
   */
  it('signals abort on lease loss AND cannot land a terminal success afterwards', async () => {
    jest.useFakeTimers();
    const job = makeJob();
    const queue = makeQueue(job, /* leaseLost */ true);
    queue.heartbeat.mockResolvedValue({ ok: false } as never);

    let observedAbort = false;
    // ⚠ THIS HANDLER DELIBERATELY IGNORES THE ABORT and returns paid bytes anyway — the worst
    // caller §12b has to survive. Round 12 found the first version of this test asserting only that
    // the SIGNAL arrived, which is necessary and nowhere near sufficient: `runOnce` proceeds from
    // `await handler(...)` straight to `queue.complete(...)`, so "abort delivered" and "work
    // abandoned" are different claims and only the second is what §12b needs.
    const handler: JobHandler = async (_job, ctx) => {
      await new Promise<void>((resolve) => {
        ctx.signal.addEventListener('abort', () => { observedAbort = true; resolve(); });
        setTimeout(resolve, 10_000); // if the signal never fires, this resolves and the test fails
      });
      return { paidBytes: 'SHA_REAL' };
    };

    const p = runOnce(queue, handler, { workerId: 'w1', leaseSeconds: 2 });
    await jest.advanceTimersByTimeAsync(10_000);
    const outcome = await p;

    expect(observedAbort).toBe(true);
    // The load-bearing half: the run does NOT report success for work done after the lease was lost.
    expect(outcome).toBe('lost');
  });

  /**
   * PREMISE 2 — the token is passed through from the claim and never re-derived.
   *
   * The fence is `reserved_by = p_token`. If the runner ever RE-READ a token — from the jobs row,
   * from a cache, from anywhere — then the credential would be recoverable by whoever can perform
   * that read, which is exactly the defect round 10 measured in the `(worker_id, job_id)` pair.
   * Asserting the terminal writes carry the ORIGINAL claim's token keeps that property visible.
   */
  it('carries the claim-time lease token into every terminal write, never a re-derived one', async () => {
    const job = makeJob({ leaseToken: 'tok-original' });
    const queue = makeQueue(job);

    await runOnce(queue, (async () => ({ ok: 1 })) as JobHandler, { workerId: 'w1' });

    expect(queue.complete).toHaveBeenCalledTimes(1);
    expect(queue.complete).toHaveBeenCalledWith(job.id, 'w1', 'tok-original', { ok: 1 });
    // Nothing in the run may look the job up to recover a credential.
    expect(queue.claim).toHaveBeenCalledTimes(1);
  });

  /**
   * PREMISE 3 — one job, one claim, no resumption.
   *
   * §12b's "abandon rather than record" is only meaningful if a lost job is not silently picked
   * back up inside the same run. A future "auto-reconnect" would break the fence's premise without
   * touching a line of SQL; this is the test that would catch it.
   */
  it('does not re-claim or resume a job after losing its lease', async () => {
    jest.useFakeTimers();
    const job = makeJob();
    const queue = makeQueue(job);
    queue.heartbeat.mockResolvedValue({ ok: false } as never);

    const handler: JobHandler = async (_job, ctx) => {
      await new Promise<void>((resolve) => {
        ctx.signal.addEventListener('abort', () => resolve());
        setTimeout(resolve, 10_000);
      });
      return { done: true };
    };

    const p = runOnce(queue, handler, { workerId: 'w1', leaseSeconds: 2 });
    await jest.advanceTimersByTimeAsync(10_000);
    await p;

    expect(queue.claim).toHaveBeenCalledTimes(1);
  });
});
