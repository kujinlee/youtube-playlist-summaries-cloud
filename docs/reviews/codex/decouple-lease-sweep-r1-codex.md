<!-- codex-review: model=gpt-5.5 -->

**Blocking**
None.

**High**
None.

**Medium**
1. Sweep failures consume the whole 60s gate window before any sweep succeeds.  
   [worker/main.ts:43](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/worker/main.ts:43), [lib/job-queue/worker-runner.ts:31](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/worker-runner.ts:31)  
   Scenario: a job’s lease has expired; the worker reaches the first eligible sweep; `shouldSweep()` advances `lastSweptAt`; `queue.sweepExpired()` then throws on a transient Supabase/network failure. `runWorkerLoop` catches and continues, but the gate stays closed for 60s, so the expired job is not reclaimed on the next 2s poll. Claimed worst-case recovery is no longer ~180s; one failed sweep makes it ~240s, repeated failures at sweep boundaries can extend it further.  
   Fix: only advance the sweep cursor after `sweepExpired()` resolves successfully, or make failed sweeps retry on the next poll. The current `() => boolean` seam cannot express “commit after success” cleanly; split it into `shouldSweep` + `markSweepSucceeded`, or move the production gate around the actual sweep call.

**Low**
1. The gate uses wall-clock time, so a backward clock step can suppress sweeps longer than intended.  
   [worker/main.ts:40](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/worker/main.ts:40)  
   Scenario: worker sweeps at local `Date.now() = T`; host clock/NTP steps back by five minutes; `t - lastSweptAt` remains negative or below 60s until the wall clock catches up, so expired leases sit unreclaimed well past the promised bound.  
   Fix: default the gate clock to a monotonic source, e.g. `performance.now()`, since the gate only needs elapsed process time.

2. The `1.5-2.2 GB/month` measurement is not derivable from the stated numbers.  
   [docs/dashboard-entries.md:9856](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/dashboard-entries.md:9856)  
   Scenario: using the stated daily counts and `919 B headers + 2 B body = 921 B`, monthly traffic is about `2.10-2.25 GB` decimal, or `1.96-2.09 GiB`, for all idle worker REST responses. The removed sweep half is about `1.05-1.12 GB` decimal. I cannot reproduce a `1.5 GB` lower bound from the written evidence.  
   Fix: recalc the range and state whether it is decimal GB or GiB, and whether it describes total idle worker egress or removed sweep egress. Same correction should be mirrored in the code/test comments that repeat the range.

**Specific Attacks**
Default preservation: preserved for direct `runOnce` callers via `opts.shouldSweep?.() ?? true`. I found no existing direct `runOnce` integration test that depends on an expired lease being swept and claimed in the same call; most claim queued jobs or use mocks. `runWorkerLoop` deliberately changes behavior after the first iteration by passing the gate.

Concurrency: no new double-claim race. `claim_next_job` only claims `status='queued'`; `sweep_expired_leases` requeues expired `active` rows under `for update skip locked`. Multiple machines having independent gates means an expired row is unclaimable until some worker sweeps, but that is the accepted up-to-60s window, not a double-claim hole.

60s vs 120s lease: production `main()` does not pass `leaseSeconds`; it uses the `runOnce` default `120`, heartbeat interval `40s`. Tests using `leaseSeconds: 2` call `runOnce` directly, whose default still sweeps every call. If production ever makes lease length configurable below 60s, this gate becomes too slow unless `SWEEP_MS` is tied to the lease or capped below it.

`pollMs` seam: test-only seam is contained in `runWorkerLoop`; `main()` still calls `runWorkerLoop({ queue, handler, shutdownSignal, workerId })`, so production defaults to `POLL_MS = 2000`.

Tests: the new cadence tests kill the major mutations: first-call closed, always-open gate, cursor-advanced-on-every-call, unconditional sweep, `?? false`, and production loop not wiring the gate. The `runWorkerLoop` ratio test would still pass with the cursor-advances-every-call bug because it finishes inside one 60s window; the 3-minute pure gate test is what kills that mutation. Tests do not cover failed sweep consuming the window or wall-clock rollback.

Integration assertion: `sweepCalls === 1` is implied by this test’s structure: first loop sweeps, `claim` throws, loop sleeps 2s, second loop is inside the 60s gate and aborts. The file has `jest.setTimeout(20_000)`, so CI cannot legitimately elapse two 60s windows and still pass.

Other hot paths: I found UI/job polling code, but no other idle server-side Supabase `claim_next_job`/`sweep_expired_leases`-style hot loop in the reviewed path. A future improvement would be folding reclaim into a cheaper claim-side RPC, but that is a bigger SQL/API change, not required for this branch.

Verification run:
`npm test -- --runTestsByPath tests/lib/lease-sweep-cadence.test.ts` passed.  
`npm run test:integration -- --runTestsByPath tests/integration/worker-main.test.ts` passed.
