# PR #299 — where the day actually went (measured, not recalled)

Captured 2026-09-14 for a later `/explain-topic`. Everything else about this branch is in the repo:
19 review documents under `docs/reviews/{claude,codex,coordinator}/record-review-topology-r1[1-7]-*`,
the dashboard entry for 2026-09-14, the PR #299 body, and backlog #114/#115/#116. **This file holds
only the numbers that were derived in conversation and committed nowhere.**

## Codex round wall-clock — prompt file written → review file written

Derived from file mtimes, not from memory. An earlier version of this table was WRONG (it claimed
r14 ≈ 34 min and r16 ≈ 40 min) because it was estimated from the chat timeline instead of measured;
the user caught the contradiction with the 30-minute budget.

| round | budget | actual | note |
|---|---|---|---|
| r11 | 900s | —    | no review file retained |
| r12 | 900s | 14 min | |
| r13 | 900s | —    | **timed out at 15 min**, `gate_ran: false`, gap declared. Dispatched without `--timeout`, so it used the 900s default — this is why r14 onward used 1800 |
| r14 | 1800s | 24 min | |
| r15 | 1800s | 10 min | |
| r16 | 1800s | 16 min | then the PROCESS hung 1h53m after writing output (backlog #116) |
| r17 | 1800s | 13 min | verification pass |

Honest range: **10–24 minutes**. One timeout, on the one run given half the budget.
⚠ `--timeout` is PER-ATTEMPT (`codex-review.py:666`), applied per candidate model. Only `gpt-5.5`
was ever tried, so per-attempt ≈ total here; with several candidates it would not be.

## The other wall-clock consumer: the mutation gate

`check-plan-code.py --mutate .` ran **nine times**, ~25 min each. Three came back refusing:

| run | entries | verdict |
|---|---|---|
| mutate4 | 626 | `NOT MEASURED — 625 of 626` — r15's fix rewrote `second_question`; anchors bind by TEXT |
| mutate7 | 629 | `CANNOT RUN — control red 138/139` — a new case read `schema-gates.yml`, which `HARNESS_TREE` did not stage |
| mutate8 | 629 | `NOT MEASURED — 628 of 629` — r16's fix rewrote another body AND renamed a case an entry named |
| mutate9 | 629 | **629 killed, 629 attributed, 0 survivors** |

So roughly **3¾ hours of mutation runs**, of which ~1¼ hours was re-running after a refusal.

## Where the day went, in round numbers

- 7 Codex rounds ≈ 1h20m of review wall-clock
- 6 Claude review halves (concurrent subagents, overlapped with the above)
- 9 mutation runs ≈ 3h45m
- 1 process hang ≈ 1h53m of pure waste — the coordinator polled `pgrep` instead of the output file
- Plus the fix/adjudicate/file cycles between rounds

## The shape worth explaining

Severity by round, and — the variable that actually mattered — **what each round was pointed at**:

| round | B/H/M/L | aimed at | found |
|---|---|---|---|
| r11 claude | 1/7/6/7 | the deliverable | a working evasion of the rule |
| r11 codex | 1/0/0/0 | the new manifests | they were unmeasurable |
| r12 | 0/1/1/1 | the instrument | one of two printers fixed |
| r13 | 0/1/2/1 | the instrument | the r12 repair could not fail |
| r14 | 0/1/2/1 | the deliverable | rename detection fail-open |
| r15 | 0/1/1/1 | the deliverable | `docs/` holds two live schema gates |
| r16 | 0/1/2/1 | the deliverable | the r15 anti-drift check compared a transcription to a transcription |
| r17 | 0/0/0/0 | verification | CONVERGED |

⭐ The coordinator initially read this as "severity falling, findings migrating away from the
deliverable" and predicted r15 would close it. **That was wrong** — the recorded correction is in
`record-review-topology-r15-coordinator.md`. The real variable was never the round number: rounds
aimed at the instrument found instrument defects; every round aimed at the deliverable found a
fail-open in it.
