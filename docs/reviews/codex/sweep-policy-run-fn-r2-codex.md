<!-- codex-review: model=gpt-5.5 -->

**Blocking**
None.

**High**
None.

**Medium**
None.

**Low**
1. `sweepPolicyFrom` does not cover every advertised “never rejects” path.  
   [lib/job-queue/worker-runner.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/worker-runner.ts:62)

   Scenario: `sweepPolicyFrom({ due: () => { throw new Error('clock'); }, commit: () => {} }).run(...)` rejects because `cursor.due()` is outside the `try`. That does **not** starve `queue.claim` through `runOnce`, because the defence-in-depth catch at `runOnce` catches it and claims. But it does violate the exported `SweepPolicy.run` contract. Also, if `cursor.commit()` throws after a successful sweep, the catch logs `sweepExpired failed`, which is the false-diagnostic class r1 High 2 was about. Reachable with a custom cursor, or with `makeSweepGate(..., now)` if injected `now()` throws during commit.

   Fix: either document `SweepCursor` as “must not throw”, or move `due()` under policy error handling and split diagnostics so sweep failure, due failure, and commit failure are not all reported as `sweepExpired failed`.

2. The “rules are written exactly once / no implementation holds either” claim is false with tests included.  
   [tests/lib/lease-sweep-cadence.test.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/lib/lease-sweep-cadence.test.ts:226)

   The test-local `policy()` double implements `SweepPolicy.run` and re-derives both rules: `ran()` happens only after `await sweep()` resolves, and the catch swallows rejection. So the production implementations are clean, but the repo-wide claim is overstated. This also makes the commit/backlog/dashboard wording “exactly once” and “restores master’s single-copy property” too broad unless scoped to production.

   Fix: build the test double with `sweepPolicyFrom({ due: () => due, commit: ran })`, or narrow every claim to “production implementations”.

3. One comment still points to the old location of the rule.  
   [lib/job-queue/worker-runner.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/worker-runner.ts:124)

   It says the commit-on-resolve rule “now lives inside `makeSweepGate.run`”; after the r1 rewrite it lives in `sweepPolicyFrom`. No runtime impact, but it sends the next reviewer to the wrong function.

   Fix: replace `makeSweepGate.run` with `sweepPolicyFrom`.

**Path Check**
`sweepPolicyFrom` paths:

- not due: returns, no sweep, no commit, no rejection.
- due + resolve: awaits sweep, commits, resolves.
- due + throw/rejected promise: caught, logs, resolves.
- `cursor.due()` throws: rejects from `policy.run`; `runOnce` catches and still claims.
- `cursor.commit()` throws: caught, resolves, but logs the wrong subsystem.

`ALWAYS_SWEEP` is stateless as currently built. No TDZ/order hazard: `sweepPolicyFrom` is a function declaration initialized before `ALWAYS_SWEEP` evaluates, and the literal cursor has no captured mutable state.

**Mutations Run**
Focused suite control: `26/26` green. `npx tsc --noEmit` clean.

- P1 throwing sweep must not spend window: mutating `sweepPolicyFrom` to `finally { commit() }` failed 2 tests: `a sweep that THROWS does not spend the window` and `keeps sweeping AND keeps claiming when every sweep throws`.
- P2 broken sweep/policy must not block claim: rethrowing from `sweepPolicyFrom` failed both never-reject contract tests; removing `runOnce`’s defence catch failed `still claims when the POLICY ITSELF rejects`.
- P3 shutting-down worker must not claim: removing the post-sweep shutdown guard failed both shutdown-arrived-during-sweep tests.
- P4 no-policy default must sweep: defaulting to no-op failed `the default policy is STATELESS` and `sweeps by default when no policy is supplied`.
- P5 monotonic/fail-safe backwards clock: `performance.now()` to `Date.now()` failed the default-clock test; removing the negative-delta floor failed the injected-backwards-clock test.

So: not quite **CONVERGED** because of the low-severity contract/docs/test-double issues above, but the shipped production path preserves PR #318’s behavioral properties.
