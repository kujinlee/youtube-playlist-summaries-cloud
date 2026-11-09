Reviewed head: b619b8f01a996b21e87fe7091ea88d80f8f52a88

# reshard-sweep-38 — round 1 — Claude half (adversarial, REFUTE mandate)

**Scope.** `git diff origin/master..HEAD` at `b619b8f0` (PR #550): the `mutation-sweep` matrix in `.github/workflows/ci.yml` goes from 24 to 38
shards, with a decision record beside it; a dated note on backlog #231 in `docs/backlog.md`; and a dashboard entry.

**Ran (all read-only, nothing memory-heavy):**
- `gh run view <id> --json jobs` over the seven cited master push runs. Slowest shard, mean, and slowest-shard name per run:
  42634452353 1683/1401 (16, attempt 2, failure), 42625034608 1669/1450.75 (19), 42609802269 1656/1356 (6),
  42592911465 1535/1296 (19), 42568439765 1538/1285 (16), 42561057231 1474/1287 (7), 42529027472 1262/1128 (2).
  **These match the record.** Max/mean spread is 1.12-1.22x, as stated.
- I loaded `check-plan-code.load_manifests` and applied `shard_slice` in-process, without running any suite. 4,505 entries over 91 targets, no
  load problems. Distinct targets per shard: **65-70 at N=24, 53-64 at N=38**, as stated (and 52-63 at N=40). Entries per shard:
  187-188 at N=24, 118-119 at N=38.
- The arithmetic. (637 + 11,067 + 23,014) / 24 = 1,446.6. At N=38: 23,014 / 38 = 605.6, plus 470 = 1,075.6. 1,075 x 1.22 = 1,312, and 1,800 / 1,312 = 1.37.
  1,075 x 1.45 = 1,559. 38 x 1,075 / (24 x 1,447) = 1.176. **All of them reproduce.**
- The last four scheduled runs, for the 60-minute variant.
- PR #550's own CI run, 42660040212. It was in flight at 17:03Z: 20 jobs in progress, 18 queued.

**What held up under attack:**
- **N=38 breaks nothing in the harness.** `SHARD_SPEC` takes up to four digits, and `parse_shard` and `--shard0` take `job-index`/`job-total`
  straight. A full-manifest shard is refused when empty (`shard_refusal`), but 4,505 / 38 leaves about 118 entries in each shard. A PR-scoped shard
  with no entries returns `Measured(declared=0)` and prints "nothing to do" (`check-plan-code.py:2085-2087`, `:7316`). So a scoped PR at N=38 still passes in
  every shard, and `mutation-sweep-complete` still reports.
- **No script pins N or a job count.** I grepped `scripts/` and `tests/` for the matrix list, `job-total`, and "24 shards" / "26 jobs". The only hits for
  `mutation-sweep (N)` are self-test fixtures, in `batch-ci.py`, `check-ci-watched.py` and `ci-durations.py`, and each uses shard 1-3.
  `ci-durations.py` keys on job names and derives the slowest shard as a group row, so new shard names 25-38 are just new rows.
- **The time budget.** `SWEEP_JOB_START` is the job's first step, so queue time is not charged to the 1,680 s budget. A second wave does not eat it.
- **The schedule's 60-minute variant only gains.** At N=24 the latest scheduled run (42489447406) had a mean of 2,021 s and a max of 2,400 s, with
  two seeds. 38 shards cut its per-shard work by the same 24/38.
- **The 20-slot model is confirmed live.** PR #550's own run shows exactly 20 jobs in progress and 18 queued.

I found no BLOCKER or HIGH defect.

### F1 — Medium — More control runs, and so more exposure of the after-control check, is a cost the record leaves out

`.github/workflows/ci.yml:1205-1235`. The record does not state it. The job's own header, at `:1030-1034`, warns that sharding *"MULTIPLIES THE
EXPOSURE OF THE ONE CHECK WHOSE JOB IS TO INVALIDATE A RUN"*.

- **What I measured.** I summed distinct targets per shard over all shards with `shard_slice`, on the real 4,505-entry manifest. The totals are
  **1,620 at N=24 and 2,218 at N=38, which is 1.37x**. Each shard runs control plus re-control for each of its targets, so roughly 3,240 suite runs become
  4,436 per full sweep.
- **What that means.** Every flaky suite gets 37% more chances to turn a green sweep into CANNOT RUN. That is the same "green commit goes red with no
  survivor" failure this change is fixing, arriving by a different route.
- **What the record says instead.** It counts this only as runner-time ("rises ~18%, costs no money").

**Fix.** Add one line to the record: control suite runs rise 1.37x (1,620 to 2,218 target-controls, by `shard_slice` over 4,505 entries), so the flake rate
of an after-control red rises with it. Name the row that tracks control flakes, if one exists.

### F2 — Medium — The record does not say how long N=38 lasts, and it reverses 11-07's "the next lever is per-suite cost, not a larger N" without saying why

`ci.yml:1229-1234`, against `ci.yml:1191-1194` (11-07) and the history of backlog #231.

- **The history.** This is the fifth retune in 16 days: 8 to 12 (10-24), 12 to 24 (10-30), 24 to 18 (11-03), 18 to 24 (11-07), and now 24 to 38.
- **What 11-07 said.** That entry stated *"the next lever is per-suite cost (…), not a larger N"*.
- **What the new record says.** *"past ~38 the lever is per-suite cost"*. That moves the line instead of answering it.
- **How fast it runs out.** The manifest held 2,512 entries on 10-30 (`ci.yml:1131`) and holds 4,505 today. That is about 200 entries a day. On the record's
  own model, the slowest shard at N=38 reaches the 1,500 s trigger when work per shard grows from 606 s to (1,500 / 1.22) - 470 = 759 s. That is a 25% rise in
  work, about 1,100 entries at today's mix. **PREDICTED, not measured: roughly 5-6 days of growth at the recent rate.**
- **The floor makes it sooner.** The floor grows too, with targets and with suite cost. It was 221 s at N=8, 309 s at N=12, and 461 s at N=24.
- **The ceiling.** After this change, N can only rise by 2 before a third wave, so the lever is nearly spent.

**Fix.** State the time-to-trigger arithmetic in the record and in the backlog note. Reconcile it explicitly with 11-07's sentence: say why N was still the
right lever this time (for example, that it is the only same-day lever). Name the row that owns the per-suite cut, so the next trigger does not reach for N
again.

### F3 — Low — The "measured" mean in the model check looks swapped, and the check is in-sample

`ci.yml:1216`: *"N=24 reproduces mean 1,450s (measured 1,447s)"*. The dashboard entry repeats it.

- **The swap.** The job wall-clock mean of run 42625034608 by `gh run view --json jobs` is **1,450.75 s**. The record's own component sum is
  (637 + 11,067 + 23,014) / 24 = **1,446.6 s**. So "1,447" is the model and "1,450" is the measurement, or "measured" means the log-derived sum, which is not
  job wall clock. Either way the labels are misleading.
- **The check is in-sample.** It reproduces the mean of the very run whose costs it was fit on. That shows the partition arithmetic is consistent, not that
  the model predicts.

**Fix.** Label each figure correctly. If possible, add one out-of-sample check, for example predicting run 42609802269's mean of 1,356 s from its manifest.

### F4 — Low — A full-sweep measurement at N=38 exists before merge, and the record defers to the master push instead

`ci.yml:1235`: *"The first master push run of this change is the measurement"*. The backlog note says the same.

- **Why the PR run counts.** `ci.yml` is a harness path, which `select_manifests` treats as FULL (the self-test pins it in `_H`, at
  `check-plan-code.py:6422-6423`). So PR #550's own run, 42660040212, sweeps the whole manifest at N=38 now.
- **The precedent.** The 11-07 retune recorded exactly this ("MEASURED on this change's own run 42432742676").

**Fix.** Before merging, read run 42660040212's per-shard wall clock. Record it as MEASURED (mean, slowest, spread), and keep the master push as the second
sample.

### F5 — Low — "Two waves" is a smoothing: slots free one at a time, and the 20 are shared

`ci.yml:1219-1228`, and the backlog note's *"38 is the largest N that adds no third wave"*.

- **Slots free one at a time.** First-wave shards finish across a 1.12-1.22x spread, and `verify` and `schema-gates` free their slots early. So N=40's
  "third wave" of two jobs waits for the 19th and 20th slot to free, not for a whole shard duration. The end-to-end cost of 38 against 40 is small either way.
  38 is a fine pick, but "no third wave" overstates a cliff.
- **The 20 are shared.** The limit is per account. A concurrent PR run (also 40 jobs now), a `batch/**` push, or another repository's jobs shift every
  wave. The record says "on a quiet queue" for the end-to-end figure, but not for the 38 = 40 - 2 derivation.

**Fix.** Soften the wording to say 38 keeps this push's own jobs within two batches of 20 on a quiet queue.

### F6 — Low — "REOPEN backlog #231" is the wrong instruction for a row that is open

- **The instruction.** `ci.yml:1235` says *"REOPEN backlog #231 if any shard exceeds 1,500s"*.
- **The row.** Backlog #231 is **🟠 STILL OPEN** (`docs/backlog.md:257`, last column). The actionable instruction is the close condition, for example
  "close when N consecutive master full sweeps stay under 1,500 s".
- **A dropped caveat.** The backlog note's range "1,262-1,683 s" drops the ci.yml record's caveat that 1,683 is censored by the kill.

**Fix.** Rewrite it as a close condition, and carry the "censored" word into the backlog note.

**Could NOT check:**
- The cost-model sums (637 / 11,067 / 23,014). These need all 24 job logs of run 42625034608. I did not download them, and I trusted the decomposition.
- The 470 s floor at N=38. It rests on per-target median control costs I did not re-derive. I verified only the target counts it rests on.
- Whether the 20-job limit is consumed by the account's other repositories.
- Attempt 1 of run 42634452353. `gh run view` shows the latest attempt only.
- The final outcome of PR #550's in-flight run.

VERDICT: CONVERGED
