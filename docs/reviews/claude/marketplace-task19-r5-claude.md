Reviewed head: f97d7245ab2bfdade05b1782d361b44713dd109f

# Round 5: `marketplace-task19`, Claude half, the last round, scoped to the round 4 fold (`c07db24f..f97d7245`)

```yaml
round: 5
subject: marketplace-task19
half: claude
scope: git diff c07db24f..f97d7245 (scripts/check-inventory.py, scripts/mutations/check-inventory.json, scripts/mutations/expected_mutations.py)
findings:
  - {id: C1, severity: Nit, fix_induced: true, component: shape, blocker: false}
  - {id: C2, severity: Minor, fix_induced: true, component: mutations, blocker: false}
```

All the work was done in a full `git clone` of the branch at f97d7245, with `node_modules` linked in, under
`scratchpad/task19/r5-claude-work/clone`. Nothing ran in /tmp. The attack worlds are copies of round 3's
Task-20-shaped tree `r3-claude-work/t20a` (rc 0 with the folded script), and each world has one input edited
(`r5-claude-work/attack.py`). Each mutation was applied to the clone's script, and its self-test was read for the
named case (`r5-claude-work/mut.py`).

## What held

### 1. Over-refusal: none found

- **The vocabularies match the plan, word for word.**
  - Plan line 854 (Task 18): `"recall": {"a": true|false|"CANNOT RUN", "b": "pass"|"fail"|"unanswered"}`.
    `RECALL_A = (True, False, "CANNOT RUN")` and `RECALL_B = ("pass", "fail", "unanswered")` match it.
  - Plan line 774 (Task 14 Step 6): `"pass_conditions": {"1".."5": "pass"|"fail"|"argued"|"CANNOT RUN"}`.
    `PASS_CONDITIONS` and `PASS_VALUES` match it.
  - Plan lines 759 and 768 to 770 cover the two Task 14 shortcuts. A skill half that is CANNOT RUN records `argued`, and
    condition 2 is recorded `not scored`, which makes it `argued`. Both still write all five keys with in-vocabulary
    values. So no legitimate Task 14 output carries fewer than five conditions.
- **The live inputs are all accepted.**
  - The live sidecar has 33 entries, each with exactly the keys `1` to `5`. Its values are argued 117, pass 27 and
    fail 21, with nothing outside the vocabulary.
  - The live inventory has `scan` = `docs/marketplace/scan-2026-11-17.json` and `recall` = `{a: false, b: "unanswered"}`.
  - The live tree is rc 1 with exactly 34 `[missing]` errors and nothing else, as the coordinator recorded.
  - `t20a` and `t20b` are each rc 0.
- **Every legitimate value is rc 0, and each one was run.** `recall.a` of true, false and `"CANNOT RUN"` are each
  rc 0, and so are `recall.b` of pass, fail and unanswered.
- **All five conditions `argued`, or all `CANNOT RUN`, is readable input.** It is rc 1 from the existing
  `[ground-experiment]` rule, because that row's experiment ground needs a `fail`. It is not refused as input.

### 2. Under-refusal: none found in what the fold declares

Each of these was run, and each is rc 2 with a CANNOT RUN that names the leaf:

- **pass_conditions keys:**
  - `{"1.0", "2".."5"}` and `{" 1", "2".."5"}`: "pass_conditions.1 is missing";
  - `{}`: rc 2;
  - absent: rc 2;
  - a list of five: "is a list of 5, not an object with exactly 1, 2, 3, 4, 5";
  - the five keys plus `"0"`: "['0'] is a key it may not have";
  - a raw duplicate `"1"` key: the repeated-key rule.
- **pass_conditions values:** `null`, `true`, `"Pass"` and `"cannot run"`.
- **recall.a:** `"true"`, `"false"`, `0`, `1.0`, `null` and `"cannot run"`. Here `_one_of` is type-strict: 0 is not
  False and 1.0 is not True.
- **recall.b:** `null`, `true`, `"PASS"`, `"unanswered "` (with a trailing space) and `"CANNOT RUN"`.
- **recall:** `null`.
- **scan:** `null`, `0` and `{}`.

The remaining cases are rc 1 by design:

- `scan` of `""`, an absolute path or a bare filename is the `[scan]` row error, rc 1, never rc 0.
- The only rc 0 among the wrong inputs is an extra key in `recall` (`"c": [1]`). `recall` is an open `_obj`, and no
  rule reads another key, so nothing it carries can change a verdict. That is by design, not a finding.
- `_exactly` is strict on keys because JSON keys are always strings, and the closed check compares them against the
  string literals `"1"` to `"5"`. It is strict on values through `_one_of`'s type-and-value match.

### 3. The dropped mutation's behaviour is still guarded, but not in the way the fold describes it (C2)

### 4. The pin is honest

- `scripts/mutations/check-inventory.json` has 144 entries, and the pin is 144.
- All 11 mutations the fold added or re-anchored were applied in the clone. Each one's anchor occurs exactly once,
  and each is killed by the case it names, with these failure counts:

| Mutation | Cases failed |
|---|---|
| non-object pass_conditions reach .values | 8 |
| a non-string pass condition is accepted | 3 |
| a non-object recall is accepted | 7 |
| sidecar pass_conditions of any keys | 3 |
| a closed object accepts a key it may not have | 1 |
| recall.a of any type | 2 |
| recall.a is not declared | 3 |
| recall.b of any type | 2 |
| recall.b is not declared | 3 |
| an inventory with no scan is a row error | 2 |
| an inventory scan of any type | 1 |

- **A note on the brief:** it says the pin went "from 145 to 144". The diff moves it from **136 to 144**: 8 new
  mutations, plus 3 re-anchored in place. A 145th mutation was measured and left out, so it was never pinned. The
  number is consistent, and only the brief's wording is off.

## Findings

### C1: Nit. The `recall.a` refusal spells JSON's booleans the way Python does

- **fix_induced:** true. It is new with `RECALL_A`.
- **Input:** `inventory.json` with `"recall": {"a": "true", "b": "unanswered"}`.
- **Observed:** rc 2, `CANNOT RUN: inventory.json: .recall.a is 'true', not one of True, False, CANNOT RUN.`
- **Expected:** the same refusal, with the vocabulary in the file's own syntax (`true, false, "CANNOT RUN"`). An
  author who follows the message literally and writes `"True"` is refused again.
- **The BLOCKER tests:**
  1. There is no false green, lost data or security hole. The input is refused, and only the wording is wrong.
  2. It was run, and the result is quoted above.
  3. It has a local fix: print the `_one_of` members through `json.dumps`.
- **Not a BLOCKER**, because it fails test 1.

### C2: Minor. "Two attributed mutations still cover it" is imprecise

- **fix_induced:** true. The claim is in the fold's coordinator note and the pin comment.
- **Input:** the dropped mutation, `PASS_CONDITIONS = ("1", "2", "3", "4")`.
- **Observed:** rc 1, with 267/311 cases passing and 44 failing.
  - The case that names this behaviour, "sidecar pass_conditions with no condition 5 exits 2", is **not** among the
    44. It still passes under the mutation, because the bad-input world's other sidecar entries (`ep2`, `lib`) keep
    key `"5"`, which is now an extra key, so the world is still rc 2 for a different reason.
  - The two mutations the fold cites ("any keys" and "closed accepts an extra key") each alter a different line, and
    neither touches the key tuple's contents.
- **Expected:** the behaviour is guarded, because every clean fixture case goes red. The fixtures' five keys are
  independent literals and are not derived from `PASS_CONDITIONS`, so the guard is real. But the guard is the 44
  unattributed clean cases, not the two cited mutations. A future edit that derives the fixtures from
  `PASS_CONDITIONS` (for example `dict.fromkeys(PASS_CONDITIONS, ...)`) would silently remove it, and no attributed
  mutation would notice.
- **The BLOCKER tests:**
  1. There is no false green today. The mutation is killed.
  2. It was run, and the result is quoted above.
  3. It has a local fix: reword the pin comment, or keep the fixtures' keys literal with a one-line comment saying why.
- **Not a BLOCKER**, because it fails test 1.

No BLOCKER. Both findings are FILED, since this is the round cap's last round.

VERDICT: CONVERGED
