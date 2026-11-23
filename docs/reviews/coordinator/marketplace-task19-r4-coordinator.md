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

## The fold

- **X1.** **Fixed in 7d638b4e.** A sidecar entry's `pass_conditions` is `_exactly` the keys `PASS_CONDITIONS` (`"1"` to `"5"`, plan Task 14 Step 6), each `_one_of(*PASS_VALUES)`. `_exactly` is `_obj` closed, the walker's sixth shape kind, so an extra key is refused too. No hand-written check was added. The evidence:
  - Codex's reproducer, `{"1": "pass"}` behind a SHIP, is now rc 2 where it was rc 0. Condition 5 left out and an extra condition 6 are rc 2 too. All three cases were red before the fix: `redbefore.txt`, 300/311.
  - The adjacent negative is all five conditions of another value, which is readable (rc 0).
  - No committed sidecar carries fewer than five. All 33 entries of `docs/marketplace/experiment-tier-a.json` have exactly `"1"` to `"5"`, and no other file under `docs/marketplace/` has `pass_conditions`. The self-test's fixture sidecar had abbreviated entries of one to three conditions. They now carry all five, and each entry keeps its meaning: whether it has a `fail` is unchanged.
- **X2.** **Fixed in 7d638b4e.** `inventory.json` declares `scan` as `_STR`, and `recall` as `_obj(a=_one_of(*RECALL_A), b=_one_of(*RECALL_B))`, using plan Task 18's vocabularies: `true`, `false` and `"CANNOT RUN"` for `a`; `pass`, `fail` and `unanswered` for `b`. The evidence:
  - `recall: {"a": [], "b": {}}` is now rc 2 where it was rc 0, and so are `recall.a` of `1`, `recall.b` of `Pass`, and either key absent.
  - An inventory with no `scan`, or with a list as its `scan`, is rc 2 where it was a row error.
  - The adjacent negatives: `recall.a` of `"CANNOT RUN"` and `recall.b` of `fail` are readable (rc 0), and a `scan` naming another file is the `[scan]` row error (rc 1).
- **The class check, every field a rule reads in every input file.** Each is now declared in `FILE_SHAPES`:
  - `components.json`: `packages.*.channel`, and `components[].id`, `effort`, `roles`, `phase` and `package`;
  - `shipping-sets.json`: `packages.*.components`, whose keys are what is read;
  - the scan: `components.*.findings[].id`;
  - the sidecar: `components.*.exercised`, `operation_ok`, `scenario` and `pass_conditions`;
  - `inventory.json`: `scan`, `recall.a`, `recall.b` and `rows`. Each row is held to `ROW_SCHEMA` by `row_errors`, as row errors at rc 1, by design.
  - No other field of an input file is read.
- **Gates on 7d638b4e, and on d42bf5fc for the mutations:**
  - The self-test passes 311 of 311, up from 296: 11 refusals, each red before the fix, and 4 adjacent negatives.
  - Mutations, in a full `git clone` at d42bf5fc: 144 of 144 killed, each attributed to the case it names, with 0 survivors. That is up from 136: 8 new, and 3 re-anchored on the new declarations. A ninth mutation was measured at 7d638b4e and left out: `PASS_CONDITIONS` cut to four keys. It is killed, but by 44 clean cases at once, so it cannot be attributed. The behaviour it would guard is held by "pass_conditions of any keys" and "a closed object accepts a key it may not have", each killed by its named case.
  - The live tree is rc 1 with exactly 34 `[missing]` errors. Both Task-20-shaped trees (`r3-claude-work/t20a`, `t20b`) are rc 0.
  - attack.py's `head` variant is the pre-Phase-6 baseline, so it was run with the folded script as variant `fold4` instead. That gives 0 TRACEBACK, 0 FAIL-OPEN and 0 NET.
    - There are 3 WRONG. One is P9 (rc 2, the intended refusal, as in round 3). The other two are the corpus's P2 controls, whose `backed()` fixture records only conditions 1 and 2, which X1 now refuses as intended.
    - With `backed()` given all five conditions, and the round-4 reproducers added (`fold4-work/attack-fold4.py`): 69 cases, 68 ok, and the 1 WRONG is P9.
  - check-docs, check-fixture-git-isolation and check-fixture-variation all pass., and check-selftest-counts passes (97 scripts, rc 0).

## Is the design working?

Yes. Phase 6's stop condition says a finding fixed by one `FILE_SHAPES` line shows the design working, and a finding that needs a new hand-written check sends the work back to Phase 6.
- Both findings are missing leaves in the declared shape.
- Neither needs a new hand-written check.
- No traceback was found, and nothing reached the net.

That is the change of character Phase 6 predicted: from "a new input type escapes" to "a declared leaf is missing". So this is not thrashing, even though X2 is fix-induced. Its cause is an incomplete declaration, not a broken mechanism.

## Round 5

Round 5 is ONE half (Claude, by alternation), scoped to this fold, and it is the last round. All its findings are FILED. A BLOCKER in round 5 is also notified to the owner and HOLDS the PR.
