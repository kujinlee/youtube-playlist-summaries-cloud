---
name: a-report-format-is-a-contract
description: "FIRES-WHEN: changing the output format of a self-test or any machine-parsed report, or pointing a mutation manifest at a new file. The harness PARSES failure lines AND the success summary; a prettier format reads as '0 red cases'"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 026980a1-ac42-4306-9327-ecd78a7e933b
  modified: 2026-09-07T15:12:46.818Z
---

**The rule: a report format consumed by another program is a CONTRACT, not styling. When a file joins a harness, ask what the harness PARSES from its output, not just what it runs — and run the REAL harness before believing a coverage claim.**

`check-plan-code.py`'s contracts with a self-test (read the code by symbol; these are pointers, verified 2026-11-14):

| # | Contract | Failure if broken |
|---|---|---|
| 1 | a failing case prints a line that **starts with** `[FAIL] ` | red with an **empty** case list |
| 2 | that line contains **`: got `** — the name is `rsplit(": got ", 1)[0]` | red with a **plausibly WRONG** case name (`, got ` clears #1, and `rsplit` on an absent needle returns the whole string) |
| 3 | a green suite prints a **whole-line summary** matching `SUMMARY_LINE` (e.g. `N/M passed`), checked by `control_is_green` | every verdict withheld as NOT CHECKED — rc 0 cannot tell "green" from "never ran" |
| 4 | `self_test()` exits **exactly 1** on failure (`caught = rc == 1`) | a suite returning the failure COUNT records loud failures as survivors |

(⟳ Contract 3 was `rc == 0 and "passed" in out` until backlog #506, 2026-11-06, which replaced the substring with the whole-line `SUMMARY_LINE`; `PASS` never counted.)

**How to apply:** document the contract at the point of emission; when N things fail identically, the cause is one layer below all N, not N causes; **take each `expect` from the run, do not predict it.** A substitute harness inherits only the rules you noticed.

**Why:** "the guard did not fire" and "nothing could see the guard fire" produce the SAME output — a formatting choice is indistinguishable from a total coverage hole, and it masks real bugs underneath.

## History (condensed)

- **2026-08-30, backlog #71 (PR #180):** 12 mutations moved onto `scripts/page_markup.py` all reported `expect matched 0 red case(s)`. I wrote "stale replacement text" into the task as the root cause — true of 3 of 12. The real cause: `page_markup._self_test` printed a prettier multi-line block, so nothing was ever seen red. Once fixed, the harness named the right cases and 4 of my `expect` guesses were wrong.
- **2026-09-07, PRs #236/#238:** `check-handoff-path` printed `[FAIL] {name}: expected {e}, got {g}` (contract 2). Of the 20 guards then owing a manifest, **zero** conformed (19 needed the fix, 1 had no locatable FAIL printer). My mirror harness verified 5/5 attribution and CI went red on contract 3, which it never modelled; after the fix the real harness gave 12 files / 217 mutations / 0 survivors. Contract 4 came from `check-paid-caller-arrival` the same week ([[a-second-implementation-of-one-rule-drifts]]).

Related: [[separate-the-rule-from-the-fetch]], [[the-control-refuted-the-premise]], [[test-harness-can-launder-failures]], [[a-test-that-cannot-fail]].
