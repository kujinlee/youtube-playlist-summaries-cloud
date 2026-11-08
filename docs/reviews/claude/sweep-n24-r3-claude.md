Reviewed head: 6a358b4d9048daf586238f774ab83709093daf01

# sweep-n24 — review round 3, Claude half (REFUTE mandate, round cap)

Scope: `git diff a40e9086..HEAD` (the round-2 label fixes) and the final `mutation-sweep` comment block in
`.github/workflows/ci.yml` as a whole, plus `git diff 83a22af1..HEAD -- .github/workflows/ci.yml`.

## What I checked, and against what

| Claim in the comment | Source | Observed | Holds? |
|---|---|---|---|
| run 42387350733 is a master push of fcf00068 | `gh run view --attempt 1` | event `push`, head `fcf00068` | yes |
| shards 3, 12, 14 CANCELLED at 30m | attempt 1 jobs | cancelled at 1,814 / 1,802 / 1,815 s | yes |
| re-run cancelled shard 3 at 30m14s, "killed at 1,814s" | attempt 2, job 128556531643 | cancelled, 1,814 s wall clock | yes |
| 1,344 s of mutant work | shard 3 log: `[1/228]` 23:07:45.43 → `[1/70] re-control` 23:30:09.24 | 1,343.8 s | yes |
| re-control at 57 of 70 when killed | shard 3 log | last progress line `[57/70] re-control` 23:33:00, terminated 23:33:15 | yes |
| ~1,881 s to finish, labelled ESTIMATED | shard 3 control took ~255 s; re-control start + 255 ≈ 23:34:24, i.e. ~1,881 s from 23:03:03 | arithmetic holds; correctly NOT under MEASURED now | yes |
| shard 12 took 29m41s | attempt 2, job 128556531550 | success, 1,781 s | yes |
| floor ~25 + ~247 + ~247 = ~520 s | shard 12 log: 23:03:03→23:03:29 (26 s); control 23:03:29→23:07:36 (247 s); re-control 23:28:33→~23:32:40 (~247 s) | yes | yes |
| PREDICTED 1,344 × 18/24 + ~537 = ~1,545 s, ~14% inside 30m | arithmetic: 1,008 + 537 = 1,545; (1,800−1,545)/1,800 = 14.2% | labelled PREDICTED | yes |
| run 42432742676 = this PR, c3d85c6d, N=24 | `gh run view --json` | `pull_request`, head `c3d85c6d`, 24 `mutation-sweep (n)` jobs | yes |
| all 24 shards green | same | 24/24 `success` (`verify` failed; the comment makes no claim about it) | yes |
| mean 1,300 s | same, startedAt→completedAt | 1,300.4 s | yes |
| slowest 1,499 / 1,460 / 1,459 s | same | shards 9, 11, 3 | yes |
| 1.20× inside 30m | 1,800 / 1,499 | 1.2008 | yes |
| "further manifest growth risks crossing it" | — | now labelled PREDICTED (R2 fold) | yes |

Matrix: `shard: [1 … 24]`, 24 entries. `git diff 83a22af1..HEAD -- .github/workflows/ci.yml` touches only `#`
comment lines inside the matrix comment block; no YAML key, step, timeout or other line outside it changed.

## Findings

### R3-F1 — Low — "this PR's own run had a shard wait 1,986s" does not name its run, and the cited N=24 run shows a longer wait

The 1,986 s figure (round 1, Claude R1-F2) came from an earlier run of this PR. The run the comment cites two
lines later, 42432742676, had a `mutation-sweep (13)` queue of 2,538 s (created_at → started_at, `gh api
.../runs/42432742676/jobs`), and `mutation-sweep (8)` 2,472 s. The sentence is true of the run it was measured on
and its direction ("contention is worse than the ~1,000-1,140s second-wave wait") is only strengthened, so nothing
is overstated. Not worth a fold under the round cap; FILE-or-drop at the coordinator's discretion. If touched,
"queued up to 2,538s on run 42432742676" would bind it to the cited run.

No other finding. Every number under MEASURED is true of its cited run; every extrapolation or forecast (~1,881s,
~1,545s, "further growth risks crossing it", the ~537 s shard-3 floor inside the PREDICTED sentence) is labelled
ESTIMATED or PREDICTED.

VERDICT: CONVERGED
