---
name: unit-coverage-does-not-compose
description: "FIRES-WHEN: two well-tested pieces are being joined — ⭐⭐ THREE ROUNDS, THREE TIMES: the gap was BETWEEN two well-tested pieces, never inside either. Mutate the CALL SITE, not only the functions — a change can be reverted where it takes effect while every unit case stays green"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b3d559c1-6b4c-49e1-81af-8ac588f0b7d8
  modified: 2026-09-21T15:33:38.911Z
---

**Distinct from [[a-test-that-cannot-fail]].** That one is a single check that cannot fail. This is
two checks that each CAN fail — every unit case kills a real mutation — while the **wiring between
them is asserted by nothing**. Unit coverage is not additive.

⭐ **THE TEST: mutate the CALL SITE, not only the functions.** If you can sever the call and the
suite stays green, the change can be reverted in a later refactor and nothing will say so.

## Measured on `scripts/check-closing-table.py`, three consecutive review rounds (2026-09-21)

| round | the two tested pieces | what nothing asserted |
|---|---|---|
| r7 **F6** | `mask_quotes` documented rule + its cases | no case contained a backslash, so the POSIX rule had no falsifier — a real input would have produced a **MISS** |
| r8 **R8-4** | `coalesce_injected` + its "records join the turn" case | the case filtered the opener out with `isinstance(x, str)` — the dict whose joining it was NAMED for |
| r9 **R9-1** | `turn_id_of` (6 cases, all killing real mutations) + `log_line` (13 cases) | **the caller.** `log_line(..., turn_id_of(judged)) → log_line(..., "-")` **SURVIVED at 151/151, rc=0** |

⭐⭐ **R9-1 IS THE SHARPEST, BECAUSE THE SURVIVING MUTATION *WAS THE ENTIRE CHANGE REVERTED* AT THE
ONLY PLACE IT TAKES EFFECT.** Every log line's id column becomes `-`, so
`cut -f4 | sort -u | wc -l` returns **1** for any log, forever — and the suite noticed nothing.
A second mutation to `session_id` also survived and is worse for a reader: the count stays
*plausible* and is wrong by the number of warned turns per session.

## Why I kept missing it, stated plainly

**"I verified one end-to-end case" is not coverage.** I ran the wiring by hand, saw the right uuid,
and moved on. A hand-check happens once; the suite is what runs again. If a manual verification is
load-bearing, it belongs IN the suite — and the end-to-end case usually already exists, needing only
one more assertion. Here the fix was: give the fixture's opener a known uuid and assert the 4th
field of the WRITTEN line equals it. Two lines.

⚠ **The reviewer found it by mutating; I could not have found it by reading**, and neither could any
amount of staring at the 13 new cases — they are all individually correct. See
[[dual-review-what-it-catches]].

## The cheap habit

After adding a function plus its cases, ask: **what single edit at the CALL SITE would undo this?**
Then write the case that dies when you make it, and add the mutation. If the change has one place
where it takes effect, that place needs a falsifier more than the function does.

See also [[fixing-a-premise-is-not-covering-the-branch]] (a premise repaired is not a branch
covered), [[assert-the-property-not-the-mechanism]], [[what-mutation-testing-proves]].
