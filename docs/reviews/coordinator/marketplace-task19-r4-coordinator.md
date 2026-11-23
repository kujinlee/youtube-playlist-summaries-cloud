# Round 4 — `marketplace-task19` — coordinator — two missing FILE_SHAPES leaves; both pass the BLOCKER test and are folded

```yaml
round: 4
fixes_nontrivial: false
subject: marketplace-task19
halves:
  codex: ran
  claude: "GAP: alternation"
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: false, component: shape, disposition: fixed}
  - {id: X2, severity: Minor, aim: deliverable, fix_induced: true, component: shape, disposition: fixed}
```

The Codex half reviewed 47dad1c2, which is the Phase 6 fold (`docs/reviews/architecture-review-2026-11-22-check-inventory-inputs.md`): [`codex/marketplace-task19-r4-codex.md`](../codex/marketplace-task19-r4-codex.md). Verdict NOT CONVERGED.

REVIEW GAP: claude — alternation

What held in round 4:
- 136 mutations and 296 cases, as pinned. Eight new mutations were killed by their named cases in a full clone.
- The `check-shipping-sets.py` edge pin moved from 360 to 361, which is not a loosening.

## The round cap: BLOCKER test (review-method.md §0 Q4c), per finding

| | 1. a concrete input gives a false green | 2. run, with the result quoted | 3. a local fix, no new mechanism | Result |
|---|---|---|---|---|
| **X1** | yes: a SHIP backed by `pass_conditions: {"1": "pass"}` alone, with conditions 2–5 unrecorded | yes: rc 0 | yes: one `FILE_SHAPES` leaf, since the plan's Task 14 record says the keys are exactly `"1".."5"` (plan line 774) | **BLOCKER, folded** |
| **X2** | yes: `recall: {"a": [], "b": {}}` gives rc 0, and an inventory without `scan` gives a row error instead of an input refusal | yes: rc 0 | yes: `FILE_SHAPES` entries for `recall.a`, `recall.b` and `scan` | **BLOCKER by the test, though graded MINOR, folded** |

## Is the design working?

Yes. Phase 6's stop condition says a finding fixed by one `FILE_SHAPES` line shows the design working, and a finding that needs a new hand-written check sends the work back to Phase 6.
- Both findings are missing leaves in the declared shape.
- Neither needs a new hand-written check.
- No traceback was found, and nothing reached the net.

That is the change of character Phase 6 predicted: from "a new input type escapes" to "a declared leaf is missing". So this is not thrashing, even though X2 is fix-induced. Its cause is an incomplete declaration, not a broken mechanism.

## Round 5

Round 5 is ONE half (Claude, by alternation), scoped to this fold, and it is the last round. All its findings are FILED. A BLOCKER in round 5 is also notified to the owner and HOLDS the PR.
