# Adversarial review — append-only roadmap + M1 plan v2 (round 2)

You are an adversarial reviewer. Find defects, not reasons to approve. **Read the actual files.**

## What to review

- `docs/superpowers/plans/2026-08-22-m1-honest-card.md` — **v2**, rewritten after round 1.
- `docs/superpowers/plans/2026-08-22-append-only-generations-roadmap.md` — spine, amended.

## Round 1's findings, and why this round exists

Round 1 (`docs/reviews/plan-append-only-m1-r1-codex.md`,
`docs/reviews/plan-append-only-m1-r1-claude.md`) returned NOT CONVERGED from both halves. v2 claims
to fix all of it.

**This repo's standing count of "a fix that moved or reintroduced a defect" stands at seven, three
of them caused by a review's own fixes.** So the primary question of round 2 is not "were the
findings addressed" but **"did addressing them break something new?"** Weight your effort there.

## The central change — attack this hardest

v1 stamped `mdGeneratedAt`/`mdCorrectionsHash` unconditionally. Round-1 B1 proved that wrong:
`SupabaseBlobStore.promote` is create-if-absent (`lib/storage/supabase/supabase-blob-store.ts:116-134`),
so the worker's bytes often never become the live body, and the pre-existing card was *accidentally
correct* in that case.

v2's replacement (plan Task 1, Step 5) reads the final key back after `promote` and stamps only when
`mdHash(live) === mdHash(core.mdContent)`, failing closed on an unreadable read-back.

Questions to press, non-exhaustively:

1. **Does the read-back actually prove what v2 claims?** Consider: the transferred body being
   byte-identical to the worker's; `mdHash`'s canonicalization (`lib/cloud-sync/content-hash.ts`)
   collapsing two different files to one hash; a third writer landing between `promote` and the
   read-back.
2. **`.catch(() => null)` swallows every error.** This repo has a memory titled *"a shim can fail in
   both directions"* and another on tests that catch "any error". Is failing closed here correct, or
   is it a silent-failure pattern that will hide a real fault? Does it differ from
   `SupabaseBlobStore.get`, which already returns `null` for every failure
   (`sync-run.ts:668-675` documents that it swallows network, 5xx, timeout and RLS denial alike)?
3. **Is `generatedAt`, captured before the blob write, the right instant** for a field consumed by
   `reconcileClassA`'s recency tiebreak (`lib/cloud-sync/reconcile-class-a.ts:49`)?
4. **One extra `GET` per summary job on the money path.** Correctly scoped as negligible, or does it
   interact with the serve-path deadline/lease work (backlog #46, migrations 0024/0025)?
5. **Does the `published` gate change any Class-A outcome the v2 Consequences table does not list?**
   Round-1 H6 found one that v1's table missed. Walk the table's six rows independently against
   `reconcile-class-a.ts:17-50` and `sync-run.ts:640-812`.

## The other v2 changes — verify each fix, and check it introduced nothing

- Task 1/2 fixtures: assertions now guarded by `expect(...length).toBeGreaterThan(0)`; the
  interleaving is modelled as `readVideo → null` (the handler's read predates the transfer) with the
  blob pre-seeded. **Is that reachable, and does it model the #19 window or something else?** Check
  `summary-handler.ts:84-93` and the `createdThisRun` path at `:127-135`.
- Task 2's second test mocks `store.get` to **reject**. Does `InMemoryBlobStore.get`
  (`lib/storage/testing/in-memory-blob-store.ts`) reject on any real path, or does it return `null`?
  If it never rejects, is the test asserting a scenario the real backend cannot produce?
- Task 3 now appends to the existing `tests/lib/cloud-sync/reconcile-class-a.test.ts` using its
  `S()` and `CUR`. Verify no collision remains and that the tie case is genuinely uncovered.
- The characterization test is deleted in favour of the existing `it.failing` tripwire at
  `tests/lib/job-queue/summary-handler-promote-divergence.test.ts:148`. Confirm nothing now
  contradicts it.
- Task 4 Step 5 claims `DEPENDS`/`ROOTS` **cannot** express "a root is gated by an item"
  (`scripts/gen-backlog-page.py:336-366`). Verify, and check the suggested prose workaround does not
  break `depends_errors`.
- Roadmap M3: v2 says seventeen rounds ran and r17 asks for the migration, not round 18. Verify
  against `docs/reviews/spec-blob-addressing-r*-coordinator.md`. Also verify the withdrawn ranking
  claim — is `video_summary_current`
  (`docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:695-790`)
  genuinely a total order?
- The roadmap's measured table now carries a command per row. **Run at least four of them** and
  report any that do not reproduce.

## Also assess

- Task decomposition and independent reviewability; placeholders; type/name consistency across
  Tasks 1–3.
- **Test quality:** would any test pass on a broken implementation? The round-1 finding was a test
  whose assertions sat inside a loop over an empty list. Look for the same shape again.
- **Completeness:** what does v2 still not cover that it should?

## Output

Findings classified **Blocking / High / Medium / Low**, each with file:line, the concrete failure
scenario (inputs → wrong outcome), and a suggested fix. Mark anything you could not run
**NOT VERIFIED** — never let an unrun check read as a pass. End with `CONVERGED` or `NOT CONVERGED`.
