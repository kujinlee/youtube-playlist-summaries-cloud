Reviewed head: 83a22af1197d7dbb09569686ae20c1a86c0ac491

# sweep-n24 — round 1, Claude half (adversarial, mandate: REFUTE)

Subject: `git diff origin/master...HEAD` — `.github/workflows/ci.yml` `mutation-sweep` matrix 18 -> 24 plus
the `⟳ 2026-11-07` comment block (ci.yml:1168-1180), and a dashboard entry (`docs/dashboard-entries.md`).

## What was checked, and how

| Check | Method | Result |
|---|---|---|
| Anything keyed on the shard COUNT or the `mutation-sweep (N)` names | grep `scripts/batch-ci.py`, `check-merge-ready.py`, `check-ci-watched.py`, `check-plan-code.py`, `scripts/mutations/`, `.claude/hooks/`, `tests/` | Nothing keys on N. `batch-ci.py:145` matches `^mutation-sweep\b`; `REQUIRED_CHECKS` (batch-ci.py:140) names only the aggregate; `check-ci-watched.py:660-680` uses shard names only in self-test fixtures. The workflow passes `strategy.job-index`/`job-total` straight to `--shard0` (ci.yml:1253-1254). Two `18 shards` mentions (`check-plan-code.py:5897`, `scripts/mutations/expected_mutations.py:12`) are dated measurements, not logic. |
| Could a shard be EMPTY at N=24 | `shard_slice` (check-plan-code.py:1337) is round-robin `muts[index-1::total]`; `shard_refusal` refuses an empty FULL shard; under a PR selection an empty slice is expected (check-plan-code.py:1747) | Full manifest ~4,090 mutations (shard 3 held 228, shard 12 held 227 at N=18) -> ~170 per shard at 24. No empty shard. |
| The cited MEASURED numbers | `gh api .../runs/42387350733/attempts/{1,2}/jobs`, the shard 3 and shard 12 attempt-2 job logs, `gh api .../runs/41609884078/jobs` | Shard 3 cancelled at 30m14s (23:03:02 -> 23:33:16) ✓; shard 12 29m41s ✓; re-control at 57/70 when killed ✓; `gen-backlog-page` control ~65s ✓. 11-03 run: slowest 1,001s (shard 15), mean 842s, six waited, max wait 745s, span 1,703s ✓. Mutant work 1,344s (23:07:45.4 -> 23:30:09.2), comment says 1,334s — 10s off, immaterial. |
| The PREDICTED ~1,435s | recomputed the non-dividing floor from the same two logs | **Floor understated — R1-F1.** |
| Second wave / 20-job limit | this PR's own live run 42427652660 (polled 00:33Z) | **Queueing understated — R1-F2.** |

## Findings

### R1-F1 — Medium — the "~435s floor" is a partial re-control; the real floor is ~520-540s and the corrected prediction (~1,545s) is OVER the comment's own 1,500s REOPEN line

**Where:** `.github/workflows/ci.yml:1175-1177` ("shard 3's mutant work x 18/24 = ~1,000s plus the ~435s floor that does not divide -> ~1,435s").

**Scenario.** The floor is setup + control + re-control. Measured from the logs of run 42387350733 attempt 2:

| Shard | setup (job start -> step) | control | mutant work | re-control |
|---|---|---|---|---|
| 3 (killed) | 24s (23:03:03 -> 23:03:27) | 258s (-> 23:07:45) | 1,344s | killed at 57/70 after 171s |
| 12 (completed) | ~25s | 247s (23:03:29 -> 23:07:36) | 1,257s | 247s (23:28:33 -> ~23:32:40) |

Re-control 1 -> 57 took 171s on shard 3 and control 1 -> 57 also took 171s (23:03:30 -> 23:06:21); control 57 -> 70
took a further 84s. So the "~435s" is `264 + 171` — control plus the PART of re-control that had run when the job was
killed — and drops ~84s of re-control and ~24s of setup. Shard 12, which finished, shows the whole floor directly:
25 + 247 + 247 ≈ 520s. Shard 3 needed ~1,881s in total (≈ 23:34:24), not "30m14s and nearly done".

Corrected: 1,344 x 18/24 = 1,008 + ~537 = **~1,545s** for shard 3's runner (shard 12: 943 + 520 ≈ 1,463s). That is
above "REOPEN #231 if any shard exceeds 1,500s" and ~14% inside `timeout-minutes: 30`, not "INSIDE 30m but near the
line". The decision to go to 24 is still right — it is the only lever that lands today — but the comment states a
headroom the arithmetic does not give, and the next red will be read against it.

⚠ One way the floor could be LOWER at 24, not measured: control runs once per file the shard touches (both logs show
70 files at N=18); a file with fewer than 24 entries is absent from some shards at N=24. The expensive control files
(`gen-backlog-page` ~65s) would need to be checked for entry counts before relying on that.

**Fix.** Restate the line as: floor ~520-540s MEASURED (shard 12 completed: 25 + 247 + 247; shard 3: 24 + 258 + ~255
extrapolated from its 57/70 re-control), prediction ~1,460-1,545s PREDICTED — at or over the 1,500s line, so the trigger
is expected to fire again on a slow runner. Keep the per-suite lever (backlog #231) open and say it is now the
expected next step, not a contingency. Correct 1,334s -> 1,344s while there.

### R1-F2 — Medium — "~500s of queueing" is a quiet-queue figure from a lighter manifest; this PR's own run already shows shards waiting 1,986s+, and the 20-job limit is account-wide

**Where:** `.github/workflows/ci.yml:1174` ("at the cost of a second wave (~500s of queueing ...)"); same claim in the
dashboard entry ("some of them wait in line for a few minutes").

**Scenario.** Two independent reasons the figure is low:

1. **Even on a quiet queue the wait grows with shard length.** After `schema-gates` (~1m43s) and `verify` (~7m) free
   two slots, the remaining four queued shards start only when a first-wave SHARD finishes. At 24 that is ~980-1,140s
   (this PR's run: shard 18 983s, shards 5 and 19 1,139s), not the 11-03 745s. So the quiet-queue end-to-end is roughly
   1,000 + 1,500 ≈ 2,500s, against N=18's measured 1,194s on 11-03 — the reason backlog #415 moved to 18 in the
   first place, now paid back with interest.
2. **The limit is shared by every concurrent run.** This PR's own run 42427652660 (created 23:58:58Z, polled
   00:33:12Z): shard 7 started 00:32:04 (**1,986s queued**), shard 3 at 00:27:24 (1,706s), and **shard 12 was still
   queued at 2,054s**. A master push now holds 26 jobs by itself, so any concurrent PR or `batch/**` run (never
   cancelled, ci.yml:30-37) is starved for a full shard length.

Nothing breaks: queue time does not count toward `timeout-minutes`, and no watcher in `batch-ci.py` or
`check-ci-watched.py` has an age threshold (grepped) — so this is latency, as the comment says. But the cost is
roughly 4x what the comment and the dashboard state, and it lands on every PR's required check.

**Fix.** Replace "~500s" with the measured range from this PR's run once it completes (sweep span and max wait), and
state the mechanism: the second wave waits for the first finished shard (~1,000s at 24) plus whatever other runs hold.
Correct the dashboard's "a few minutes". Consider filing the cheaper alternative explicitly on backlog #231 / #415:
reducing per-suite cost lets N return to 18 (one wave), which is the end-to-end win.

### R1-F3 — Low — backlog #231 is still ✅ closed while the comment says its trigger fired and it "stays open"

**Where:** `docs/backlog.md:257` (row 231, `✅ (was 🟠)`), versus `.github/workflows/ci.yml:1168` ("ITS TRIGGER FIRED A
THIRD TIME") and `:1179` ("stays open on backlog #231").

**Scenario.** The PR does not touch `docs/backlog.md`. The row's latest dated text is the 11-03 move to 18; the 11-07
firing and the per-suite lever it names exist only in a workflow comment and a dashboard entry. `dev-process.md`
requires a discovered step in the backlog in the same turn; a reader of the backlog sees a closed row.

**Fix.** Reopen row 231 (or add the 11-07 firing to it) with the measured run, the N=24 move, and the per-suite lever
as the open next step, in this PR.

### R1-F4 — Low — the 11-03 "1,001s slowest shard" is cited as support for 24 but measures a manifest ~60% lighter

**Where:** `.github/workflows/ci.yml:1172-1173` ("its per-shard work was MEASURED at a 1,001s slowest shard on 11-03").

**Scenario.** On 11-03 N=18's slowest shard was 1,184s (41607028370); today N=18's shard 3 needed ~1,881s. The 11-03
N=24 figure says nothing about today's per-shard work, yet sits in the sentence that justifies the choice, labelled
MEASURED. The next sentence does say PREDICTED for today, so this is phrasing, not a false number.

**Fix.** Either drop it or qualify it: "on the 11-03 manifest; today's is ~1.6x heavier (shard 3: 1,184s -> ~1,881s at
N=18)".

### R1-F5 — Info — this PR's `verify` is red on `check-review-recorded (PR only)`

Run 42427652660, job 128569300979: `FAILED — 1 guarded path(s) changed and no review round was recorded:
.github/workflows/ci.yml`. Expected before this review is filed; it should clear once the round documents land. Not
a defect of the change.

## Not found

- No consumer keys on N or on a specific shard name; no shard can be empty at 24.
- `cancel-in-progress` is unchanged and applies to pull requests only; a push sweep at 24 is never cancelled, which
  is what makes F2's starvation of concurrent runs real but bounded to one sweep length.
- `timeout-minutes` (60 on the schedule, 30 otherwise) is untouched; the scheduled two-seed sweep gains headroom
  from 24 as well.

VERDICT: NOT CONVERGED
