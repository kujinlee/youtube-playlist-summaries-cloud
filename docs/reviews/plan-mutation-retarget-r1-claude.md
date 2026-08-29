# Backlog #70 plan — dual review, round 1 (Claude half)

**Subject:** `docs/superpowers/plans/2026-08-29-mutation-manifest-retarget.md` at `1ce0218`.
**Codex half:** [`plan-mutation-retarget-r1-codex.md`](plan-mutation-retarget-r1-codex.md).

⚠ **REVIEW GAP: claude — the dispatched independent reviewer never returned.** It was pinged twice
and produced nothing. Per `docs/plugins.md` the rule is do not wait; this half is therefore the
coordinator's own review, and it is weaker than an independent pass because the author reviewed
their own document. Recorded rather than hidden.

**Verdict: NOT CONVERGED — 4 defects, all in the plan's own text, all fixed before implementation.**

| # | Found by | Defect |
|---|---|---|
| 1 | coordinator | **The case-count chain was asserted, not counted.** The self-review claimed 121→125→130→134→138 "each bumped in the task that adds the cases". Counted: T1 adds 4, T2 5, T3 3, T4 3 → 121→125→130→133→136. Left alone it reddens every task from T3 on, for a reason unrelated to the task. |
| 2 | Codex | **T1's fixture anchor was ambiguous.** `"return 1"` occurs twice in it (`f`'s body and `_self_test`'s failure branch) and the engine *refuses* ambiguous anchors, so the case proving the extraction works would have failed for an unrelated reason. |
| 3 | Codex | **T6's assertion forbade prose that must survive.** `assert "<!-- file:" not in s` trips on `:3055` of the dashboard plan, a table cell recording the `../escape.py` path-escape defect. The regex was right; the assertion was wrong. Now line-anchored. |
| 4 | coordinator | **1,401 was inherited, never counted.** The figure came from backlog #70 and was propagated into the spec, the plan and a drafted CI comment — while the same spec's measured table said 1,551 two sections earlier. Real: **1,541** lines in the blocks. |

## Verified sound (both halves agree)

The extraction's substitution table names no missing variable; `ok` as a local is correct; `check()`
preserves report ordering; `run_suite(d, "scripts/gen-dashboard.py")` works after `copytree`
(coordinator prototyped it: 113/113 with only `scripts/` copied, no `docs/` needed); the exact count
catches both shrinkage and growth; the round-trip comparison is sound because `(file, name)` is
unique. Codex additionally built a standalone prototype of the delivered-script path and got
43 mutations / 0 survivors before any of this was implemented.

## What round 1 did NOT catch, and execution did

Three further defects surfaced only when the plan was executed — recorded in
[`branch-mutation-retarget-r1-claude.md`](branch-mutation-retarget-r1-claude.md). Two reviewers read
this document and neither found them. **Reading a plan is a weaker instrument than running it.**
