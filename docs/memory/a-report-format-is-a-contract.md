---
name: a-report-format-is-a-contract
description: "FIRES-WHEN: changing the output format of a self-test or any machine-parsed report — A self-test's failure-line SHAPE is parsed by the mutation harness; a prettier format made all 12 mutations report \\\"0 red cases\\\" — indistinguishable from a total coverage hole, and it masked 3 real bugs underneath"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 026980a1-ac42-4306-9327-ecd78a7e933b
  modified: 2026-09-07T15:12:46.818Z
---

**MEASURED 2026-08-30 (backlog #71, PR #180).** I moved 12 mutations onto `scripts/page_markup.py`.
Every one reported `expect matched 0 red case(s)`. I diagnosed it as stale replacement text still
naming `gen-dashboard` symbols, **wrote that into the task description as the root cause, and was
wrong** — it was true of 3 of the 12.

The real cause: `check-plan-code.py:495` finds which case a mutation reddened by reading lines that
**start with `[FAIL] `** and splitting on the LAST `": got "`. `page_markup._self_test` printed
failures as a prettier multi-line block. **Nothing was ever seen as red.**

**Why:** *"the guard did not fire"* and *"nothing could see the guard fire"* produce the SAME output.
A formatting choice was indistinguishable from a total coverage hole — and it *masked* the three
genuine edit bugs, so fixing what I thought was wrong would have left a red run with no signal.

**How to apply:** when a new file joins an existing harness, ask **what does the harness PARSE from
its output**, not just what it runs. A report format consumed by another program is a contract, not
styling — document it as one at the point of emission. And when N things fail identically, the cause
is one layer down from all N, not N causes; my per-item diagnosis was a category error.

## ⭐⭐ THERE ARE **THREE** CONTRACTS, NOT ONE — and the third is on the SUCCESS side (2026-09-07)

Paying down the R4 manifest debt (PRs #236/#238) hit all three in two guards. `check-plan-code.py`:

| # | Contract | Read at | Failure if broken |
|---|---|---|---|
| 1 | the line must **start with** `[FAIL] ` | attribution | red, **empty** case list |
| 2 | it must contain **`: got `** — `rsplit(": got ", 1)[0]` | attribution | red, **plausibly WRONG** case name |
| 3 | a green suite must print **`passed`** — `control_is_green` is literally `rc == 0 and "passed" in out` | control | **every verdict withheld** as NOT CHECKED |

**(2) is the dangerous one and it is dangerous by being CLOSE.** `check-handoff-path` printed
`[FAIL] {name}: expected {e}, got {g}` — `, got `, not `: got `. It CLEARS the `startswith` filter, so
it does not fail emptily; **`rsplit` on an absent needle returns the WHOLE string**, yielding
`'…the reversion this exists to catch: expected 1, got 0'` — an attribution no `expect` can match,
wearing the shape of a real one.

**(3) exists because rc 0 cannot tell "green" from "never ran"** — a script with no `__main__` exits 0
in silence. `PASS` is not `passed`; the harness refused, correctly, and said so.

⚠ **MEASURED POPULATION, 2026-09-07: of the 20 guards still owing a manifest, ZERO conform.** 19 need
the fix, 1 has no locatable FAIL printer. This is not a tail risk — it is every remaining item, and
each contract stays latent until a manifest first points at that file.

⛔ **AND THE LESSON ABOUT MY OWN VERIFICATION, which is the reusable part.** I wrote a harness that
mirrored the *attribution* parse exactly and verified 5/5 attributed — then CI went red on (3),
because my harness never modelled the *control predicate*. **A substitute for a checker inherits only
the rules you noticed.** Per the lighter-verification default I had skipped the local `--mutate .`;
CI earned its keep. Run the REAL harness before believing a coverage claim — re-running it locally
after the fix gave 12 files / 217 mutations / 0 survivors. See
[[a-second-implementation-of-one-rule-drifts]] and [[separate-the-rule-from-the-fetch]].

⟳ Second half, same run: once the harness could see red cases it **named the right ones itself**, and
4 of my `expect` guesses were wrong (the entity-trim mutation edits the line inside `scan`, so the
direct `trim_url_tail` cases stay green and the scan-level case is the guard). **Take the expect from
the run; do not predict it.** Related: [[the-control-refuted-the-premise]],
[[test-harness-can-launder-failures]], [[a-test-that-cannot-fail]].
