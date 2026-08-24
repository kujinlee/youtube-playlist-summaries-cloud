<!-- codex-review: model=gpt-5.5 -->

**Blocking**

`docs/superpowers/plans/2026-08-22-m1-honest-card.md:280`

Task 2 adds a passing characterization that asserts the worker’s paid body is silently discarded under Supabase `promote()` semantics. That is already a live defect tracked by backlog #22, and the repo already encodes it correctly as an `it.failing` tripwire in `tests/lib/job-queue/summary-handler-promote-divergence.test.ts:140`.

Failure scenario: final key already contains `TRANSFERRED local body`; worker pays Gemini for `WORKER body`; `SupabaseBlobStore.promote()` skips because final exists; the plan’s new test passes by asserting the stale transferred body remains live. A future M5 implementer now has one test demanding the defect remain true and one tripwire expecting it to flip.

Suggested fix: remove this passing characterization, or rewrite it as an `it.failing` desired-behavior test colocated with the existing promote-divergence tripwire. Do not assert paid-output discard as expected behavior.

**High**

`docs/superpowers/plans/2026-08-22-m1-honest-card.md:45`

The “Videos with corrections” consequence is over-broad. The real sync path runs Class B first and has an explicit unresolved-corrections guard before Class A at `lib/cloud-sync/sync-run.ts:707-720`. `reconcileClassA` alone would copy the current body, but `runSync` deliberately skips Class A when both sides have MD and corrections are an unresolved no-write conflict.

Failure scenario: local has body generated for corrections `A`; cloud has body generated without corrections after M1; local/cloud human `corrections` differ and are backfilled. `reconcileHuman` logs a conflict; `sync-run.ts:707-720` skips Class A, flags regen, and preserves both bodies. The plan predicts `lCur=true, cCur=false -> copyToCloud`.

Suggested fix: qualify the consequence: “when corrections have a settled reconciled value.” Add a note that unresolved Class-B corrections conflicts still suppress Class A, and add/point to an end-to-end `runSync` test if M1 depends on that interaction.

**Medium**

`docs/superpowers/plans/2026-08-22-m1-honest-card.md:316`

Task 3 is not executable as written against the actual repo. `tests/lib/cloud-sync/reconcile-class-a.test.ts` already exists and already defines `const CUR` at line 6. The pasted snippet defines another top-level `const CUR` at plan line 342.

Failure scenario: an engineer follows the “write the test” block literally in the existing file. TypeScript/Jest fails on duplicate block-scoped declarations instead of testing M1.

Suggested fix: provide an “append inside existing `describe`” patch using the existing `S` helper and `CUR`, or rename the new constants and state exactly where to insert them.

**Medium**

`docs/superpowers/plans/2026-08-22-m1-honest-card.md:222`

Task 1 Step 6 says a broken Class-A sync test is “a real signal, not noise,” but gives no decision rule. In this repo, Class-A has both pure tests and integration guards for corrections conflicts, unreadable blobs, and baseline advancement; a failing test could mean the plan premise is wrong, the implementation timestamp changed an ordering, or an existing test encoded the pre-M1 lie.

Failure scenario: after adding `mdGeneratedAt`, a sync test changes from `copyToLocal` to `copyToCloud`. The instruction only says “read it,” so an implementer can rationalize either updating or preserving the test.

Suggested fix: add a concrete rubric: identify which branch changed, list the old/new `ClassASignals`, and require plan update/re-review before changing any Class-A expected action.

**Low**

`docs/superpowers/plans/2026-08-22-append-only-generations-roadmap.md:34`

I could not reproduce the measured “192 call sites across 40 files” figure with an equivalent grep. A targeted search over `summaryMd`, `baseName`, `baseOf`, model-key and `.md` base derivations produced 203 hits across 40 files. The file count matches; the call-site count does not.

Verified measured rows:
`schema/` is 4 files / 4,108 lines; shipped migrations stop at `0025_settle_is_observable.sql`; `generation_id` has zero refs under `lib app worker supabase`; Jest lists 268 suites. I did not run the full suite, so “2,722 tests green” is NOT VERIFIED.

Suggested fix: record the exact command used for each measured table row, or change the count to a reproducible value.

**Verdict**

NOT CONVERGED.
