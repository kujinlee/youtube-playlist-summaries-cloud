Reviewed head: 0b4f691a0c3b8f6839db8b0755378db81db633cd

# reshard-18 — round 1 — Claude half

Reviewed range: `origin/master...origin/build-415` (head `0b4f691a`, PR #484, backlog #415).

Method: read the full diff (5 files). Ran in a fresh detached worktree of `origin/build-415`. Mandate: REFUTE —
look for a dropped or duplicated mutation, a count pin that disagrees, a shard that can time out, a number not measured.
Everything below marked EXECUTED was run. Anything else is labelled UNVERIFIED. No git writes, no Postgres.

## Verdict

**CONVERGED on the code.** There are three Low findings, all in prose: the backlog and register still state the old
count or a refuted figure. None of them changes behaviour. I found no input where a mutation is dropped or duplicated,
and no count pin that disagrees.

## What was checked

| Check | Result |
|---|---|
| Where N is encoded | Only in the matrix list, `ci.yml:1130` (`[1..18]`). The step passes `--shard0 "$SHARD_INDEX/$SHARD_TOTAL"` from `strategy.job-index`/`job-total` (`ci.yml:1370-1371,1388`). No hand-written `/N` anywhere. `mutation-sweep-complete` reads `needs.mutation-sweep.result` (the aggregate), so it does not depend on N. `grep job-total\|shard0` over `scripts tests .claude/hooks` matches only `check-plan-code.py` and its manifest. Neither holds a count. |
| Partition at N=18 (EXECUTED) | Used the harness's own `load_manifests`, `parse_shard(f"{i}/18", zero_based=True, flag="--shard0")`, `shard_refusal` and `shard_slice` for i = 0..17. 3,313 entries, 0 load errors. Shard sizes: 185, then 184 ×17. 3,313 entries assigned, 3,313 unique, equal to the manifest. No shard empty, none dropped, none duplicated. `shard_slice` is `muts[index-1::total]` (`check-plan-code.py:2697`), an exact partition for any N ≥ 1. |
| `check-plan-code.py --self-test` (EXECUTED) | **281/281 passed**, with `node_modules` linked into the worktree. Without the link: 278/281. The 3 failures were all `node_modules/typescript is missing`, which comes from the fresh worktree, not from this diff. |
| Measured numbers (EXECUTED, `gh run view --json createdAt,headSha,jobs`) | Run 41607028370 (`ac6b8f87`, 18 shards, all success): slowest 1,184 s, mean 993 s, longest start wait 13 s, `mutation-sweep-complete` done at 1,194 s. Run 41609884078 (`7e37589e`, 24 shards, all success): slowest 1,001 s, mean 842 s, six waits of 436–746 s (the seventh-longest was 128 s), complete at 1,704 s. **Every figure in the diff reproduces.** Arithmetic: 1 − 1194/1704 = 29.9% ("30%"); 1704/60 = 28.4 min and 1194/60 = 19.9 min; the difference is 8.5 min ("about eight"). |
| Timeout headroom | Measured: 1800/1184 = **1.52x** at 18 (claimed 1.52x), 1800/1001 = 1.80x at 24 (claimed 1.80x). At the worst 1.45x spread on record: 993 × 1.45 ≈ 1,440 s, which is 1.25x inside the timeout and 60 s under backlog #231's 1,500 s trigger. The slowest measured shard is 316 s under the trigger, so about 27% growth in its work fires #231 before the timeout is in danger. Safe today. The trigger is the alarm, as the comment says. |
| Job budget | `schema-gates.yml` adds one PR job (`schema-gates`; `prod-drift` runs only on schedule or dispatch, `:261`). `verify` + 1 + 18 = 20. That matches `ci.yml:1117-1119`. |

## Findings

### L1 — Low — backlog #231 still says one push starts "at least 26 jobs (24 shards …)" and repeats the refuted "35 jobs ran at once"

**Where:** `docs/backlog.md`, row 231 (the "Concurrency measured, not assumed: 35 jobs ran at once on 2026-10-30, so 26
jobs per run fits" clause, and the "one push now starts at least 26 jobs (24 shards + `verify` + `schema-gates`)" risk
note).

**Scenario:** a reader who opens #231 when it next fires learns that the limit is ≥35 and that a run is 26 jobs. Both
are now false. The first was refuted at `ci.yml:1108-1109`: the count included 24 cancelled jobs. The second is false
since this PR. This row is the one #415's own text tells the reader to reopen. The fault was already on master, and this
PR changes the count without updating it.

**Fix:** one line in row 231: "⟳ 2026-11-03: 18 shards, 20 jobs per PR run (backlog #415); the 35 figure counted
cancelled jobs."

### L2 — Low — register row 10 now disagrees with itself about N

**Where:** `docs/optimization-register.md:34`.

**Scenario:** the title now says "on 18 shards (24 until 2026-11-03 …)". The same cell still says "the matrix goes from
12 to 24 shards", and the Status column names only PR #445 and PR #449. A reader of the row cannot tell which PR set
18. The new paired measurement appears only in the title, not in the MEASURED column, where the old "PREDICTED ~1055 s"
and "1,473 s" still stand as the current numbers.

**Fix:** add "PR #484 (18 shards, 2026-11-03)" to Status, and add the 1,194 s / 1,704 s pair and slowest 1,184 s to the
measured cell.

### L3 — Low — the quiet-queue result is stated as a property of the change; the busy-queue case is not measured

**Where:** `docs/dashboard-entries.md` (2026-11-03 entry, first line), and the #415 row's DONE cell.

**Scenario:** at N=18 a lone PR run uses exactly 20 of 20 slots. Any other run alongside it, such as a master push after
a merge or a second PR, now queues shards at both N. The #415 row itself warned that a quiet and a busy measurement
"can disagree", and only the quiet one was taken. The dashboard's tech paragraph and the body sentence do say "with
nothing else running", so this is honestly scoped. But the opening line, "now reports about eight minutes sooner", is
unconditional.

**Fix:** optional. Put "when nothing else is running" into the first sentence. The busy-queue case can be filed if
anyone cares to measure it.

## Not findings (refutation attempts that failed)

- **A shortened list with a stale denominator:** impossible by construction. `job-total` is derived from the list.
- **An empty shard at N=18:** `shard_refusal` returns None for all 18 at 3,313 entries. The smallest shard holds 184.
- **A required check that depends on N:** `mutation-sweep-complete` has a stable name and reads the aggregate result.
- **The step skipped silently, so a shard "succeeds" in seconds:** the durations (mean 993 s) show that the sweep ran on
  every shard in the N=18 run.

VERDICT: CONVERGED
