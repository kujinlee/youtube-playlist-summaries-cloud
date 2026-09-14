# record-review-topology — round 1, coordinator adjudication

**REVIEW GAP:** claude — not invoked; this branch was built by a worker fork that is not permitted
to spawn subagents, so only the Codex half could run. **The Claude half is OWED before merge** and
this is not a "Codex was down" fallback — it is the opposite shape, and saying so is the point of
the marker.

⚠ That matters more than usual here. `dual-review-halves-are-not-redundant` records a Codex-only
round clearing a live money guard that the skipped Claude half caught in one pass, and this very
branch's own evidence table shows the two halves producing **zero overlapping findings** across
three rounds. A single-half round is a weaker gate, measurably, and this one reviewed a guard.

## Round 1 — Codex, `gpt-5.5`

`docs/reviews/codex/record-review-topology-r1-codex.md` · verdict
`docs/reviews/verdicts/record-review-topology-r1-codex.verdict.json` (`gate_ran: true`).
Verdict line: **NOT CONVERGED**. 1 Blocking, 3 High, 3 Medium, 1 Low.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | **Blocking** | `dirty` subtracted by PATH, so "review `x`, edit `x` again, commit" certified unreviewed content. Reproduced in a scratch repo | **FIXED** — the verdict now records the **blob** of each uncommitted file; the check compares content against the merging tree |
| 2 | High | CI runs the step on `pull_request` only; a push to `master` asks neither question | **ACCEPTED, STATED** — the path is closed by `.claude/hooks/block-default-branch-push.sh`, a different mechanism. Recorded in the docstring so nobody reads green CI on master as this gate speaking |
| 3 | High | A round taken at the merge base — before the branch's first commit, which is what the hold-fixes-uncommitted practice produces — was silently skipped | **FIXED** — the merge-base skip is deleted; membership is decided entirely by "this branch ADDED the verdict" |
| 4 | High | "No usable round" returned 0 while printing NOT CHECKED, and CI reads the exit code | **FIXED** — now exit **2**, CANNOT RUN, cleared by a `REVIEW GAP:` line (the marker that already exists for a half that could not run) |
| 5 | Medium | Population used CHANGED verdicts, so a MODIFIED historical verdict could clear the tail | **FIXED** — population is now `added_paths`, matching how `review_added` answers the sibling question |
| 6 | Medium | `git status --porcelain` parsed by slicing: quoting, renames, a file named `a -> b` | **FIXED** — `git diff --name-only -z --no-renames HEAD`; the field IS the path |
| 7 | Medium | `docs/plugins.md` still commanded concurrent dispatch with no r2+ exception, contradicting the new section | **FIXED** — that line now states both topologies and points at *Round topology* |
| 8 | Low | A case named the live `guarded_changes` wiring without exercising it; deleting the call left the suite at 45/45 | **FIXED** — the rule moved into the pure `round_tail`, which the cases now drive, and a mutation covers it |

Codex also noted two of the five original mutation entries were killed by sibling cases as well as
by the case they name. `check-plan-code --mutate .` verifies attribution and reported all 564
attributed, so this is weaker one-case attribution than the prose implied, not a survivor.

## What was re-proved after the fixes

Live, against real git, each direction over a control: same path + different content **fails**;
same content passes; a merge-base round covering the branch passes; no usable round is **rc=2**;
a declared `REVIEW GAP:` clears it and echoes the reason.
