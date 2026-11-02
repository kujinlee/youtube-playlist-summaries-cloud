# Round 1 — reshard-sweep — claude

**Subject:** branch `reshard-sweep`, PR #445 (backlog #231), HEAD `26ff4899`, diffed against `origin/master...HEAD` (4 files, +56/-3).
**Mandate:** refute. **CI measured:** run `41065653565` (CI) and `41065653519` (Schema gates), both on `26ff4899`, which is the PR's head.

## Verdict

**NOT CONVERGED.** There is one Major and two Minors. The resharding itself is correct, and the timing goal is met: all 24 shards are green, the slowest is **1,032 s** (shard 17), and every shard is under 1,500 s. What fails is the concurrency claim the PR uses to justify N=24. The PR's own CI run contradicts it.

## Shard times — run 41065653565, `26ff4899`, job wall clock (`startedAt` → `completedAt`)

| shard | job s | sweep step s | entries | start offset s |
|---|---|---|---|---|
| 1 | 974 | 951 | 105 | 0 |
| 2 | 676 | 657 | 105 | **625** |
| 3 | 791 | 766 | 105 | **582** |
| 4 | 577 | 557 | 105 | **619** |
| 5 | 622 | 603 | 105 | 0 |
| 6 | 928 | 903 | 105 | **288** |
| 7 | 1002 | 971 | 105 | 0 |
| 8 | 984 | 955 | 105 | 5 |
| 9 | 937 | 908 | 105 | 0 |
| 10 | 579 | 562 | 105 | 0 |
| 11 | 769 | 746 | 105 | 0 |
| 12 | 945 | 919 | 105 | 0 |
| 13 | 987 | 962 | 105 | 0 |
| 14 | 783 | 760 | 105 | 0 |
| 15 | 897 | 868 | 105 | 0 |
| 16 | 571 | 553 | 105 | **98** |
| 17 | **1032** | 1008 | 104 | 0 |
| 18 | 958 | 929 | 104 | 0 |
| 19 | 912 | 890 | 104 | **561** |
| 20 | 558 | 540 | 104 | 0 |
| 21 | 614 | 592 | 104 | 2 |
| 22 | 940 | 913 | 104 | 0 |
| 23 | 701 | 679 | 104 | 0 |
| 24 | 916 | 893 | 104 | 0 |

- Mean **819 s**, max **1,032 s**, min 558 s. Max/mean is **1.26x**, close to the 1.24x spread the comment predicted. Headroom under `timeout-minutes: 30` is **1.74x**. The comment predicted ~1,055 s for the slowest shard, and 1,032 s was measured.
- Every shard's log ends `OK — … 0 survivor(s) — measured over shard i of 24 (round-robin)`, with i taking each value from 1 to 24 exactly once. The entry counts sum to 16×105 + 8×104 = **2,512**, which is the manifest.
- `mutation-sweep-complete` passed. The sweep's wall clock, from the first shard start to the last shard finish, was **1,473 s**: shard 19 started at +561 s and ran 912 s.

## Checks run

| CHECK | RESULT |
|---|---|
| Coverage, using the harness's own `load_manifests`, `parse_shard(..., zero_based=True, flag="--shard0")`, `shard_refusal` and `shard_slice` for every `i/24`, i = 0..23, over the real manifests (`scratchpad/cov445.py`) | 2,512 entries, 0 load errors. Slice sizes are 105 ×16 and 104 ×8, summing to 2,512. **0 missing, 0 duplicated** (by object identity). No shard refused as empty. `check-main-drivable` entries per shard: 7–8 |
| Matrix vs harness count | `shard: [1..24]` at `ci.yml:1087`. The harness gets `--shard0 "$SHARD_INDEX/$SHARD_TOTAL"` from `strategy.job-index`/`strategy.job-total` (`ci.yml:1324-1325,1342`), so there is **one source**: N cannot drift between the matrix and the harness |
| Required contexts | Branch protection reads `["verify","schema-gates","mutation-sweep-complete"]`. No per-shard context is required, and `mutation-sweep-complete` keeps its name and reads the aggregate `needs.mutation-sweep.result` (`ci.yml:1367-1377`). Nothing in it hard-codes 12 |
| Other hard-coded 12s (grep over `scripts/ .github/ docs/*.md docs/adr CONTEXT.md .claude/hooks`) | None live. What remains is history in comments (`ci.yml:1044-1066`) and stale prose in the body of backlog row #231 (Minor 2 below) |
| `python3 scripts/check-plan-code.py --self-test` (foreground) | `246/246 passed`, 14.6 s |
| PR CI overall | **CI concluded `failure`**. The only red step is `verify` → `check-review-recorded (PR only)`: "2 guarded path(s) changed and no review round was recorded". This round is what clears it (Minor 1) |

## Findings

### M1 — Major — the "concurrency limit is at least 35" claim is refuted by this PR's own run: the cap behaves as **20**, so every N=24 run queues 6 shards

- **Where:** `.github/workflows/ci.yml:1081-1084` ("35 jobs ran at once … so the account's limit is at least 35 — one run at N=24 is 26 jobs and fits"). The same sentence is in the PR body, line 50 of `gh pr view 445 --json body`.
- **Concrete input:** this PR's own CI run, 41065653565, which is the run the comment itself names as "the measurement".
- **Evidence (ran):** I listed every job of every run created between 12:30Z and 14:30Z on 10-30 (20 runs, 172 jobs, `scratchpad/jobs-window.tsv`) and counted the jobs in progress at each minute:
  - 13:44–14:24Z: concurrency is **exactly 20 at almost every sample, for about 40 minutes**. At 13:44:10 it was 19 jobs of this CI run plus 1 schema-gates job. At 13:46, 13:50 and 13:54 it was 20, all from this run. `ci.yml` sets no `max-parallel` (only `fail-fast: false`, `:1000`).
  - Only 18 shards started at T+0. Shards 16, 6, 19, 3, 4 and 2 started at **+98, +288, +561, +582, +619 and +625 s**, each one as an earlier job freed a slot.
  - The "35 at 13:03" figure comes from three runs: **24 of the 35 jobs concluded `cancelled`** (13 in 41059902379, 11 in 41059547611) and only 11 are `success`. These are `concurrency: cancel-in-progress` runs (`ci.yml:21-23`). I have **not verified** whether the cancelled jobs ever held a runner or only carry a `started_at` stamp. Either way they are no measurement of the cap, and the 20-job plateau directly contradicts them.
- **Consequence:** this is not a correctness or timeout problem, because queue time is not charged to `timeout-minutes` and the gate stays loud. It is latency:
  - The sweep's wall clock was **1,473 s, against a slowest shard of 1,032 s**. About 440 s of the run was waiting for a runner.
  - The required context `mutation-sweep-complete` did not *start* until **14:20:42Z**, 730 s after the last shard finished at about 14:08:30Z. By then two other PRs' runs (41068314545 and 41067400142) held all 20 slots (20 jobs at 14:15Z). From the first job start to the required check reporting took **2,203 s, about 36.7 min**.
  - One N=24 run fills the whole 20-slot cap for about 10 minutes and still has 6 shards waiting. Any second PR pushed in that window queues completely, which the 14:02 `usage-pace` pushes did.
- **Why it matters for the N decision:** the comment's model is "slowest = mean × spread, one wave". At a cap of 20, minus `verify` and `schema-gates`, only 18 shards run in the first wave. N=24 is therefore *two waves* every time, even with no other run on the account, and the end-to-end latency the change was meant to cut includes a second-wave tail. Using the comment's own cost model, N=18 gives a mean of 25 + 309 + 12,965/18 ≈ 1,054 s and a single-wave slowest of about 1,300 s at 1.24x (**PREDICTED, not measured**). That is under 1,500 s and probably no worse end-to-end than the 1,473 s measured here. Choosing between them is the coordinator's call. Correcting the false measurement is not optional.
- **Fix:** correct `ci.yml:1081-1084` and the PR body: the 35 figure includes 24 cancelled jobs, and this run shows a 20-job plateau with up to 625 s of queueing at N=24. The claim "N=24 fits" is withdrawn. Then either keep 24 with the two-wave cost stated, or measure N≤18. Whichever is chosen, the comment should state the measured numbers from this run, not the prediction.

### m1 — Minor — PR CI is red on `check-review-recorded`, which is expected and cleared by filing this round

`verify` failed only at `check-review-recorded (PR only)`: "`.github/workflows/ci.yml, scripts/check-plan-code.py` changed and no review round was recorded". Every other `verify` step succeeded or was a cache-only skip. Not a defect in the change. The merge needs a re-run after both halves are filed. That re-run touches only `docs/reviews/`, so `sweep_needed` should skip the sweep there. The shard measurement above therefore stays the evidence of record for `26ff4899`, and any code fold must re-measure.

### m2 — Minor — backlog #231 still says "14 jobs (12 shards + …)", and its FAILS IF is about `master`

- `docs/backlog.md:257`, in row #231's body: "one push now starts at least 14 jobs (12 shards + `verify` + `schema-gates`)". At N=24 that is 26, which matters given M1. The status cell was updated; this sentence was not.
- The row's FAILS IF reads "any `mutation-sweep` shard exceeds 1,500 s … **on `master`**". This PR's run is a branch run, so the measurement supports closing (max 1,032 s), but the condition as written is met only by the first master run after merge. The row correctly stays 🟠 in this PR. Whoever closes it should cite a master run ID, not 41065653565.

## What I tried to break and could not

- Gaps or duplicates at N=24: none, measured with the harness's own functions over the real manifest.
- An empty shard: `shard_refusal` returns None for every i in 1..24 at a count of 2,512.
- Matrix/harness drift: impossible as wired, because the harness reads `strategy.job-total`, not a literal.
- A renamed required context: none. The protected contexts do not include matrix legs.
- A summary or aggregate job that hard-codes 12: none. The aggregator reads `needs.mutation-sweep.result`.
