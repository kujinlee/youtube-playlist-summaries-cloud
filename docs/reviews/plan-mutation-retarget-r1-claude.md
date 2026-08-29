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

---

# ADDENDUM — the independent Claude half, received after implementation

**The REVIEW GAP above is CLOSED.** The dispatched reviewer returned with 1 Blocking, 2 High,
4 Medium, 8 Low, having built a working prototype from the plan's code. Re-measured against what
actually shipped:

| Finding | Against the plan | Against shipped code | Disposition |
|---|---|---|---|
| **Blocking** — T4's ratchet breaks two of T3's cases; suite 134/136 and the control falsifier stops asserting | real, reproduced by their prototype | **does not apply** | The implementation sets `EXPECTED_MUTATIONS` inside the fixtures' `try/finally`, so the ratchet is scoped to the fixture. 136/136. **And the control falsifier is NOT vacuous** — disabling the control check makes it fail (135/136), verified by mutation, which is precisely the property they warned could be lost |
| **H1** — `dev-process.md:155` + `roadmap:1347` assert `--compare`/`--verify-evidence` as mechanically enforced | real | **REAL AND LIVE** | **Fixed.** `dev-process.md` is `@`-included into every session; it would have described an enforcement CI no longer performs — the exact defect class this branch removes |
| **H2** — the module docstring is `--help` and says "ITS SUBJECT IS THE PLAN'S COPY" | real | **REAL AND LIVE** | **Fixed.** Rewritten per-mode; `--mutate` documented as what CI runs |
| **M1** — the control is a prologue, not an invariant | real | real | **Fixed.** Re-run after the sequence on the restored copy; an environmental red mid-run is no longer recordable as `caught` |
| **M3** — nothing in CI runs `--self-test` | real | real | **Fixed.** Added as a CI step |
| **Low** — CI comment says "shrinks below" but the ratchet is exact | real | real | **Fixed**, and it now names the duplicate-identity refusal too |
| **Low** — `--mutate` silently ignores `--compare`/`--evidence`/`--verify-evidence` | real | real | **Fixed** — refuses with rc=2; falsified |
| **Low** — `roadmap:1359` "Suite 44 → 121 cases", stale at 136 | real | real | **Fixed** by deleting the number, not correcting it: it has gone stale twice |
| **M2** — T6 S7's gate loop discards exit codes | real | n/a | The loop as executed captured `rc` on its own line. Their warning that `${PIPESTATUS[0]}` after an assignment does not work is correct and was independently hit on this branch |
| **(a)** `set(counts) - set(EXPECTED_MUTATIONS)` is live, not dead, and uncovered | correct | correct | Accepted, **not fixed** — a case would need a second script+manifest pair in a fixture. Filed below |
| **(b)** round-trip cannot lose data on this input | sound | sound | Matches the coordinator's own check |
| **(c)** no forward task dependency | sound | sound | — |

## Where they were right and I was not

Their §(d) correction to my own self-review: I claimed the *anchor missing or ambiguous* falsifier was
"T1 S2 (inherited, pinned)". **T1 S2 pins missing only**; ambiguity is covered solely by the
pre-existing `check()` cases. "Pinned" overstated it by half. Recorded rather than quietly corrected.

They also verified the rc=2 falsifier claim I had asserted — three existing cases drive `check()`
with `SUITE_TIMEOUT = 2` and route through `run_mutations` after T1. That one held.

## Residue, filed not fixed

- **The undeclared-target branch has no case.** Live guard, no test. Small, and it needs a
  two-script fixture.
- **Global Constraints in the plan says "four `<!-- file: … -->` strings"; there are six** — two added
  by the round-1 fix. A count in prose that nobody updates, in a document about exactly that failure.
- **The evidence-block deletion had no assertion of its own.** It completed (parser reports 0 blocks),
  but its regex was the least anchored of the three and a silent no-op would still have cleared the
  `> 1300` line guard.
