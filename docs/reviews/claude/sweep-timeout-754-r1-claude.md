Reviewed head: 66590fea02c62cf81a265e75802f6860cb24feea

# sweep-timeout-754, round 1, Claude half (adversarial)

Scope: `git diff origin/master...HEAD`, which touches `.github/workflows/ci.yml` (the sweep job's `timeout-minutes: &sweep-limit`, 30 -> 40 off the schedule) and `scripts/check-merge-ready.py` (the ACCOUNTED_MENTIONS key for that line).

## What I ran, on this head

| Check | Result |
|---|---|
| `python3 scripts/check-merge-ready.py --self-test` | rc 0, 463/463 |
| `python3 scripts/check-plan-code.py --self-test` (includes `sweep_limit_pin` over the real ci.yml and its fixtures) | rc 0, 506/506 |
| `check-merge-ready.unaccounted_mentions` over every workflow | `[]` for ci.yml, schema-gates.yml, strace-measure.yml |
| `hold_reasons` / `failure_path_flags` / `gate_invocation_removals` / `scope_exits` over this branch's own diff | all empty, so no false LOOSENING HOLD and no missed mention |
| `sweep_partition(manifest, 38, sweep-costs.json)` + `shard_estimate`, full manifest (6,810 entries) | estimated work per shard: min 1,093 s, median 1,127 s, max 1,133 s |
| grep for other readers of the 30 (`1680`, `1,680`, `|| 30`, `30 min`, `SWEEP_TIMEOUT_MINUTES`, `SWEEP_HEADROOM`) in scripts, workflows, batch-ci, session-state | no CODE reads the literal. `ci_deadline` takes the runner-evaluated alias, and the self-test's `30` values are synthetic `LIMIT_VAR` fixtures that do not depend on ci.yml. `batch-ci.py` has no sweep-duration bound. Only comments and case names are stale (C2) |

Not a gate loosening. The limit caps runtime and is not a pass/fail condition. The harness still stops 120 s before the kill (`SWEEP_HEADROOM`), and each suite run is still capped by `SUITE_TIMEOUT_CEILING` (600 s). So a hung mutant is still killed per suite, and only a hang outside the harness (for example a stuck `npm ci`) now costs 40 min instead of 30. The new comment says this. Raising the limit instead of adding shards is consistent with the matrix comment's WHY 38: 40 jobs fill two batches of 20 runners. The arithmetic checks out: 40 x 60 - 120 = 2,280, and 1,680 / 1,330 = 1.26, so a 26% slowdown reaches the old budget, which sits inside the measured 18-44%.

## Findings

**C1 — Medium — commit subject closes backlog #754, but the row is not updated, and the change implements a different fix from the row's.** `docs/backlog.md:693` (row 754 still `🟢 FILED`). The HEAD subject ends `(backlog #754)`, which `scripts/check-backlog-closure.py:109` (`CLOSING`) reads as closing the row.
- **What happens:** once this squash-merges, `check-backlog-closure` warns that row 754 is closed without a `✅`, and the backlog still lists #754 as open work.
- **Why the row cannot simply be ticked:** its Fix for C1 is "headroom in the CUT (a factor on the estimate, or a lower target per shard)". Its C2 (single-sample prices, ±25%), C3 (stale run ids at `ci.yml:1392` and `check-plan-code.py:1665`) and C4 are untouched here.
- **Needed:** the row records that a longer limit was taken in place of cut headroom, and says what stays open (C2-C4). Either keep the row open with a ⟳ note and use a subject that does not close it, or split the row. The dev-process rule is that the tick rides in the same PR.

**C2 — Low — comments and self-test case names that state the old 30 / 1,680 as current.**
- `.github/workflows/ci.yml:1206`: "60 on the schedule only; every other event keeps 30."
- `ci.yml:1374`: "1.20x inside 30m".
- `ci.yml:1409`: "1.37x inside 30m".
- `ci.yml:1417-1418`: "inside the 1,680s budget".
- `scripts/check-plan-code.py:133`: "the whole `timeout-minutes: 30` of a pull request's shard".
- Case names at `check-plan-code.py:3181` ("none of a push's 1,680 left") and `:3462` ("leaves 1,530 s of a push's 1,680").

Failure scenario: a later reader sizing the shard count or the headroom takes 1,680 as the live push/PR budget, which is the mistake this branch exists to correct. The fixtures are synthetic, so their VALUES are fine; only the "a push's" wording is now false. The `1,680s` in the budget-stop cases at `check-plan-code.py:4846/4855` comes from a fixture limit of 30 and is also fine. Fix: mark the historical ones as the old 30, and reword the case names so they do not name a push's real budget.

**C3 — Low — the new comment's "~1,330 s of work at the NIGHTLY's prices" has no source, and the committed table does not reproduce it.** `.github/workflows/ci.yml:1223`.
- **What the table gives:** `sweep_partition` + `shard_estimate` over the committed `scripts/sweep-costs.json` (source `46048742954@4e247843`) and the full manifest on this head estimate a max of 1,133 s per shard (median 1,127 s). 1,330 s may be a job wall clock including setup and install, or a different manifest, but the comment calls it "work at the nightly's prices" and cites nothing.
- **What hangs on it:** the derived "2,280 s of budget is ~1.7x the cut" would be ~2.0x on the model's own number.
- **Failure scenario:** the next sizing decision anchors on a figure nobody can re-derive.
- **Fix:** cite where 1,330 comes from (run id and how it was read), or replace it with the model figure and say it is the model.

No Blocking or High findings. The change is mechanically correct, both self-tests are green, and check-merge-ready classifies the diff without a false HOLD. C1 is the only item that affects what merges, and it is bookkeeping, not code.

VERDICT: NOT CONVERGED
