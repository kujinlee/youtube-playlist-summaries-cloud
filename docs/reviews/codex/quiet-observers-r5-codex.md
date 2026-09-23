# quiet-observers — round 5, Codex half

REVIEW GAP: claude — rounds alternate; the Claude half ran as round 4, and this round's
subject is that round's FOLD

<!-- codex-review: model=gpt-5.5 -->

Subject: `cdd8d589` on `quiet-stop-observers-wt`.

**Method.** I read `git show cdd8d589`, `docs/reviews/claude/quiet-observers-r4-claude.md`, the pause writer/reader code, and the Phase 6 rule in `docs/dev-process.md` / `docs/review-method.md`. I proved the controls green first:

```sh
python3 scripts/begin-plan.py --self-test
# 63/63 self-test cases passed
python3 scripts/check-plan-progress.py --self-test
# 43/43 self-test cases passed
python3 scripts/check-ci-watched.py --self-test
# 32/32 self-test cases passed
```

I also replayed the harness attribution rule over the 49 relevant mutation entries in a temp staged copy:

```sh
# begin-plan.json 18; check-plan-progress.json 17; check-ci-watched.json 14
# population 49
# controls green before and after
# run_mutations ok True
# measured entries 49 survivors []
# caught 49 attributed 49 unmeasured 0
```

## Findings
| # | Severity | Finding | Introduced by round 4's fold? |
|---|---|---|---|
| - | - | No findings. | No |

## The thrashing question, answered on its own terms

Yes: the literal thrashing condition has fired.

The rule I read is:

```sh
sed -n '100,112p' docs/dev-process.md
# It fires when two consecutive rounds carry findings caused by the previous round's own fix, in one component
```

The evidence matches the prompt’s record. Round 3 says its Medium was introduced by the round 2 fix:

```sh
rg -n "introduced by the round 2 fix" docs/reviews/codex/quiet-observers-r3-codex.md
# 63:So this is introduced by the round 2 fix.
```

Round 4 says findings 4 and 5 were introduced by r3’s fix, while its Blocking roots at the r2 fold and its two Mediums are older:

```sh
rg -n "From r3's fix|YES|No" docs/reviews/claude/quiet-observers-r4-claude.md
# 341:Blocking ... No
# 342:Medium ... No
# 343:Medium ... No
# 344:Low ... YES
# 345:Low ... YES
# 347:The literal answer is that it arms.
```

So: r3 carried an r2-fix defect; r4 carried r3-fix defects; all are in the `cmd_pause` / stamp-observer component. I agree the arming condition fired.

I do **not** think that means this fold is unsound. The secondary test is the important one: can redesign remove it? I attacked that through the actual state space.

Reader predicate:

```sh
# population 36 = 6 paused-line shapes x 6 stamp shapes
# colonless `paused`: paused? False -> BLOCK
# `paused:` empty value: paused? True -> paused branch
# duplicated `paused`: last-wins -> paused branch
# `paused` inside another value: paused? False -> BLOCK
```

Writer transition table for `cmd_pause`:

```sh
# unpaused/no-stamp        -> paused_unticked: 3
# unpaused/orphan-valid    -> paused_unticked: 3
# unpaused/orphan-invalid  -> paused_unticked: 3
# paused/valid             -> preserves old value
# paused/no-stamp          -> preserves absence
# paused/invalid           -> preserves invalid value
# paused/empty             -> preserves empty value
# paused/duplicate         -> strips to one paused/paused_unticked pair, last prior value
# colonless-paused/orphan  -> treated unpaused; recomputes 3
```

That is one rule, not three special cases: **if the sentinel is already paused under `parse_sentinel`, restating changes only `paused`; the stamp state is inherited exactly, including absence and invalid value. If it is not already paused, any old stamp is not a pause baseline and a new baseline is produced when possible.**

I found no fourth corner in `(paused present?, paused_unticked present?, value valid?) × (plan readable?, step counts)`. Missing/zero/all-ticked plans still split correctly: paused missing/zero is WARN not BLOCK, unpaused missing/zero is BLOCK, paused all-ticked is WARN and keeps the sentinel, unpaused all-ticked clears.

On the repo’s derived-value rule: r4’s second stamp input is enough. The relevant producer now has two distinct drives: 2 steps/1 done gives outstanding 1, and 4 steps/1 done gives outstanding 3. The manifest confirms the two ambient-constant holes are guarded:

```sh
# begin-plan.json 16: constant stamp -> exact second-input case
# begin-plan.json 17: DONE-count stamp -> exact second-input case
# begin-plan.json 18: stamp-less restatement invents baseline -> exact stamp-less case
```

The harness replay also confirms every one of the 49 relevant entries applies once and reddens exactly the named case: `caught 49 attributed 49 unmeasured 0`.

## Attacked, and found sound

**VERDICT: CONVERGED**

