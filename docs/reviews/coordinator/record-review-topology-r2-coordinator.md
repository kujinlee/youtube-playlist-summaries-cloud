# record-review-topology — round 2, coordinator adjudication

**REVIEW GAP:** claude — not invoked; built by a worker fork that cannot spawn subagents. Both
rounds are Codex-only and **the Claude half is owed before merge**. This branch's own evidence
table is the argument for why that matters: three rounds, zero overlapping findings between halves.

⚠ **Alternating was not possible here, and that is a deviation from the protocol this branch
writes down.** Step 4 says rounds 2+ go to the half that did NOT author the fix. r2 went to Codex
again, so the reviewer was grading its own round-1 findings. It still found three defects in the
repairs — but a Claude half reviewing the same deltas is exactly the thing the measured table says
would have found *different* ones.

## Round 2 — Codex, `gpt-5.5`, aimed at r1's FIXES

`docs/reviews/codex/record-review-topology-r2-codex.md` · verdict
`docs/reviews/verdicts/record-review-topology-r2-codex.verdict.json` (`gate_ran: true`).
Verdict line: **NOT CONVERGED**. 1 Blocking, 1 High, 1 Medium — **all three inside the r1 repairs**,
which is the finding this branch exists to make mechanical.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | **Blocking** | The content comparison ignored MODE. Same bytes, newly executable, credited as reviewed — reproduced in a scratch repo | **FIXED** — the recorded and compared unit is the git TREE ENTRY, `"<mode> <blob>"`, via `git ls-tree` and a throwaway index |
| 2 | High | `declared_gap` accepted a gap naming EITHER half, so `REVIEW GAP: claude — not invoked` cleared a missing **Codex** verdict — one absence excusing a different one | **FIXED** — `gap_names_codex` reads the WHO; the rule moved into the pure `first_codex_gap`, driven by cases holding the real parser |
| 3 | Medium | `hash-object` recorded a symlink as the hash of its TARGET's contents (git stores the link text), and `git diff HEAD` omitted untracked files — both **false failures on the careful path** | **FIXED** — `read-tree` + `add -A` into a `GIT_INDEX_FILE` throwaway index, then `diff-index`. Git's own answer, not a reconstruction |

## The shape worth recording

**Both rounds' Blockings were the same class, one layer apart.** r1: subtracting dirty *paths*
credited a file edited again after the round. r2: comparing *content* credited a mode-only change.
The fix was not "compare harder" but "stop reconstructing what git already knows" — ask git what it
would store, and compare that. Per `review-method.md`'s stop condition, two consecutive rounds of
fix-induced findings in one component escalates from FIX to REDESIGN; this **was** the redesign,
applied within r2 rather than deferred to an r3 — the mechanism changed, not the threshold.

## Re-proved live after the fixes

In a scratch repository, through `reviewed_state` itself:

| observation | result |
|---|---|
| same blob, mode `100644` → `100755` | recorded `100644 8f1188e…` vs final `100755 8f1188e…` → **differ, so MISSED** |
| symlink `link → target2` | recorded `120000 3b7781e…` == final → no false failure |
| untracked `new.py` present at review time | recorded `100644 b917a72…` == final → no false failure |

Plus, on the real repository: `reviewed_state`'s entry for a staged file is byte-identical to what
`git rev-parse :<path>` reports, so the comparison runs through git's own filters.
