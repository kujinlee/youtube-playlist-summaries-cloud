# Round 3 — `observed-reach-spec` — coordinator

```yaml
round: 3
fixes_nontrivial: true
subject: observed-reach-spec
halves:
  codex: gap
  claude: ran
findings:
  - {id: R3-C1, severity: High, aim: deliverable, fix_induced: true, component: observed-reach-spec, disposition: fixed}
  - {id: R3-C2, severity: Medium, aim: deliverable, fix_induced: true, component: observed-reach-spec, disposition: fixed}
  - {id: R3-C3, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R3-C4, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R3-C5, severity: Low, aim: deliverable, fix_induced: true, component: observed-reach-spec, disposition: fixed}
```

REDESIGNED → spec-586-redesign. The redesign this round introduced (the dedicated `record-reads` job, then the
owner's `strace -f` recorder) is reviewed as its own stream from round 1:
`docs/reviews/coordinator/spec-586-redesign-r1-coordinator.md`. That closes the REVIEW GAP below.

REVIEW GAP: codex — alternation

REVIEW GAP: redesign — round 3 is the last round (the round cap, `docs/review-method.md` §0 Q4c), so NO round 4
runs and no review round has seen this fold's redesign of the recording into one dedicated job. The gap is
closed by the owner's walkthrough of the spec (§7) and by the build plan's own dual review, which must take the
`record-reads` job as its first subject.

Claude half: `docs/reviews/claude/observed-reach-spec-r3-claude.md` (F1-F5, recorded here as R3-C1..C5), on
`1c6bcfdb`, NOT CONVERGED. Committed on its own as `6c7a1428`; the fold is the commit after it.

**Method.** Every finding was checked against `shard_slice`, `mutate_delivered`'s control block, `control_parts`,
`seed_runs` and `run_suite_parts` in `scripts/check-plan-code.py`, and the `concurrency` block, triggers and
`mutation-sweep` matrix comments in `.github/workflows/ci.yml`, never taken from the reviewer. The reviewer's
scratch scripts were re-run where a number moved. Two new scratch scripts (session scratchpad, `fold586/`):
`r3f_lag_dedicated.py` re-scores the reviewer's lag data with the save time of a dedicated job, and reproduces
the reviewer's figures as its control row (`M=None`: 42 / 41 / 5 usable, 25 harness misses, identical);
`r3f_opts.py` + `r3f_lagk.py` re-score lag 1 with §3's listed-directory row removed.

## The call: the arming condition is met

Round 2's four findings all came from round 1's fold (R2-X1..X4, `observed-reach-spec-r2-coordinator.md`). Round
3's F1, F2 and F5 sit in text round 2's fold wrote: the owner rule, the lag-1 cause sentence, and §8.5. That is
two consecutive rounds of fix-induced findings in one component, so the Phase 6 arming condition
(`docs/dev-process.md`, *The arming condition is thrashing*) is MET.

**Shape: BOTH.** One strand is thrashing and the rest is the prose floor, which `review-method.md` (*Non-convergence
means different things on a DOCUMENT and on CODE*) says can coexist. Per finding, with the single test, *can a
redesign remove it?*

| Finding | Caused by the previous fold? | Can a redesign remove it? | Kind |
|---|---|---|---|
| **R3-C1** (High), the owner rule loads shard 1 | Yes: r2's owner rule | **Yes** (below) | **mechanism** |
| **R3-C2** (Medium), the lag-1 zeroes blamed on `scripts/` additions | Yes: r2's sentence | No. It is a measurement attributed to the wrong rule, a sentence | editorial / measurement |
| **R3-C3** (Medium), the cadence was measurable and unmeasured | No: an omission | No. It is a missing measurement, now made | prose floor |
| **R3-C4** (Medium), "green-sweep condition" undefined | No: round 1's phrase | Partly: the dedicated job never reads the sweep, so the question loses its subject | under-specified |
| **R3-C5** (Low), the shadow comparison's evaluation time | Yes: r2's §8.5 | No. Any design must say when it compares | branch coverage |

**The coordinator's judgment, CONFIRMED with evidence: R2-X2 and R3-C1 share one cause.** Recording was coupled to
the SHARDED sweep, which forced the question *which shard owns a target's recording?* `shard_slice` strides over
ENTRIES (`muts[index - 1::total]`), so a target's entries scatter across shards, and an owner rule must satisfy
three things at once: the owner ran the target's control (R2-X2's failure: `index mod 24` owners ran none for
27 of 91, MEASURED in round 2), the load is spread (R3-C1's failure: lowest-index puts 68 of 91 owners and
553 of 602 s on shard 1, MEASURED by the reviewer's `r3_owner.py`), and the per-seed counts agree between
shards that ran the same control. Each fold satisfied one constraint and broke another. The finding lives in the
coupling, not in either rule, so the test answers YES: one dedicated, unsharded job dissolves all three.

**Why the redesign, not the reviewer's accretion.** The reviewer's own fix, owner = the shard holding the
target's FIRST entry, does pass both R2-X2 and R3-C1 (MEASURED by the reviewer: heaviest shard 115 s local). It
is a valid third patch. It was not taken, for four reasons the dedicated job removes and the patch does not:

1. **Shard headroom.** `ci.yml`'s matrix comment predicts shard 3 at N=24 at ~1,545 s, "INSIDE the 30m timeout
   by only ~14%". Adding up to 115 s to a shard spends most of that (INFERRED: local seconds).
2. **The save condition.** A shard-coupled save needs every shard to finish. 3 of the last 45 master runs had a
   cancelled shard (MEASURED, reviewer), and every one of those runs saves nothing.
3. **Cadence.** A shard-coupled save lands only when the sweep ends, 40-60 min after the push (MEASURED). The
   dedicated job does not wait. Re-scored with its save at the master run's start + 25 min, PR runs with a usable
   set rise from 88 to 101 of 113, and lag 0 from 42 to 82 (INFERRED: the 25 min is assumed; 20 and 30 min give
   102 and 101, `r3f_lag_dedicated.out`).
4. **Count reconciliation.** Per-seed counts across shards, and the merge of 24 partial artifacts, disappear.

Its cost: one runner for about 20 min (INFERRED: the spike's 602 s hooked plus one plain pass), and one more
queued job on a master push, which already exceeds the account's 20-job limit.

**The recording run is still equivalent to the controls: CHECKED against the code.** `run_suite_parts` runs
`[sys.executable, name, "--self-test"]` with `cwd=d` and `env=mutation_env(d, seed)`. `control_parts` runs that
per seed through `seed_runs`, each seed in its own `seed_trees` copy. `mutate_delivered` builds `d` with
`stage_tree(root, d)`, then makes `d / CHILD_HOME`, then `seed_trees`. The spec now requires the job to build its
tree by that same sequence and, per target and seed, run the PLAIN control exactly so, then the hooked run with
the same argv, `sys.path[0]`, `cwd` and env. It accepts a read set only when both are green by
`control_is_green` with equal case counts. Its count reference is therefore its own plain control, not a
shard's, which is why the cross-shard check could go. **One difference remains and is stated (§4.3):** a shard
runs only its own targets' controls in its tree, while the job runs all 91, so a suite's predecessors differ.
That is spike caveat 8's class (a suite writing into the shared tree), and it was already a stated bound.

## Dispositions

| Finding | Class | Disposition and evidence |
|---|---|---|
| **R3-C1** | REDESIGNED IN SPEC | §2 Record is now the `record-reads` job described above; the owner rule, the per-shard pass, the cross-shard count check and the artifact merge are gone. §2's cost line ("602/N s per shard"), which the reviewer showed false, is replaced by a whole-job estimate, labelled INFERRED and timed on the first CI run. §8.4 is rewritten for the job |
| **R3-C2** | FIXED IN SPEC | Verified: the round-2 scorer ran lag 1 with `--ignore-harness` (`loop_r2.sh`), and `r3_lagk.out` gives, with the hash ON, 7 of 15 zero: six harness misses and `311d3631` (`fixture_git.py` modified). The bullet now says so, and the column uses the hash-ON figures. **The listed-directory row is REMOVED**: the reviewer is right. A path added over R..BASE is an `A` in `git diff R HEAD` whenever it still exists at HEAD, so Use 3(b) picks the target; if it was deleted again by HEAD, R and HEAD agree and nothing is owed. The row only turned a definite pick into the naming fallback, which can pick fewer. Use 3(b)/(c) now say "over R..HEAD" explicitly, and §8.3's case now asserts a PICK. Re-scored with the row removed (`r3f_lagk.out`): lag 1 is unchanged, 7 of 15 zero, B 48 / 807, D 53 / 841, A 65 / 996 (MEASURED on the spike's reads); the footprint column has no R..BASE additions and cannot move |
| **R3-C3** | FIXED IN SPEC | The reviewer's CI-history figures were re-run (`r3f_lag_dedicated.py`'s control row reproduces them). §5 gains *The cadence the saving depends on*: MEASURED coverage (45 of 45 master commits ran), the lag distribution (37 / 48 / 15%), 73% usable at lag 0-1 with the harness hash, the dedicated job's INFERRED 89%, and the INFERRED saving by lag (377 / 207 / 123 picks). Q5 now asks the owner to accept the dependency. **Narrowing the validity hash: DEFERRED, with a reason.** Hashing `check-plan-code.py` alone raises usable runs only from 101 to 103 of 113 (INFERRED, same script), and soundness needs a proof of which workflow edits cannot change a suite's reads, which only the built job can give |
| **R3-C4** | FIXED IN SPEC | §2 Store defines the save: the job finished (not cancelled, not timed out) and every target is present with a set or a refusal; a red plain control refuses only its target; nothing in the sweep can block it. §8.4 cases a recording beside a sweep red by a survivor (saves), a cancelled recording job (does not), and a red plain control |
| **R3-C5** | FIXED IN SPEC | §8.5 states the comparison is evaluated after BOTH sweeps finished, by the next scheduled run over PRs merged since the last evaluation; until then PENDING, counted neither way; a base with a cancelled shard is INCONCLUSIVE, a red one with per-mutant verdicts comparable. ⚠ This deviates from the brief's "after the base's recording exists": the comparison is between two SWEEPS, and a PR's selection is fixed when it runs, so a later recording cannot change it. A PR whose selection found no usable set has no would-skip target and is not a sample. **Reachability, checked:** the 63% of PR runs that start before their base's sweep ends do not matter once evaluation waits. INFERRED: about 48 merged PRs (half run ALL, ~89% of the rest have a usable set, 42 of 45 bases finished every shard), roughly 6 days at the MEASURED 21 master commits in 2.5 days. Stated in Q4 |

## Verdict

**NOT CONVERGED, and STOPPED by the round cap.** One High, fix-induced, and non-trivial fixes (Q4a would
CONTINUE). From round 4, any finding is FILED unless it is a BLOCKER (Q4c), and no round 4 runs: the redesign is a
new mechanism, which a round-4 review could only file. The redesign's review is owed to the build plan.

What the three rounds show. The core claim (control reads are a sound basis for target-level skipping) was never
disputed. Every High was in the RECORDING's placement and bookkeeping, and the strand that thrashed was the
coupling of recording to the sharded sweep. The redesign removes that coupling instead of patching it a third
time. Decision log: this spec's row is closed with `outcome: stopped`, `rounds_at_termination: 3`, and its
`observed` field says the stop is the cap's, with an unreviewed redesign, not a repair a round confirmed.
