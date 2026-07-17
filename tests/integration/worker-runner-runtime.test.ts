import { runOnce, echoHandler } from '@/lib/job-queue/worker-runner';
import type { JobHandler } from '@/lib/job-queue/worker-runner';
import { NonRetryableError } from '@/lib/job-queue/errors';
import { GoogleGenerativeAIFetchError } from '@google/generative-ai';
import type { JobQueue, JobStatus, LeasedJob } from '@/lib/storage/job-queue';

// This suite tests runOnce's TIMER/SIGNAL/TEARDOWN control flow (heartbeat cadence, the
// composed abort signal, wall-clock bound, and the single-terminal-write guarantee) — it
// deliberately runs against a fully controllable in-memory JobQueue fake rather than the
// live Supabase stack, so that timing-sensitive assertions ((a) and (g)) are driven by
// Jest's fake timers and are fully deterministic (no real wall-clock waits, no network
// jitter). The DB-level fencing/RPC behavior itself is already covered by
// tests/integration/job-queue-worker.test.ts and job-queue-runner.test.ts.

function makeJob(overrides: Partial<LeasedJob> = {}): LeasedJob {
  return {
    id: 'job-1', ownerId: 'w1', playlistId: 'pl-1', videoId: 'vid-1', sectionId: -1,
    kind: 'summary', version: '3.3', payload: { hi: 1 }, attempts: 1, leaseToken: 'tok-1',
    ...overrides,
  };
}

function makeQueue(job: LeasedJob): jest.Mocked<JobQueue> {
  return {
    enqueue: jest.fn(),
    getStatus: jest.fn(async () => ({ id: job.id, status: 'active' as JobStatus, cancelRequested: false, result: null, error: null })),
    requestCancel: jest.fn(),
    claim: jest.fn(async () => job),
    heartbeat: jest.fn(async () => ({ ok: true })),
    complete: jest.fn(async () => ({ ok: true })),
    fail: jest.fn(async () => ({ ok: true, status: 'failed' as JobStatus })),
    sweepExpired: jest.fn(async () => 0),
    setProgressPhase: jest.fn(async () => ({ ok: true })),
  } as unknown as jest.Mocked<JobQueue>;
}

afterEach(() => {
  jest.useRealTimers();
  jest.restoreAllMocks();
});

test('(a) heartbeat extends a short lease so a slow handler still completes', async () => {
  jest.useFakeTimers();
  const job = makeJob();
  const queue = makeQueue(job);
  const handler: JobHandler = async () => {
    await new Promise((resolve) => setTimeout(resolve, 3000));
    return { done: true };
  };

  const resultP = runOnce(queue, handler, { workerId: 'w1', leaseSeconds: 2 });
  await jest.advanceTimersByTimeAsync(3000);
  const outcome = await resultP;

  expect(outcome).toBe('done');
  // interval = floor(2000/3) = 666ms; over a 3000ms window that ticks ~4 times.
  expect(queue.heartbeat.mock.calls.length).toBeGreaterThanOrEqual(3);
  expect(queue.complete).toHaveBeenCalledTimes(1);
  expect(queue.complete).toHaveBeenCalledWith(job.id, 'w1', job.leaseToken, { done: true });
});

test('(b) heartbeat interval is cleared once the job settles (throw path)', async () => {
  jest.useFakeTimers();
  const job = makeJob();
  const queue = makeQueue(job);
  const handler: JobHandler = async () => { throw new Error('boom'); };

  const outcome = await runOnce(queue, handler, { workerId: 'w1', leaseSeconds: 2 });
  expect(outcome).toBe('failed');

  const callsAtSettle = queue.heartbeat.mock.calls.length;
  await jest.advanceTimersByTimeAsync(5000); // well past the 666ms interval — should tick zero more times
  expect(queue.heartbeat.mock.calls.length).toBe(callsAtSettle);
});

test('(c) a NonRetryableError fails the job non-retryably', async () => {
  const job = makeJob();
  const queue = makeQueue(job);
  const handler: JobHandler = async () => { throw new NonRetryableError('bad input'); };

  const outcome = await runOnce(queue, handler, { workerId: 'w1' });

  expect(outcome).toBe('failed');
  expect(queue.fail).toHaveBeenCalledTimes(1);
  expect(queue.fail).toHaveBeenCalledWith(job.id, 'w1', job.leaseToken, 'bad input', { retryable: false, billableSucceeded: true, metered: false });
  expect(queue.complete).not.toHaveBeenCalled();
});

test('(d) ctx.setPhase writes progress_phase via setProgressPhase', async () => {
  const job = makeJob();
  const queue = makeQueue(job);
  const handler: JobHandler = async (_job, ctx) => {
    await ctx.setPhase('summarizing');
    return {};
  };

  const outcome = await runOnce(queue, handler, { workerId: 'w1' });

  expect(outcome).toBe('done');
  expect(queue.setProgressPhase).toHaveBeenCalledWith(job.id, 'w1', job.leaseToken, 'summarizing');
});

test('(e) a rejecting heartbeat is treated as lease loss — no unhandled rejection', async () => {
  jest.useFakeTimers();
  const unhandled: unknown[] = [];
  const onUnhandled = (reason: unknown) => unhandled.push(reason);
  process.on('unhandledRejection', onUnhandled);

  const job = makeJob();
  const queue = makeQueue(job);
  queue.heartbeat.mockRejectedValue(new Error('network down'));

  const handler: JobHandler = (_job, ctx) => new Promise((resolve, reject) => {
    ctx.signal.addEventListener('abort', () => reject(new Error('aborted')));
    setTimeout(resolve, 10_000); // would hang forever without the abort
  });

  try {
    const resultP = runOnce(queue, handler, { workerId: 'w1', leaseSeconds: 2 });
    await jest.advanceTimersByTimeAsync(700); // let the first heartbeat tick (≈666ms) fire and reject
    const outcome = await resultP;

    expect(outcome).toBe('failed'); // caught as a throw ⇒ retryable fail
    expect(queue.fail).toHaveBeenCalledTimes(1);
    expect(queue.fail).toHaveBeenCalledWith(job.id, 'w1', job.leaseToken, 'aborted', { retryable: true, billableSucceeded: true, metered: false });
    await Promise.resolve(); // flush any queued unhandledRejection events
    expect(unhandled).toHaveLength(0);
  } finally {
    process.off('unhandledRejection', onUnhandled);
  }
});

test("(f) lease loss mid-handler causes exactly one terminal write — the 'lost' no-op path", async () => {
  jest.useFakeTimers();
  const job = makeJob();
  const queue = makeQueue(job);
  queue.heartbeat.mockResolvedValue({ ok: false });
  queue.fail.mockResolvedValue({ ok: false, status: null });

  const handler: JobHandler = (_job, ctx) => new Promise((resolve, reject) => {
    ctx.signal.addEventListener('abort', () => reject(new Error('lease lost')));
    setTimeout(resolve, 10_000);
  });

  const resultP = runOnce(queue, handler, { workerId: 'w1', leaseSeconds: 2 });
  await jest.advanceTimersByTimeAsync(700);
  const outcome = await resultP;

  expect(outcome).toBe('lost');
  expect(queue.fail).toHaveBeenCalledTimes(1);
  expect(queue.complete).not.toHaveBeenCalled();
});

test('(g) wall-clock exceeded aborts and fails the job retryably', async () => {
  jest.useFakeTimers();
  const job = makeJob();
  const queue = makeQueue(job);

  const handler: JobHandler = (_job, ctx) => new Promise((resolve, reject) => {
    ctx.signal.addEventListener('abort', () => reject(new Error('wall clock exceeded')));
    setTimeout(resolve, 60_000); // far beyond wallClockMs
  });

  const resultP = runOnce(queue, handler, { workerId: 'w1', leaseSeconds: 120, wallClockMs: 50 });
  await jest.advanceTimersByTimeAsync(50);
  const outcome = await resultP;

  expect(outcome).toBe('failed');
  expect(queue.fail).toHaveBeenCalledTimes(1);
  expect(queue.fail).toHaveBeenCalledWith(job.id, 'w1', job.leaseToken, 'wall clock exceeded', { retryable: true, billableSucceeded: true, metered: false });
  // wall-clock fires long before the lease's own heartbeat interval (40s) ever ticks.
  expect(queue.heartbeat).not.toHaveBeenCalled();
});

test("(h) a throwing terminal fail RPC resolves to 'lost', it does not reject out of runOnce", async () => {
  const job = makeJob();
  const queue = makeQueue(job);
  // Handler throws (enters the catch) AND the terminal fail RPC itself throws (transient DB error).
  queue.fail.mockRejectedValue(new Error('db unavailable'));
  const handler: JobHandler = async () => { throw new Error('handler boom'); };

  // Must RESOLVE to 'lost' — never reject — so the long-lived worker loop (Task 8) can't be
  // crashed by an unhandled rejection escaping runOnce's declared outcome contract.
  await expect(runOnce(queue, handler, { workerId: 'w1' })).resolves.toBe('lost');
  expect(queue.fail).toHaveBeenCalledTimes(1);
  expect(queue.complete).not.toHaveBeenCalled();
});

test('runOnce returns idle when the queue has no job (echoHandler smoke)', async () => {
  const queue = makeQueue(makeJob());
  queue.claim.mockResolvedValueOnce(null);
  const outcome = await runOnce(queue, echoHandler, { workerId: 'w-empty' });
  expect(outcome).toBe('idle');
});

describe('worker-runner release decision (Task 10)', () => {
  const prev = process.env.CLOUD_GEMINI_RELEASE_VERIFIED;
  afterEach(() => { process.env.CLOUD_GEMINI_RELEASE_VERIFIED = prev; });

  // helper: run one job through runOnce with a handler that throws `err` (optionally metering first);
  // returns the args the stub queue.fail() was called with.
  async function failArgsFor(err: unknown, opts: { meterFirst?: boolean; gate?: string } = {}) {
    process.env.CLOUD_GEMINI_RELEASE_VERIFIED = opts.gate ?? 'true';
    const failSpy = jest.fn(async (..._args: Parameters<JobQueue['fail']>) => ({ ok: true, status: 'failed' as const }));
    const job = makeJob();
    const queue = makeQueue(job); queue.fail = failSpy;
    const handler = async (_job: unknown, ctx: { billing: { metered: boolean } }) => {
      if (opts.meterFirst) ctx.billing.metered = true;
      throw err;
    };
    await runOnce(queue, handler as JobHandler, { workerId: 'w' });
    return failSpy.mock.calls[0];                                    // [jobId, workerId, token, err, optsArg]
  }

  it('class-A not-metered {503} → billableSucceeded=false (RELEASE), retryable=true', async () => {
    const [, , , , optsArg] = await failArgsFor(new GoogleGenerativeAIFetchError('x', 503, 'x'));
    expect(optsArg).toEqual({ retryable: true, billableSucceeded: false, metered: false });
  });

  it('metered-then-{503} → billableSucceeded=true (KEEP), latch overrides class-A', async () => {
    const [, , , , optsArg] = await failArgsFor(new GoogleGenerativeAIFetchError('x', 503, 'x'), { meterFirst: true });
    expect(optsArg.billableSucceeded).toBe(true);
  });

  it('gate OFF → even a clean {503} is billableSucceeded=true (KEEP)', async () => {
    const [, , , , optsArg] = await failArgsFor(new GoogleGenerativeAIFetchError('x', 503, 'x'), { gate: 'false' });
    expect(optsArg.billableSucceeded).toBe(true);
  });

  it('WRAPPED NonRetryableError → retryable=false AND billableSucceeded=false (H1)', async () => {
    const wrapped = new Error('transcript unavailable', { cause: new NonRetryableError('disabled') });
    const [, , , , optsArg] = await failArgsFor(wrapped);
    expect(optsArg).toEqual({ retryable: false, billableSucceeded: false, metered: false });   // isNonRetryable walked the chain
  });
});

// T13-d (Task 13/H1): every queue.fail() call — terminal AND requeue — must report THIS attempt's
// billing latch, so fail_job can durably OR-persist it into jobs.ever_metered before the next
// attempt runs. Extends the Task 10 spy assertions above (which already cover the {retryable,
// billableSucceeded} shape) with a dedicated check of the `metered` field in isolation.
describe('worker-runner ever_metered wiring (Task 13/H1)', () => {
  const prev = process.env.CLOUD_GEMINI_RELEASE_VERIFIED;
  afterEach(() => { process.env.CLOUD_GEMINI_RELEASE_VERIFIED = prev; });

  async function failArgsFor(err: unknown, opts: { meterFirst?: boolean } = {}) {
    process.env.CLOUD_GEMINI_RELEASE_VERIFIED = 'true';
    const failSpy = jest.fn(async (..._args: Parameters<JobQueue['fail']>) => ({ ok: true, status: 'failed' as const }));
    const job = makeJob();
    const queue = makeQueue(job); queue.fail = failSpy;
    const handler = async (_job: unknown, ctx: { billing: { metered: boolean } }) => {
      if (opts.meterFirst) ctx.billing.metered = true;
      throw err;
    };
    await runOnce(queue, handler as JobHandler, { workerId: 'w' });
    return failSpy.mock.calls[0];
  }

  it('a metered-then-throw handler reports metered:true on queue.fail (durable across retries)', async () => {
    const [, , , , optsArg] = await failArgsFor(new Error('boom'), { meterFirst: true });
    expect(optsArg.metered).toBe(true);
  });

  it('a not-metered throw reports metered:false on queue.fail', async () => {
    const [, , , , optsArg] = await failArgsFor(new Error('boom'));
    expect(optsArg.metered).toBe(false);
  });
});
