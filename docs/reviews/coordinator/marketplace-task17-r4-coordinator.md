# Round 4 — `marketplace-task17` — coordinator — one BLOCKER fixed (a row named grounds it does not rest on), one fix-induced MAJOR in Task 19's rule filed

Codex reviewed 2a61db59 (the round 3 fold of plan Task 17, PR #616):
`docs/reviews/codex/marketplace-task17-r4-codex.md` (X1 BLOCKER, X2 MAJOR; NOT CONVERGED). Severity below uses the
header grammar's words: X1 is `Blocking`, X2 is `High`. The round cap governs (`docs/review-method.md` §0 Q4c): from
round 4 a finding is FILED unless it is a BLOCKER, so X1 is folded and X2 is filed.

REVIEW GAP: claude — alternation

## The findings

- **X1 (Blocking, not fix-induced) — fixed.** VERIFIED before folding: `sweep-red-alert`'s notes rest the C3 fail on
  two reasons, the record contract (RECORD_SCHEMA and RECORD_KEYS bind the runtime reader to our engine's record
  format) and the self-test's dependency on the engine. `sweep-red-alert:6:1` is the self-test's `git`, building a
  throwaway repository (line 471), and the notes themselves said "git (:6:1) is used only by the self-test"; it
  bears on neither reason. The class test found a second id the claim did not name: `sweep-red-alert:2:1` (line 496)
  runs the alert step's `run:` block, read from this repo's `ci.yml`, against a fake `gh`, and the notes gave it no
  reason either, only a location ("inside _self_test_body"). Both are removed; `rests_on` keeps
  `sweep-red-alert:4:1`, the self-test's importlib load of `check-plan-code.py`, which is the second reason. The ground
  sentence now says the record-contract reason is argued (the scan emitted no finding on the runtime path) and names
  the two ids as NOT grounds, with why. Not fix-induced: the three-id cite list is in `2a61db59^` (`"cites":
  ["sweep-red-alert:4:1", "sweep-red-alert:2:1", "sweep-red-alert:6:1"]`); the r3 fold only renamed the field.
- **The class search, every other row's `finding` grounds.** `mutation-sweep-job`: `:2:106`, `:2:107`, `:2:108`
  are each the C3 reason (a repo-relative call to this repo's script, at lines 1432, 1515 and 1628, inside the sweep's
  jobs). `velocity-docs`: `:2:1` (a cwd-relative `scripts/check-plan-code.py`) and `:4:1` (a doc-path into
  `docs/reviews/`) are each the C3 reason ("neither of which ships"). `check-plan-code` and `mutation-manifests` carry
  no `finding` ground; `coverage-verdict` is SHIP with none. Nothing else removed.
- **X2 (High, fix-induced) — filed, backlog #696 (f).** `{"kind": "finding", "ids": []}` passes every check the
  plan's refusal list states for Task 19 (nonempty `rests_on`, an allowed kind, no id absent from the row's own scan
  findings, and the measured-C2/C3 finding requirement). The typed-ground amendment in `2a61db59` introduced the gap.
  It is in the unbuilt guard's rule, not in any row (no row has an empty `ids`; the throwaway checker refuses one), so
  under the round cap it is filed for Task 19 to build with a self-test case.

## The Phase 6 stop condition — agreed, not triggered

The architecture review (`docs/reviews/coordinator/architecture-review-2026-11-22-marketplace-inventory-rows.md` §5)
says: "**The redesign has FAILED if** the next round carries a finding, caused by that fold, about what any of those
three rows cites." The three rows are `check-plan-code`, `coverage-verdict` and `mutation-manifests`. I agree with
Codex that it did not fire. X1 is about `sweep-red-alert`, not one of the three, and is not caused by the fold (the
cite list predates it, quoted above). X2 is caused by the fold but is about Task 19's plan rule, and no row has the
empty list it describes: the three rows' grounds are `spec` §3 + §2c, none, and `spec` §3 + `c5`, each resolved by the
throwaway checker (`OK: 6 rows, 15 comparisons, 0 errors`). In the decision scheme's terms the redesign bet's
narrower prediction held while its route's failure observation (the unit still carried a finding) was seen, so the
row is scored `continued` and the next route is logged as `defer` under the round cap, `split` skipped with a reason.

```yaml
round: 4
fixes_nontrivial: true
subject: marketplace-task17
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Blocking, aim: deliverable, fix_induced: false, component: marketplace-inventory-rows, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: true, component: marketplace-inventory-ground-rule, disposition: filed}
```
