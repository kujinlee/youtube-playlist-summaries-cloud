<!-- codex-review: model=gpt-5.5 -->

**Blocking**
1. The “finally mistake is unwritable” claim is too strong for the exported custom policy seam.  
   [lib/job-queue/worker-runner.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/worker-runner.ts:20), [worker/main.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/worker/main.ts:139)

   Failure scenario: a caller passes a custom `SweepPolicy` via `runOnce(..., { sweepPolicy })` or `runWorkerLoop(..., { sweepGate })`:

   ```ts
   const bad: SweepPolicy = {
     async run(sweep) {
       if (insideWindow()) return;
       try {
         await sweep();
       } finally {
         lastSweptAt = now(); // commits even when sweep throws
       }
     },
   };
   ```

   Inputs -> wrong outcome: `queue.sweepExpired()` throws on poll 1; `bad.run` commits in `finally`; `runOnce`’s outer catch logs and still claims; the next poll skips the sweep for the cadence window. P1 is broken for that supplied policy.

   Important nuance: this mistake is unwritable at the `runOnce` call site now. It is still writable inside any custom `SweepPolicy`, and `SweepPolicy` is exported and accepted as an option. So the implementation is sound for the shipped policies, but the blanket “unwritable by construction” rationale is false unless it is scoped to “unwritable by callers of the policy.”

   Fix: either narrow the docs/backlog/comments to “unwritable at the call site; policy implementations still own the contract,” or remove/privatize the arbitrary `SweepPolicy` injection seam and expose only vetted constructors.

**High**
None.

**Medium**
None found in shipped behavior. P1-P5 hold for `makeSweepGate`, `ALWAYS_SWEEP`, and the current production wiring.

**Low**
1. Stale comments still describe the deleted `onSwept()` protocol.  
   [worker/main.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/worker/main.ts:69), [lib/job-queue/worker-runner.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/worker-runner.ts:85)

   Scenario: a reader follows the current comment text, which says the cursor advances in `onSwept()` and that `onSwept()` is inside the `try`, but the code now has only `run(sweep)`. No runtime failure, but this is exactly the protocol text this refactor is trying to make less fragile.

   Fix: rewrite those clauses to say `makeSweepGate.run` commits `lastSweptAt` only after `await sweep()` resolves.

**Properties Checked**
P1 preserved for shipped policies: `makeSweepGate.run` sets `lastSweptAt = now()` only after `await sweep()` resolves. Killed by `a sweep that THROWS does not spend the window — the next poll retries` and by `keeps sweeping AND keeps claiming when every sweep throws`.

P2 preserved: both `makeSweepGate` and `ALWAYS_SWEEP` catch sweep failure, and `runOnce` has a defence-in-depth catch around bad policies. Killed by `still claims when the sweep throws` and `still claims when the POLICY ITSELF rejects`.

P3 preserved: `runOnce` checks `shutdownSignal?.aborted` after the sweep and before claim. Killed by both shutdown-during-failed-sweep and shutdown-during-successful-sweep tests.

P4 preserved: missing policy uses `ALWAYS_SWEEP`, which currently holds no state and always invokes `sweep`. Killed by `sweeps by default when no policy is supplied`.

P5 preserved: production default clock is `performance.now()`, injected clock backwards steps fail open, and the default clock is directly tested. Killed by the injected backwards-clock test, the default wall-clock-step test, and the default-clock-advances test.

**Other Attacks**
The outer catch is not redundant: it protects claims from a custom/future policy that rejects. It can also swallow a malformed policy TypeError, but only with invalid runtime input outside the TypeScript contract; it logs and preserves intake. I would not block on that.

`ALWAYS_SWEEP` is safe today: [worker-runner.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/worker-runner.ts:35) has no state. If state is later added, the singleton becomes dangerous; the current tests likely catch a simple cadence state because there are multiple no-policy `runOnce` calls in the same file, but a dedicated “default sweeps on two consecutive calls” test would make that explicit.

No `this` hazard: `() => queue.sweepExpired()` calls the method as `queue.sweepExpired()`, preserving receiver binding. The closure is created per `runOnce`, so no stale queue capture.

Repo grep found no other production implementers/consumers beyond `makeSweepGate`, `ALWAYS_SWEEP`, `runOnce`, and `runWorkerLoop`; the rest are tests.

Verification: `npx jest tests/lib/lease-sweep-cadence.test.ts` passed, 24/24. `npx tsc --noEmit` passed. Note: literal `git diff origin/master...HEAD` was empty in this checkout; I reviewed the real working tree diff against `origin/master`, which contains the described changes.
