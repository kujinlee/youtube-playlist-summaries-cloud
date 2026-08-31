# Runner mutation coverage (backlog #74) — round 1, coordinator half

**Subject:** branch `feat/mutation-coverage-for-the-runner`.
**Codex half:** [`runner-mutations-codex-r1.md`](runner-mutations-codex-r1.md), `gpt-5.5`.

**REVIEW GAP: claude — an independent subagent reviewer could not be dispatched under this session's
tool constraints; the coordinator ran the adversarial pass in its place.** Same caveat as the
HOME-redirect round: an author reviewing their own diff shares its blind spots.

---

## What discovery found before any reviewer ran

Adding the runner to the manifest is itself an instrument. Of 17 candidate mutations, **13 reddened
a case and 4 survived at 152/152.** Two of the four were my own bad mutations (semantically
equivalent); **three were real coverage gaps**, each guarding something a past review round had
bought:

| survivor | what it means |
|---|---|
| the after-sequence control | a tree going bad at mutation 17 was recorded as catches; nothing asserted the check |
| the duplicate-anchor refusal | two entries with the same anchors measure one thing twice, second reports phantom coverage |
| `check()`'s redirected-home mkdir | **the fix written for Codex in PR #181 the day before, shipped with no case** |

Each now has a case, and each case is proved load-bearing by the mutation that reddens it.

## Codex findings, adjudicated by reproducing them

| # | Sev | Verdict |
|---|---|---|
| 1 | High | **CONFIRMED, two bypasses.** `ESCAPE_EXEMPT` was a line-level text filter. `s = "# not-a-home-escape:"` — the marker inside a STRING LITERAL — dropped the whole physical line including a real `getpwuid` before it. And a marker written onto a line of live code exempted the live code. Both reproduced |
| 2 | Medium | **CONFIRMED, and it corrects me.** I excluded `caught = rc == 1` → `rc != 0` from the manifest as "semantically equivalent, since `if rc == 2: continue` leaves only {0,1}". That reasoning is wrong: the guard excludes 2 and nothing else, so a suite exiting **3** would be credited as caught under the mutant. It is real coverage, not an equivalent mutant |

### Fixes

1. `home_escapes` is now **tokenised**, not line-matched. The marker counts only as a genuine
   `COMMENT` token, and it exempts a line only when the route disappears once every `STRING` token
   is blanked — i.e. the route is string DATA, not code that runs. **An executable route cannot be
   exempted by anyone with any comment.** Source that will not tokenise is scanned raw with no
   exemptions honoured: unparseable is a reason to be stricter, never to pass.
2. `rc == 1` keeps its contract and gains two cases ("a suite exiting 3 is a SURVIVOR, not a catch"),
   so the mutation joins the manifest rather than being excused.

Four mutations were added for the fixes themselves, taking the manifest 17 → 21.

## What the harness did to ME during the round, which is the point

My `expect` for the string-literal mutation named the wrong case: the mutation turned out to skip
STRING tokens entirely and reddened **four other** cases instead. The tool refused it — *"matched 0
red case(s) — it was caught by something else"* — rather than recording a green. I then narrowed the
mutation to the behaviour I actually meant and **took the `expect` from the run**, which reported
exactly one case. That is the third time this project has been bitten by predicting an `expect`
rather than measuring it.

## Excluded, deliberately

None. The one candidate previously excluded as equivalent is now in the manifest (Codex #2). No
entry in the manifest is exempt from reddening its named case.

## Measurements

```
scripts/check-plan-code.py --self-test   158/158        (152 -> 158 over the round)
scripts/check-plan-code.py --mutate .    4 files, 94 mutations, 0 survivors
EXPECTED_MUTATIONS   gen-dashboard 47 + page_markup 14 + check-dashboard-entry 12
                     + check-plan-code 21 = 94
check-ratchet-contract / check-docs / check-anchors / check-test-counts /
check-producer-enumeration / page_markup --self-test          all OK
```

Codex independently applied all 17 original entries and confirmed each exited red with its exact
named case, and found no self-mutation where the orchestrator's judgement was corrupted rather than
the target's behaviour.

## Carried, stated not fixed

⚠ **`--mutate .` runs 13s → 3m13s**, because 21 of the 94 mutations run a 158-case suite that itself
spawns suites. Real and measured. Not addressed in this branch; if CI time becomes a problem the
lever is parallelising the mutation loop, not dropping coverage.

`home_escapes` remains static, so a home path assembled at runtime still slips past — said in its
docstring rather than left to be discovered.
