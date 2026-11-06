Reviewed head: 8972ed35c1de9b4b8b5b556234be338805bc51f3

Adversarial Claude half, round 1, of `seed-varied-sweep` (backlog #506, the class check). I tried to make the harness
report a seed-dependent mutant as killed, or report green when a seed did not run. Those attempts held: the seed reaches
the child (`mutation_env` sets `PYTHONHASHSEED` in a fresh env per `subprocess.run`, and `fixture_git.PROCESS_PASSED`
forwards it to the grandchildren it spawns). `check-main-drivable`'s `_memo_by_node` and `functools.lru_cache` live inside
one child process, so no memo is reused across seeds, and `child_env` sets `PYTHONDONTWRITEBYTECODE`, so no bytecode cache
is reused either. An rc 2 under any seed makes the mutant a cannot-run before any kill is read. The control and re-control
run under every seed (`control_parts`). PRs get no `--seeds` and keep `timeout-minutes: 30`. The scheduled seed
`1 + RUN_ID % 4294967295` is never 0 and never repeats 0. A red or timed-out scheduled sweep reaches `sweep-red-alert.py`,
which files on any `SWEEP != success`. I found one real defect, in the opposite direction from the one asked about: the
"killed by DIFFERENT cases" rule is stricter than the property it is meant to protect. Measured on the very mutant
backlog #506 fixed, it will raise a false NONDETERMINISTIC red on roughly 1 nightly in 150. It fails closed, so it is not
a BLOCKER, but it is a recurring false alarm on the one channel (the `sweep-red` issue) that has to stay believed.

## Findings

### MAJOR 1: the "different cases" rule turns a deterministic kill into a NONDETERMINISTIC red (measured on #506's own mutant)

`seed_outcome` (scripts/check-plan-code.py) says a mutant killed under every seed but with a different SET of red cases
is NONDETERMINISTIC, because "which case kills it is luck, so the `expect` attribution is luck too". That is true only
when the `expect` case itself is red under some seeds and not others. When the `expect` case is red under every seed and
only an incidental case varies, both the kill and its attribution are deterministic. The rule still reds the shard.

**Concrete failing input (measured, temp copy, never in place).** The mutation "scope_lead's tied names lose their stable
order, which the reader prints" (`scripts/mutations/check-review-decision.json`; its anchor binds exactly once). Its
`expect` list includes the new case `backlog #506: tied names given in REVERSE order still come back sorted, under every
hash seed`. I ran the mutated `check-review-decision.py --self-test` under PYTHONHASHSEED 0..599:

- 596 seeds red the same three cases: the new #506 case, `...and the tied names are reported in a stable order...` and
  `the reader says NO LEAD and lists the tied names on a second line`.
- 4 seeds (266, 312, 342, 449) red only the new #506 case.
- rc is 1 under all 600, and the `expect` case is red under all 600, so the #506 fix works.

I fed the real outputs at seeds (0, 266) to the delivered `seed_outcome`. It returned
`1 killed under every seed, but by DIFFERENT cases: PYTHONHASHSEED=0: [3 cases]; PYTHONHASHSEED=266: [1 case]`.
`run_mutations` then puts the mutant among the survivors, sets `ok = False` and reports `mutation NONDETERMINISTIC`.

**Consequence.** The nightly runs seeds 0 and a run-id seed. Whenever that seed lands in this mutant's 4-in-600 set, the
shard goes red and the `sweep-red` issue is filed or commented, about 1 night in 150 from this mutant alone. That is the
defect class #506 set out to remove (a red that reflects luck rather than a coverage gap), moved from PRs onto the
nightly. Any manifest entry caught by more than one case, where one of those cases depends on hash order, has the same
exposure. I measured only this one entry; I did not measure how many others exist (inference, not measured).

**Fix direction.** Classify on the named cases, not the whole set. NONDETERMINISTIC when the mutant is killed under some
seeds and not others, or when the set of `expect` cases that are red differs between seeds (or, at minimum, when some
seed reds none of the `expect` cases). Pin it with this real shape as the adjacent negative: the same `expect` case red
under both seeds plus an extra case under one seed is an ordinary attributed kill. The current self-test case
`...killed under every seed but by DIFFERENT cases is NONDETERMINISTIC too` uses two disjoint sets, so it cannot tell the
two rules apart.

### MINOR 2: the two-seed path and its 60-minute budget are first exercised by the first nightly after merge

The shard estimate of about 2,400s at two seeds is labelled PREDICTED in `ci.yml`, which is honest. But the workflow has
no `workflow_dispatch` trigger and PRs never set `SEEDS`, so nothing before merge runs the `SEEDS=...` shell branch or
`${SEEDS:+--seeds "$SEEDS"}`. Nothing before merge measures the doubled shard time either. Failing input: if any shard
exceeds 3,600s, every nightly ends as a timeout. That is visible, because the alert fires on any non-success, but the
issue reads "sweep red", not "budget exceeded". Suggest one manual dispatch (or a `workflow_dispatch` that takes the
schedule path) to measure the time before it becomes the daily signal. I traced the shell expansion by hand and it looks
correct; that is not a run.

### MINOR 3: the NONDETERMINISTIC message names the hash seed as the cause even when the cause is something else

`seed_outcome` cannot tell hash-seed dependence from any other run-to-run variation. Thread timing is the other half of
#506 (`check-selftest-counts.py`). A suite whose red set varies by timing gets reported as "killed under
PYTHONHASHSEED=A but survived under PYTHONHASHSEED=B" and is told to "give it an order that is deterministic and NOT
sorted". In that case re-running `--seeds A,B` may not reproduce it. Suggest wording that says "differed between the two
runs (seeds A, B)" and suggests re-running before blaming the seed. I did not construct a timing-dependent mutant, so this
is an inference.

### Checked and held (no finding)

- All 21 new `check-plan-code.py` mutations (master→HEAD) bind their anchor exactly once. Each, applied to a temp copy of
  `scripts/`+`docs/`+`.github/` and run with `HOME` redirected and `PLAN_CODE_MUTATION_RUN=1`, goes rc 1 with a named
  `expect` case red (21/21).
- `parse_seeds` refuses one seed, a repeated seed, an empty element, a negative and >2**32-1. `--seeds` without
  `--mutate` is refused with rc 2.
- A red control under one seed refuses the run (NotMeasured), naming the seed. That is the forged-kill input, and it is
  covered by `⛔ #506 ADVERSARIAL`.
- On re-run of a failed nightly, GitHub keeps `run_id`, so the same seed recurs and the log's seeds reproduce it.

Self-test: `python3 scripts/check-plan-code.py --self-test` → 335/335 passed, rc 0 (36s, at this head).

VERDICT: CONVERGED
