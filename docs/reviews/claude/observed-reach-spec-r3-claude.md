Reviewed head: 1c6bcfdb0ed687e531db1f221a2ca567e975a144

# observed-reach-spec — round 3 — Claude half (adversarial, REFUTE mandate; the last round before the cap)

**Scope.** The spec `docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md` at `1c6bcfdb`, with the
round-2 fold's delta (`git diff 8ed9c9e7..1c6bcfdb -- docs/superpowers/specs/`) read line by line. Checked against
`shard_slice`, `load_manifests`, `harness_files` and the shard's control block in `scripts/check-plan-code.py`, the
`concurrency` block, triggers and `mutation-sweep` job of `.github/workflows/ci.yml`, and CI history read through
`gh run list` / `gh run view` (read only). Mandate and rules: the round-1 brief (no `.claude/plans/`, no GitHub writes).

**Ran** (every script is in the session scratchpad, `fold586/`, and imports the REAL harness functions):

- `r3_owner.py`: the r2 owner rule (LOWEST-index shard whose `shard_slice` holds an entry) on the real 4,505 entries,
  N=24, with the spike's per-target `secs` from `observed.json`.
- `r3_cov.py`: every one of the last 45 first-parent master commits against its `push` CI run.
- `r3_lag.py`: for every `pull_request` CI run since 2026-11-03, the newest master commit whose push run had FINISHED
  GREEN when the PR run started, and with the harness-hash rule applied (`r3_lag.out`, `r3_lag_post_c85.out`).
- `r3_harness.py`: how many of the last 45 master commits change a `harness_files` member.
- `r3_lagk.py` + `r3_opts.py` (`opts.py` with `name()` memoised, no rule changed): the 30-commit loop at R = BASE~k,
  the harness-hash check ON (`r3_lagk.out`).
- `git diff --name-status` of the four commits that zero the lag-1 column; a one-line `sys.addaudithook` probe of the
  `import` event (`python3 -I`).

## Findings

### F1 — HIGH — §2 Record, the owner rule — CAUSED BY THE ROUND-2 FOLD

**The r2 owner rule puts 68 of 91 recordings on shard 1.** `shard_slice` is `muts[index - 1::total]` over entries that
are contiguous per target (its own docstring: "EVERY ENTRY OF ONE FILE IS CONTIGUOUS"). Any target with at least N
entries therefore has an entry in EVERY shard, and its "lowest-index shard" is always shard 1. MEASURED (`r3_owner.py`):
49 of 91 targets have ≥ 24 entries; owners per shard =
`[68, 2, 1, 1, 3, 1, 0, 2, 2, 1, 1, 1, 1, 1, 1, 1, 2, 0, 2, 0, 0, 0, 0, 0]`. Weighted by the spike's local `secs`,
shard 1 carries **553 of the 602 s** of recording; the next heaviest carries 15 s.

That contradicts §2's own cost line ("about 602/N s per shard", left unchanged by the fold), and it lands on a job
with no room: `ci.yml`'s matrix comment records the slowest shard at 1,499 s, mean 1,300 s, against a 30-minute
timeout, and three of the last 45 master runs already had a cancelled shard (`42387350733`, at the 30-minute
timeout by `ci.yml`'s own comment; `42432602877`; `42377549561`). INFERRED (local seconds, not CI): shard 1 + ~553 s is over 1,800 s on a mean shard, so the
recording pass would time out shard 1 on most master pushes. A timed-out shard cancels the master sweep (a red
master) AND, by §2 Store, means no `readsets.json` is ever saved — the feature would both red master and never
record.

**Fix.** Owner = the shard holding the target's FIRST entry (`index of first entry mod N`, plus 1). It is still a
shard whose slice holds one of the target's entries, so it ran that target's real control (r2 Codex F2 stays
closed). MEASURED with the same script: owners per shard
`[2, 5, 2, 1, 4, 3, 4, 3, 8, 5, 6, 2, 5, 4, 4, 4, 4, 3, 5, 2, 4, 5, 2, 4]`, heaviest shard 115 s of recording
(local). Add to §8.4: "a recording pass whose per-shard seconds exceed X" or "owners concentrated on one shard",
and state that the recording pass needs its own time budget inside `ci_deadline`, or the job's
`timeout-minutes` raised by it.

### F2 — MEDIUM — §5 lag-1 bullet and §5's conclusion — CAUSED BY THE ROUND-2 FOLD

**The cause the fold gives for the four lag-1 zeroes is not the measured cause.** §5 says: "4 of the 15 commits get 0
usable sets, because an addition under `scripts/` over R..BASE makes every traceable set stale (all of them list
`scripts`)." The four zeroes (with the harness check OFF, as the fold scored it) are 4a6f1577, 311d3631, fcf00068 and fb2a7e4b (`loop_r2.out`, third column). Their
R..BASE commit is, in each case, BASE itself: 8e052493, bd1284b4, 1d5fd219, c85a10ba. `git diff --name-status`:

| R..BASE commit | changes `check-plan-code.py` (harness) | adds under `scripts/` | what zeroes it |
|---|---|---|---|
| 8e052493 | yes | `scripts/ci-durations.py` | the harness hash (the scorer had `--ignore-harness` on) |
| 1d5fd219 | yes | `scripts/batch-ci.py` | the harness hash |
| c85a10ba | yes | `scripts/mutations/expected_mutations.py` | the harness hash |
| bd1284b4 | no | **nothing** (adds only `docs/reviews/**`) | `scripts/fixture_git.py` MODIFIED; all 43 traceable sets read it (MEASURED in `observed.json`) |

So three of the four are harness changes, which make ANY older recording unusable by §3's hash row regardless of
the listing row, and the fourth is a shared-module modification with no addition at all. MEASURED
(`r3_cov`-style loop): only **5 of the last 45** master commits add or delete anything under `scripts/`, and three of
those five are the harness commits above. The fold's lag-1 column was produced with the harness check switched off,
so its sentence explains the zeroes by the one rule that did not need to fire. And with the check ON the column
itself moves: 7 of 15 zero, B 48 / 807, not 41 / 726 (`r3_lagk.out`). Q1's "41 at lag 1" quotes the hash-off
figure as if a lag-1 recording could reach it.

This matters to the owner because it points at the wrong lever. "Rarely add scripts" is not the condition the
design depends on; **a recording at every master push** and **harness changes resetting every recording** are.

**Answer to the coordinator's question (is §3's listed-directory row stricter than its reason?).** Yes, and it is
also redundant. §3 row 4 already takes added and deleted paths over R..HEAD, and Use 3(b) picks a target when such a
path lies under its `listed`. A file added over R..BASE under a walked directory is therefore an `A` in R..HEAD, and
3(b) PICKS the target. r1 Claude F4's hole (a later-added file the PR modifies) is closed by that pair alone. The
listing row only converts a definite pick into the naming fallback, which can pick FEWER, since naming sees only
the BASE..HEAD paths. It is not less safe than today (fallback is today's rule), but it is not needed for its reason.
It does NOT recover any saving if removed: a `scripts/` addition still picks all 43 traceable targets via 3(b). Not
caused by the r2 fold (both rows are r1's).

**Fix.** Report the lag-1 column with the harness check ON (48 / 807 for B), and rewrite the bullet: the four hash-off zeroes are three harness changes and one modification of
`fixture_git.py`, which every traceable set reads. State that the scorer's lag-1 column ignores the harness hash,
and that the harness hash is what resets the recording in practice (F3). Either delete the listed-directory row,
stating that row 4 + 3(b) cover it, or keep it and say why. Optional, for later: the `scripts` listing is the import
system's, and the `import` audit event names the module even for a FAILED import (MEASURED here: a failed
`import zz_no_such_mod` raised `('import', 'zz_no_such_mod')`). Recording attempted top-level names would let a
new `scripts/foo.py` pick only suites that tried to import `foo`.

### F3 — MEDIUM — §5 and §7 Q1/Q4: the cadence the saving depends on is stated, but not measured, and it was measurable

The fold concluded that "the saving needs a recording at, or very near, nearly every master commit". The question
the owner needs answered is whether that cadence exists. It can be measured from CI history today, and it is
partly favourable and partly not:

- **The recording point exists at every master commit.** MEASURED (`r3_cov.py`): all 45 of the last 45 first-parent
  master commits got a `push` CI run. `concurrency` never cancels a push (`cancel-in-progress` is
  `github.event_name == 'pull_request'`), and a push runs the WHOLE manifest. 35 of 45 were green. 10 were not:
  7 red with every shard finished, 3 with a cancelled shard (job results read with `gh run view`; all 10 are
`mutation-sweep` shards, none is `verify`).
- **A PR's BASE is the master tip when its run starts.** A `pull_request` run checks out `refs/pull/N/merge`
  (`actions/checkout` has no `ref:` in `mutation-sweep`), whose first parent is the current master tip, so
  `git merge-base origin/$BASE_REF HEAD` is the newest master commit. Master's run takes 40-60 min (createdAt →
  updatedAt in `gh run list`), so any PR run started inside that window cannot see its base's recording.
- **Lag, if every green master push saved a recording at the end of its run** (MEASURED from run timestamps, 113
  `pull_request` runs after `c85a10ba` moved the pins out of the harness; `r3_lag_post_c85.out`): lag 0 for 42 (37%),
  lag 1 for 54 (48%), lag 2 for 11 (10%), lag 3-4 for 6 (5%). **With the harness-hash rule applied**
  (`ci.yml` + `check-plan-code.py`; `coverage_verdict.py`, the third member, was not included, so this undercounts
  misses): **83 of 113 runs (73%) have a usable recording (42 at lag 0, 41 at lag 1), 25 (22%) miss** because a
  harness change lies between the newest finished recording and BASE, and 5 are usable at lag 2.
- **The harness changes on about 1 master commit in 4 to 1 in 3.** MEASURED (`r3_harness.py`): 24 of the last 45 master
  commits change a harness file, but that count is dominated by the case-count pin table that lived inside
  `check-plan-code.py` until `c85a10ba` (e.g. 54089125's whole change is `"scripts/goal-tree.py": 282 → 297`). Since
  `c85a10ba`: 5 of 18 commits.
- **At lag 1 about half the saving survives; at lag 2 little does.** Re-scored with the harness-hash check ON
  (`r3_lagk.out`; the fold's column had it off), over the same 15 non-FULL commits: lag 1, 7 of 15 commits get 0
  usable sets (6 harness misses + 311d3631's `fixture_git.py`), B median 48 / total **807**, D 53 / 841, A 65 / 996;
  lag 2, 10 of 15 zero, B 64 / **891**. Against today's 67 / 1,014 and the footprint's 40 / 637: the B saving is
  377 picks at lag 0, 207 at lag 1, 123 at lag 2 (INFERRED: the spike's reads stand in for each R). This loop's
  harness-miss rate (6 of 15) is higher than the PR-run rate above because it treats master commits, 13 of 30 of
  which are FULL, as the PRs.

**So the design is viable, but only under a cadence the spec should name as a dependency**: a recording saved by
EVERY master push (the push already runs the full sweep, so the cost is the recording pass alone, F1), usable at
lag 1 (most PR runs see lag 1, not 0), with roughly a fifth of PR runs getting no saving because a harness change
is in flight. INFERRED, not measured: the per-PR saving on those PR runs, since the spike's reads are one tree's.

**Fix.** Replace "needs a recording at, or very near, nearly every master commit" with the measured statement above
(numbers and labels), and make the dependency explicit in §7: Q5 or a new line, "the saving exists only while every
master push records; a harness change resets it for ~50 min". Q4's shadow mode then measures the real fallback rate
against this prediction. One lever the spec does not weigh: the recording's validity hash is the WHOLE
`harness_files` set, so any `ci.yml` edit resets every recording (23205db6's lag-1 miss is `ci.yml` alone). A
hash over what can change a suite's reads (`check-plan-code.py`, its top-level imports, the launcher, and the sweep
step's environment) would keep the verdict rule (`ci.yml` stays FULL) and stop unrelated workflow edits resetting the
recording. Whether the sweep step's env is a sound proxy for the workflow is the build plan's to show.

### F4 — MEDIUM — §8.4 / §2 Store: "a green-sweep condition" is undefined, and a red master is common

§8.4 refuses a `readsets.json` saved with "a green-sweep condition unmet"; §2 Store requires that "every shard's
sweep finished". Neither says whether a sweep that FINISHED with a survivor saves a recording. It matters: 7 of the
last 45 master sweeps were red with every shard finished, and red stretches cluster (11-06: 3 of 4 consecutive
commits red; 11-07: four in a row not green, `1d5fd219` … `f7ff7eb0`). If a red sweep saves nothing, the saving
disappears for the whole stretch, which is when master is red for 1-3 days by backlog #560's own row. §3's reason
needs only that each target's CONTROL was green with its case count and that every shard finished; a survivor in
another target's mutant does not touch any control's reads. Not caused by the r2 fold (the phrase is round 1's).

**Fix.** Define it: save when every shard FINISHED (none cancelled or timed out) and keep a per-target set only when
that target's control was green with its count; a survivor does not block the save. Case it in §8.4 with a
red-by-survivor sweep that saves, and a cancelled shard that does not.

### F5 — LOW — §8.5 and Q4: when the comparison is evaluated is unstated — CAUSED BY THE ROUND-2 FOLD

§8.5 makes "a missing base artifact" INCONCLUSIVE. By F3, a PR run usually starts before its base's full sweep
has finished (63% of runs are at lag ≥ 1), and 10 of 45 base sweeps did not finish green. If the comparison is
evaluated when the PR's sweep ends, most PRs are INCONCLUSIVE and the 20 COMPLETE PRs take far longer than 20 PRs.
If it is evaluated later, against the base's finished sweep, it is fine.

**Fix.** Say the comparison is evaluated after BOTH sweeps have finished (e.g. by the base's
`mutation-sweep-complete`, or the next scheduled run), and that a base sweep cancelled for timeout is INCONCLUSIVE
while a red one with per-mutant verdicts is comparable.

## Numbers in §5 and §7 — labels checked

| Claim | Label | Checked |
|---|---|---|
| Strict: 0 usable sets on every scored commit; 14 fail ancestry, `4a6f1577` and this spec's PR fail the hash | MEASURED | ✅ matches `loop_r2.out` column 2 (14 ancestry misses + 4a6f1577 hash miss = 15) |
| Footprint table (36/65/61, 65 (879), 45 (676), 40 (637); today 64/68/64, 67 (1,014)) | INFERRED / today MEASURED | ✅ labels right; reproduced by Codex r2 |
| Lag 1: 65 (988), 46 (774), 41 (726) | INFERRED | ⚠ reproducible, but only with `--ignore-harness` ("harness hash assumed equal"); with §3 applied it is 65 (996), 53 (841), 48 (807). The CAUSE sentence is wrong (F2) |
| "4 of the 15 … because an addition under `scripts/`" | presented as fact | ❌ F2 |
| 15 run ALL: 13 harness/workflow, 2 shared modules | MEASURED | ✅ consistent with the loop (15 FULL rows) |
| 76 against 67 on one commit (fb2a7e4b) | footprint | ✅ |
| 33 of 36 picks are spawners | MEASURED reads, INFERRED pick | ✅ label |
| r2 probe rule adds 0 picks | MEASURED | ✅ plausible: `probes()` collects only failed opens of non-repo paths |
| 602 s serially, "about 602/N s per shard" | INFERRED | ❌ under the r2 owner rule shard 1 carries 553 s (F1) |
| 27 of 91 `index mod N` owners run no control | MEASURED | ✅ re-derived by the coordinator; my `r3_owner.py` uses the same slice |
| Q1: "40 median against today's 67; 41 at lag 1" | INFERRED | ✅ |
| Q3: 50 = 47 + 3 | INFERRED | ✅ arithmetic |
| Q4: below 14% at 20, below 45% at 5 (95%) | arithmetic | ✅ 1 − 0.05^(1/20) = 0.139; 1 − 0.05^(1/5) = 0.451 |
| §6: 40 of 90 reusable at the strict rule | INFERRED | ✅ label |

## The round-2 findings — fixed?

| r2 finding | Fixed? | Note |
|---|---|---|
| R2-X1 probed modification | ✅ | Use 3(a) now matches `A`/`M`/`D` against `reads` ∪ `probed`; §8.3 cases size and mode bits with a negative |
| R2-X2 owner without a control | ✅ for the stated defect, ❌ new defect | the new rule always has a control, but concentrates 68 of 91 owners on shard 1 (F1) |
| R2-X3 scorer eligibility | ✅ arithmetic, ⚠ claim | three scorings, labelled; the lag-1 explanation is wrong (F2) and the cadence it concludes is unmeasured (F3) |
| R2-X4 missing comparison | ✅ | §8.5 added; its evaluation time is unstated (F5) |

## Fix-caused, for the thrashing watch

F1, F2 and F5 are in text the round-2 fold wrote (the owner rule, the lag-1 cause sentence, §8.5). Round 2's four
findings were all caused by round 1's fold. **This is two consecutive rounds of fix-caused findings in one component,
so the Phase 6 arming condition (`docs/dev-process.md`, *The arming condition is thrashing*) fires.** F3 and F4 are
not fold-caused: F3 is an omission (the cadence was measurable), F4 is round 1's phrase.

## Could not check

- No CI run of a recording pass: the per-shard seconds are the spike's LOCAL `secs`, so F1's timeout is INFERRED.
- F3's lag assumes a recording is saved at the end of a green push run (`updatedAt`) and that `sweep-select` runs at
  the PR run's `createdAt`; queue time in either direction moves it. "Green" is the run's conclusion; the 10 non-green
  were confirmed sweep failures/cancels by `gh run view`.
- F3's harness misses use two of the three `harness_files` (`coverage_verdict.py` not included): they undercount.
- Whether a PR's diff in the scored runs was itself FULL (a harness PR saves nothing at any lag) was not separated.
- The spike's reads are one tree's; no read set at any historical base exists, so every per-PR saving stays INFERRED.

VERDICT: NOT CONVERGED
