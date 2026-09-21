# closing-table — round 3, Claude half

**REVIEW GAP: the independent Claude half could not be dispatched (third round running).** Same
constraint as r1 and r2 — this session cannot spawn subagents. Coordinator self-review only.

## r3's verdict: NOT CONVERGED. Two Highs were real defects in r2's own fixes.

| # | Grade | Finding | Disposition |
|---|---|---|---|
| r3-B1 | Blocking | *"clean-copy mutation evidence not reproducible"* — `git archive HEAD` omits `node_modules`, so `stage_tree()` refuses and the run reports NOT MEASURED | ⚠ **NOT a defect in the guard — a defect in the verification command I supplied.** The harness-backed verdict exists: CI's `verify` job on `3b5e4a18` ran `--mutate .` and the step **"Mutation manifest against the delivered scripts" reported success**. Evidence below |
| r3-H1 | High | `mask_quotes` treated any matching quote byte as a closer, ignoring backslash escapes | fixed — both directions had defects |
| r3-H2 | High | fence pairing ignored fence CHARACTER and LENGTH, so a stray ` ``` ` was "closed" by a later `~~~` and a real table between them was hidden | fixed — pairing now requires the same character at the same length or longer |
| r3-M1 | Medium | the borrowed-rule semantic probe had no mutation | fixed — a case now stands up a FAKE `check-banner-armed.py` whose `judged_window` returns the live turn, and asserts the loader refuses it |

⭐ **Both Highs were introduced BY r2's fixes** — quote masking and fence pairing are both things r2
asked for and r3 found broken. That is the third instance on this branch of *the fix creates the next
round's finding*, and it is exactly why `check-review-recorded` refuses to let a branch merge on a
review that never saw the code being shipped.

## The r3-H1 defect is worth stating precisely, because it failed in BOTH directions

One omission — not handling `\` inside a double-quoted span — produced a false positive and a false
negative at once:

    echo "a \"; git push"            -> ['a push']    FALSE ACT (the escaped quote "ended" the span)
    git commit -m "a \" --dry-run"   -> []            MISSED (the flag leaked out of the message)

Measured after the fix: `[]` and `['a commit']` respectively.

## On r3-B1, stated plainly rather than argued away

Codex is right that it could not reproduce a clean-copy measurement, and right about why. It is
wrong only in the implication that no harness-backed verdict exists. The authoritative run is CI's,
because CI is the environment the harness was built for — `stage_tree()` needs `node_modules`, which
`git archive` does not carry. My own scoped verifier is a stand-in and r2 already measured that it
was **weaker than the gate**; it is not offered as the evidence here. CI is.

## Verification

| check | result |
|---|---|
| Self-test | ✅ **99/99** |
| Mutations kill via the case each NAMES | ✅ **26/26** — 0 survivors, 0 unattributable, 0 orphaned |
| Anchors distinct | ✅ asserted before write |
| **CI `--mutate .` on `3b5e4a18`** | ✅ **success** — the harness-backed verdict r3 asked for |
| CI `verify` overall on `3b5e4a18` | ❌ failed — **only** `check-review-recorded`: r2 never saw r2's fixes. That is this round |
| CI `schema-gates` | ✅ pass |
| ⭐ **Live smoke on the REAL session transcript** | ✅ ran against 2,020 real records: **fires exactly once in six turns**, on the turn that merged PR #324 and closed with prose — a true positive found in the wild |
| `check-fixture-variation` / `check-selftest-counts` / `check-ratchet-contract` / `check-docs` | ✅ all rc=0 |
| An independent Claude reviewer ran | ❌ **NO** — see REVIEW GAP |

## ⭐ What the live smoke found that no fixture could

Every test before r3 used synthetic transcripts. Running the guard against this session's real
transcript exposed a defect none of them could: a `<task-notification>` record is `type: "user"`
with no `isMeta`, so the borrowed boundary rule calls it a NEW TURN. **A background job finishing
mid-turn splits that turn between the act and the report**, and the fragment carrying the `git push`
has no table — a false warning, in a session that receives such notifications constantly.

Fixed by `coalesce_injected`, which folds an injected window back into the turn it interrupted.
⚠ Deliberately NOT by changing the borrowed rule: that rule answers *where is a boundary*, this one
answers *was the boundary a PERSON*. Two different questions, composed — not one question answered
twice.
