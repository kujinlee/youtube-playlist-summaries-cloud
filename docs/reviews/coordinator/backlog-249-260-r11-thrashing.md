# Round 11 — THRASHING OR PROSE FLOOR? The arming question, answered by the documented TEST

⟳ **REWRITTEN 2026-10-13, during the Phase 6 review this document armed.** The first version led
with the symptom — *"two consecutive folds, each producing Highs about the previous fold"* — and
`docs/review-method.md:137` says exactly not to: *"Apply the single test at `:173`, **never the
symptom list**; using the list as a checklist produced a measured false escalation on 2026-08-14."*
Worse, the symptom cannot discriminate on its own, because §Iterative Re-Review (`:495`) states
fix-caused findings are the EXPECTED shape of re-review: *"Fixes routinely introduce new defects or
expose deeper ones that the first pass could not see"*, and *"A Blocking fix is itself a new,
unreviewed design — it must be re-reviewed."* A document that armed an architecture review on the
documented normal of re-review would have been wrong even with the right conclusion.

## The test, applied per finding — `review-method.md:200`

> ### Can a redesign remove it?

With the discriminator at `:195`: **mechanism** defects (the rule cannot be satisfied, two
requirements contradict) → REDESIGN; **branch-coverage** defects (*"the rule doesn't say what
happens in case X"*, where X is a branch the rule governs but does not own) → FIX + an
exhaustiveness pass.

| finding | kind | can a redesign remove it? | verdict |
|---|---|---|---|
| **r11 Claude H1** — `exception_heading` named the LAST traceback block as the killer; the premise is FALSE at interpreter shutdown, and the flooding composite left the real exception nowhere in the report | **MECHANISM** — the rule's premise is untrue, so no amount of case-covering satisfies it | **YES.** Stop attributing: name every heading, claim none. The finding cannot be stated about a rule that makes no causal claim | REDESIGN |
| **Phase 6 F1** — `attributed: True` recorded over `fails: []`, a field contradicting its own definition, when `expect` is omitted and the suite crashed | **MECHANISM** — two requirements contradict | **YES.** One mandatory clause removes the state entirely | REDESIGN |
| **r11 Codex H1** — a multi-line message pushes the heading out of the 400-char window | branch-coverage — the window rule did not say what happens for case X | NO; a reshaped window still has a budget | FIX + exhaustiveness |
| **r11 Claude H2** — two of three worlds asserted by no case | branch-coverage — the arms exist and are unasserted | NO; any message with worlds needs a case per world | FIX + exhaustiveness (done: a case and a mutation per world) |
| r11 Claude M1, Codex L1/L2, Claude L1/L2/L3 | figure and prose corrections | NO | FIX |

## Verdict: ARCHITECTURE REVIEW is owed, on the MECHANISM findings only

Two mechanism defects, in one component, whose shape a redesign dissolves. That is the test passing,
not the symptom list firing. The branch-coverage findings in the same round are **not** evidence for
it and are recorded above so a later reader does not count them as such.

**Component:** `scripts/check-plan-code.py` — the child-verdict path: `caught = rc == 1`, the
`expect` attribution clause, and the `if not fails` branch.

**The one root cause both mechanism findings share:** the harness asserts a cause it cannot read
from a child's text. `caught = rc == 1` claimed "a case failed" where a traceback also exits 1; the
message claimed "a report-format defect in `<file>`"; the fold claimed "the child DIED with X". Each
fix MOVED the claim, which is why each produced the next finding.

⭐ **And the repair already exists in this file, for the other side of zero.** `control_is_green`
(`:376`) is `rc == 0 and "passed" in out` — two clauses, no opt-out — and its docstring records the
reasoning on 2026-09-03: *"the exit code alone cannot tell "green" from "never ran""*. The rc==1
side has the same second clause as `expect`, but **OPT-IN**, because the field is optional. F1 is
what the optionality costs. So the redesign is not an invention: it is making one existing clause
mandatory, which is what the rc==0 side already does.

## Not a prose floor

A prose floor is findings whose character holds while severity drifts — the 2026-08-28 measurement
where Blocking totals ran 4→5→4 over improving prose. These are measured behaviours of delivered
code, each with a reproduction, each changing the shipped artifact: a false attribution over four
real children, an unfalsifiable arm proved by mutating a 260-case mirror, a survivor found by CI,
and a false green reproduced as a 2×2.

## Consequence

Phase 6 was sequenced by the owner on 2026-10-13 and ran; its findings are in
`docs/reviews/architecture-review-2026-10-13.md`.

⛔ **NOT CONVERGED.** Round 11: Codex 1 High + 2 Medium + 2 Low; Claude 2 High + 1 Medium + 3 Low.
Zero of two consecutive clean rounds; zero in eleven.
