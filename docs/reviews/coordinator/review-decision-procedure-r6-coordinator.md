# review-decision-procedure — round 6, coordinator adjudication

```yaml
round: 6
fixes_nontrivial: true
subject: review-decision-procedure
halves:
  codex: ran
  claude: "GAP: this session spawns no subagents"
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: false, component: card-tool-drift, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: parse-header, disposition: fixed}
  - {id: L1, severity: Low, aim: instrument, fix_induced: true, component: exit-codes, disposition: fixed}
```

* Codex: `docs/reviews/codex/review-decision-procedure-r6-codex.md` (`gpt-5.5`) —
  **0 Blocking, 1 High, 1 Medium, 1 Low. NOT CONVERGED.**
* **REVIEW GAP: claude** — as rounds 1–5.

## H1 — the card stated a rule the tool could not enforce

**ACCEPTED AND FIXED.** Q4 listed *"non-trivial fixes → CONTINUE"*, and `converged()` had no
way to observe that. Codex drove two Low, instrument-only, full-loop rounds with
`tree_reviewed=True` and got **STOP** — *"the card says continue and the tool says stop."*

⛔ **This is the exact defect the branch exists to remove**, committed inside the artifact
that removes it: a rule written where it cannot be enforced. Not fix-induced — surviving
drift from the card's first draft.

**Fixed** by making it a recorded judgement rather than a remembered one:
`fixes_nontrivial: true|false` joins the round header, is **required** (a missing value
raises), and `converged()` refuses to converge on a round whose fixes were non-trivial. The
card's row now says the tool enforces it. Backfilled `true` on rounds 1–5, which is what
they were.

## M1 — braces in ordinary gap prose raised a false CANNOT RUN

**ACCEPTED AND FIXED.** The flow-mapping scan covered the whole YAML body, so a legitimate
`halves.claude: "GAP: connector returned {disabled}"` counted as a finding and tripped the
parity check. **A false CANNOT RUN from human prose**, and a guard that refuses valid input
is a guard that gets switched off. Fix-induced — the parity hardening of r2 made the
whole-body scan user-visible. The scan is now confined to the `findings:` span.

## L1 — the exit-code mapping was pinned by nothing

**ACCEPTED AND FIXED.** `CANNOT_RUN → 2` lived inline in `main()`; the cases asserted the
decision *string* and never the process-facing code. Extracted to a pure `exit_code_for()`
with four cases.

## ⛔ A MUTATION SCORED "0 CASES RED" WHILE GENUINELY BREAKING THE PARSER

The strongest finding of this round came from the controls, not the reviewer. The
whole-body-scan mutation reported **0 red** — and the cause was not a missing case. **The
case RAISED**, which kills the suite before it prints anything, and the harness counts
`[FAIL]` lines. A traceback and a clean run are indistinguishable to a grep.

⚠ **Third instance of one shape on this branch**: r4's classifier coupling crashed
anonymously; r3's staged-tree harness produced a traceback counted as a pass; now a case
itself. Fixed with `_try()`, which converts a raise into a **named** value so the case fails
by name. **All ten mutations now go red**, over a green 61/61 control:

```
thrashing unions          3     classifier ignored       11     nontrivial ignored    1
convergence ignores aim   1     absent findings key       1     whole-body scan       1
one-round bar             1     adjacency by position     2     CANNOT_RUN exit lost  1
tree question dropped     1
```

## ⚠ A SELF-INFLICTED SETBACK, RECORDED

Applying `_try` with a broad regex mangled the file; `git checkout` to recover discarded
**every r6 fix**, not just the bad edit, and they were reapplied by hand. The manifest and
the pins were in other files and survived, so the tree was briefly inconsistent. **A revert
is not a surgical instrument**, and a regex over source is the reason it was needed.

## Verified on this tree

```
check-review-decision --self-test  61/61
manifest 10 entries — every anchor unique, every `expect` a live case name
check-plan-code · check-fixture-variation · check-selftest-counts ·
check-ratchet-contract · check-docs · check-anchors · check-review-rounds   all rc=0
```

**NOT CONVERGED.** H1's and M1's repairs are unreviewed code, this round's fixes were
non-trivial — which now blocks convergence by the rule H1 added — and the branch is
full-loop.
