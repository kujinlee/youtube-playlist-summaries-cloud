<!-- codex-review: model=gpt-5.5 -->

# Codex adversarial review — backlog #142 wake-on-visit — round 3

## Verdict: FINDINGS

## Re-derivation of the eight claims

1. **Partly false.** `onFatal` is now required and called unconditionally at `worker/main.ts:243` and `worker/main.ts:286`; the new handler comment at `worker/main.ts:266-281` accurately says the in-flight job is aborted. But the disproven “finishes the in-flight job” sentence still survives in `fly.toml:21-22` and `fly.worker.toml:38-39`.

2. **Partly true, partly unguarded.** The route-side `.catch()` at `app/api/jobs/route.ts:94` is genuinely bound: after a green control, removing it made `tests/api/jobs-route-wake.test.ts:93-102` fail on `flycast unreachable`. The enqueue-side `.catch()` at `lib/job-queue/enqueuer.ts:78` is not bound by the focused suites: removing it left `tests/lib/worker-wake.test.ts` and `tests/api/jobs-route-wake.test.ts` green. The 50ms settle is sufficient for the immediate `Promise.reject` being tested; it is not a general proof for delayed rejection.

3. **Correct.** `kill_signal` / `kill_timeout` values are pinned at `tests/lib/worker-idle-exit.test.ts:285-287`. Mutating `fly.worker.toml:40` from `SIGTERM` to `SIGKILL` failed that test.

4. **Acceptable declination, with caveat.** The written declination is at `worker/main.ts:247-253`. Node’s current docs say omitted host binds `::` when IPv6 is available and may also listen on IPv4; Fly’s docs still recommend `0.0.0.0` and explicitly warn wildcard behavior depends on language/library. I measured local Node 20 binding `::`; I did not measure Node 22 inside the image.

5. **Correct.** The unmeasured “predicate no index serves” clause was cut at `worker/main.ts:162-167`. Local Supabase `EXPLAIN` chose a seq scan on the tiny table, but `SET enable_seqscan=off` showed the predicate can use a partial index. Cutting, rather than reversing, was right.

6. **Correct.** `docs/deploy.md:229-270` deletes the unenforceable “keep stopped” phase, accepts the Fly scale-count refutation, uses delete-group + deploy as the stable transition, and gives `fly deploy --process-groups web` as the interim rule. Fly docs support this: process-group deploy creates/destroys group Machines, and scale-to-zero is not preserved when deploying from no Machines. Sources: https://fly.io/docs/launch/processes/ and https://fly.io/docs/launch/scale-count/.

7. **Correct.** The falsifier now requires `fly logs -a yps-worker` to show the claim at `docs/deploy.md:223-226`.

8. **Matched.** `npx tsc --noEmit` clean; `npm test -- --runInBand` passed 278 suites / 2882 tests; both Fly configs validate; `check-docs.py`, `check-review-rounds.py`, `check-anchors.py`, `check-test-counts.py`, and `check-dashboard-entry.py` all exit 0.

## Findings

### [Medium] 1 — The disproven “finishes the in-flight job” claim still survives in both Fly configs

**Evidence:** `fly.toml:21-22` says “stops claiming, finishes the in-flight job, exits.” `fly.worker.toml:38-39` repeats the same claim. That directly contradicts the corrected listener comment at `worker/main.ts:270-281`, which now says the handler is aborted and the job dead-letters with spend kept.

**Introduced by an earlier round's fix?** yes.

**Why it matters:** These are load-bearing operational comments beside `kill_signal` / `kill_timeout`. They preserve the exact false model that created #139: future work can read the config and believe graceful drain is real when the code aborts the handler.

**Fix:** Replace both config comments with the measured behavior: SIGTERM/fatal shutdown aborts the handler today; `kill_timeout` only gives time for current shutdown behavior, not for finishing the job. Point at backlog #139.

### [Low] 2 — The enqueue-side `.catch()` is present but not mutation-guarded

**Evidence:** `lib/job-queue/enqueuer.ts:78` correctly uses `void this.wake().catch(() => {})`. But after a green control, mutating that line to `void this.wake();` left both `npm test -- tests/lib/worker-wake.test.ts --runInBand` and `npm test -- tests/api/jobs-route-wake.test.ts --runInBand` green.

**Introduced by an earlier round's fix?** yes.

**Why it matters:** This is a guard gap, not a live production bug: the default wake swallows rejections. But the whole reason for adding `.catch()` was to make call sites independent of that invariant. One of the two call sites can regress silently.

**Fix:** Add an enqueue-side test with an injected `wake = jest.fn(() => Promise.reject(...))`, await `enqueue()`, then wait one macrotask/settle window so the unhandled rejection lands if `.catch()` is removed.

## Your round 2 fix (b), refuted by the Claude half — do you accept the refutation?

Yes. I accept the refutation. Fly’s scale-count docs say scale created/destroyed state is preserved except when scaled all the way to zero, and deploying with no existing Machines seeds new Machines from `[processes]`. So “scale old group to zero after each deploy” is the unstable state, not a fix. The current runbook’s `fly deploy --process-groups web` interim rule is better.

## Things I checked and found correct

`onFatal?.()` is gone; `onFatal()` is unconditional.

`server.listen(port)` is now a written, sourced declination rather than a dropped finding. I would still prefer a Node 22-in-image measurement before calling it fully settled.

`fly.worker.toml` has `auto_start_machines = true`, `[[services.ports]] port = 80`, `internal_port = 8081`, and `policy = "on-failure"`.

The old worker transition docs now match the Fly docs and no longer rely on keeping a Machine stopped.

Worktree ended clean after all mutations.

## What I could not run

I did not run a live Fly deploy or observe real Flycast traffic.

I did not measure `server.listen(port)` inside the Node 22 Fly image; local measurement was Node 20, and Node’s current docs were used for the version-stability check.

I did not run integration/E2E suites beyond the local Supabase `EXPLAIN`.
