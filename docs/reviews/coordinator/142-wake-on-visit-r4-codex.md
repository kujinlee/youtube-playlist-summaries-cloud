<!-- codex-review: model=gpt-5.5 -->

# Codex adversarial review — backlog #142 wake-on-visit — round 4 (final-tree pass)

**REVIEW GAP:** claude — not invoked; round 4 is a deliberate SINGLE-HALF final-tree pass, not a
review round. Rounds 1–3 each ran both halves and converged (2 Blocking + 3 High → 1 High + 5 Medium
→ 0 Blocking + 0 High), and round 3's Claude half judged explicitly that *"a round 4 is not
warranted"*. What forced this pass was CI's final-tree gate, which is a different question from
convergence: it refused the merge because no recorded verdict had seen the tree being merged, the
delta being master's already-reviewed #321 code arriving via merge, one small fold, and a merge
resolution nobody had checked. The human was given three options — this single half, a
`NO-REVIEW:` declaration, or a full round 4 — and chose this one, so that the append-only
`docs/dashboard-entries.md` resolution would actually be reviewed by someone. Its silent failure
mode (a released entry deleted with nothing going red) is why a declaration was not enough.


## Verdict: FINDINGS

One Low finding: the tree is merge-safe, but `lib/job-queue/worker-wake.ts:96` overstates that no unit test can kill removal of the internal `.finally(...).catch(...)`.

## The merge resolution — per file, did it lose anything?

`docs/dashboard-entries.md`: no loss found. I split each parent and the merge into whole `## YYYY-MM-DD` blocks and hashed exact block contents.

Parent 1 had 218 blocks, parent 2 had 219, merge has 222. Missing from either parent: 0. Duplicated beyond parent max: 0. Extra beyond parent union: 0. Dates are nondecreasing. The merge tail keeps master’s #321 entries before this branch’s wake-on-visit entries; see `docs/dashboard-entries.md:10575`, `docs/dashboard-entries.md:10610`, `docs/dashboard-entries.md:10646`.

`docs/backlog.md`: no row loss found. Rows 140, 141, 142 each appear once at `docs/backlog.md:168`, `docs/backlog.md:169`, `docs/backlog.md:170`. Row 140 matches master’s closed `✅ (was 🟢)` version; rows 141/142 match this branch’s closed `✅ (was 🟠)` / `✅ (was 🟢)` versions. `gen-backlog-page.py --self-test` passed 165/165.

`docs/roadmap-to-launch.md`: count is correct at `docs/roadmap-to-launch.md:2045`: `2891 unit / 278 suites`. I re-derived it with both `npm test -- --runInBand` and `npm test -- --ci --json --outputFile=jest-results.json`.

## The round-3 fold

`app/api/jobs/route.ts:79-107`: the corrected read-path comment is true. It recovers queued summary jobs only. It excludes crashed-worker `active` rows on purpose, and the dig gap is accurately described because `listByPlaylist` hard-filters `job_kind = 'summary'` at `lib/storage/supabase/supabase-job-queue.ts:24-29`.

`tests/lib/worker-wake.test.ts:180-198`: the enqueue-side guard is now timing-free and mutation-killing. Removing `void this.wake().catch(() => {})` from `lib/job-queue/enqueuer.ts:78` made `tests/lib/worker-wake.test.ts` fail with `catchSpy` called 0 times.

`worker/main.ts:252-264`: the `server.listen(port)` declination is now precise enough: it cites the actual `node:22-bookworm-slim` / v22.23.2 measurement and does not overclaim from local Node 20.

Finding: `lib/job-queue/worker-wake.ts:96-109` says no unit test can kill removal of the final `.catch()`. Existing behavior tests cannot: with that `.catch()` removed, `tests/lib/worker-wake.test.ts` still passed 22/22. But a temporary unit probe using `jest.spyOn(Promise.prototype, 'catch')` killed the mutation: red with the guard removed, green with it present. That makes the absolute comment false, and there should be a narrow white-box test or the comment should be softened.

## Do the merged #321 sweep policy and this branch's idle-exit compose?

Yes. `runWorkerLoop` constructs one sweep policy outside the loop at `worker/main.ts:149-150` and passes it into `runOnce` at `worker/main.ts:154-158`, so the cursor is not reset per poll. `runOnce` runs the sweep before claiming at `lib/job-queue/worker-runner.ts:187-188`, catches policy rejection at `lib/job-queue/worker-runner.ts:187-194`, and still checks shutdown before claim at `lib/job-queue/worker-runner.ts:204`.

Idle exit only considers exit after `runOnce` returns idle, and then asks `queueIsDrained` at `worker/main.ts:161-165`. That function fails safe at `worker/main.ts:329-335`; the Supabase implementation counts both `queued` and `active` rows at `lib/storage/supabase/supabase-job-queue.ts:104-110`. Focused composition tests passed: `tests/lib/worker-idle-exit.test.ts` + `tests/lib/lease-sweep-cadence.test.ts` = 44 passed.

## Re-derivation of the claims

Passed:

`npx tsc --noEmit`

`npm test -- --runInBand`: 2891 tests / 278 suites

`npm test -- --ci --json --outputFile=jest-results.json`: 2891 tests / 278 suites

`python3 scripts/check-test-counts.py`: roadmap count matches suite

`fly config validate -c fly.toml` and `fly config validate -c fly.worker.toml`

`python3 scripts/check-docs.py`

`python3 scripts/check-review-rounds.py`

`python3 scripts/check-anchors.py`

`python3 scripts/check-dashboard-entry.py`

`python3 scripts/check-backlog-closure.py`

`python3 scripts/check-selftest-counts.py`

`python3 scripts/gen-backlog-page.py --self-test`

Mutation probes were reverted. Final `git status --short` is clean.

## Findings (if any)

Low: `lib/job-queue/worker-wake.ts:96` says no unit test can kill removal of the internal `.finally(...).catch(...)`. I proved a temporary white-box unit test can kill it by spying on `Promise.prototype.catch`: guard removed failed with 0 catch calls; guard present passed. The existing suite still cannot kill it behaviorally because `send()` swallows all rejections, but the comment’s absolute claim is false.

## What I could not run

I did not run a live Fly deployment/autostart falsifier. All requested local gates and mutation probes were run, and the final tree is clean.
