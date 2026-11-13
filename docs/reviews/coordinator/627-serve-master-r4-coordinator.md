# Round 4 — `627-serve-master` (backlog #627) — coordinator

REVIEW GAP: codex — alternation (owner 2026-10-28: rounds 2+ run ONE half).

**Why a fourth round.** After r3 converged, CI run 43431833044 failed 16 `mutation-sweep` shards on
ATTRIBUTION (0 survivors). `check-plan-code.py` matches an `expect` to a red case by equality (`w == f`).
14 expects written in the r2 fold named a prefix of their case, and 2 r1 cases went red by raising, which
appends ` — <Exc>: <msg>` to the reported name. Commit f8bd907e fixes both, in self-tests and manifests
only. `check-review-recorded` then refused the PR because guarded code was committed after r3, so this
round reviews f8bd907e.

**Evidence.** Full `--mutate . --only` sweeps on a clone outside the repository: explainer-serve 112/112
killed and attributed, regen-pages 72/72, 0 survivors. Self-tests 282/282 and 121/121.

**Result.** The Claude half (`docs/reviews/claude/627-serve-master-r4-claude.md`) is CONVERGED with no
findings. The round cap (from r4, findings are filed unless a Blocker) did not come into play.
