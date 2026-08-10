import { runOnce } from '@/lib/job-queue/worker-runner';
import type { JobHandler } from '@/lib/job-queue/worker-runner';
import type { JobQueue, JobStatus, LeasedJob } from '@/lib/storage/job-queue';

/**
 * CONTRACT TEST — the runtime premises the blob-addressing schema is designed on.
 *
 * WHY THIS FILE EXISTS, and it is worth the paragraph.
 *
 * ⚠ RE-POINTED BY ADR-0007 — THE FENCE THIS FILE WAS WRITTEN UNDER NO LONGER EXISTS, AND THESE TESTS
 * OUTLIVE IT. It used to open with §12b's caller obligation:
 *
 *     A worker MUST hold its reservation token for the life of the job.
 *     A worker that cannot present it MUST abandon rather than record.
 *
 * and with "`record_artifact` completes a generation ONLY for `reserved_by = p_token` — no fallback,
 * no recovery path." **There is no `reserved_by`, no token and no fence.** ADR-0007 deleted the
 * reservation protocol outright — six consecutive review rounds produced a Blocking or High in that
 * one seam, four of them introduced by the previous round's own fix, because the fence had to be
 * permissive (so a reclaimed writer could record work it had already paid for) and strict (so a
 * stranger could not complete a generation) at the same time. Writers now simply do not contend:
 * `record_artifact` INSERTs a new generation and appends its artifact, and `on conflict do nothing`
 * plus a `completed_by_another` outcome is what keeps a second writer safe. `docs/adr/0007` retires
 * §12b explicitly and says this file stays but is re-purposed — *"it now documents job-queue
 * behaviour rather than propping up a schema premise."* This header is that re-purposing (found
 * un-done by the 2026-08-10 implementation review, M4).
 *
 * SO WHAT THE THREE PREMISES BELOW ARE NOW. They are job-queue properties, and they are worth pinning
 * on their own account — a worker that keeps working after losing its lease is a second worker on the
 * same paid job, which costs money whether or not any SQL predicate reads a token. They are no longer
 * the thing that makes a schema fence safe, because there is no fence to make safe. **If one of them
 * fails, that is a real regression in `worker-runner`** — fix the runner, not the test — but it no
 * longer means "the schema's fence must be reconsidered", which is what this header used to say and
 * which would now send a reader looking for something that was deleted.
 *
 * Rounds 7 and 9 each built an elaborate SQL fallback for a caller state that the runtime already
 * prevents, and round 10 measured both fallbacks being usable by a stranger — kept here because it is
 * the reason this file exists at all, and it survives the fence.
 *
 * The structural lesson (round 11): the validation stack was ASYMMETRIC. The schema had 122
 * assertions and 57 mutations; the runtime premises underneath it had nothing at all — one of them
 * ("worker_id is stable config") was simply false, and no gate anywhere could see it. A rule
 * written in prose in a design doc is a rule that depends on remembering.
 *
 * So these are not tests of `worker-runner`'s features — `worker-runner-runtime.test.ts` covers
 * those. They pin the properties that decide WHETHER A SECOND WORKER CAN BE RUNNING A PAID JOB, and
 * they are co-located with the code that provides them so that a future refactor (auto-reconnect,
 * background retry, resuming a job after a restart) fails HERE rather than quietly re-introducing
 * one. That was the schema's core assumption while a fence existed; with the fence gone it is a
 * spend property of the job queue, which is why the file survives the thing it was written for.
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

describe('blob-addressing — the job-queue properties that bound a paid job to ONE worker', () => {
  /**
   * PREMISE 1 — a worker that loses its lease STOPS.
   *
   * This used to be "what makes `no recovery path` safe". With the fence gone it is simpler and no
   * less valuable: a worker that keeps running after losing its lease comes back holding paid Gemini
   * bytes for a slot another worker now owns — two paid calls for one job. ADR-0007 removed the SQL
   * that cared about WHO records; nothing removed the cost of computing the same thing twice.
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
   * The credential this protects is now the JOB QUEUE's, not the artifact schema's: `complete_job` /
   * `fail_job` filter on `(id, locked_by, lease_token, status='active')`
   * (`supabase/migrations/0008_jobs_queue.sql`). If the runner ever RE-READ a token — from the jobs
   * row, from a cache, from anywhere — that credential becomes recoverable by whoever can perform the
   * read, which is exactly the defect round 10 measured in the deleted `(worker_id, job_id)` pair.
   * The lesson outlived the fence it was learned on. Asserting the terminal writes carry the ORIGINAL
   * claim's token keeps the property visible.
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
   * "Abandon rather than record" is only meaningful if a lost job is not silently picked back up
   * inside the same run. A future "auto-reconnect" would put a second paid call on one job without
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
