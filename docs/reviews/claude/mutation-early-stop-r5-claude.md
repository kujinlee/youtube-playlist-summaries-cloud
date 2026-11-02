Reviewed head: fa778c504f65aba15ee73863ad38554f00e9806b

# Round 5 — `mutation-early-stop` (draft PR #476, backlog #405) — Claude half

Subject: the r4 narrowing in `scripts/check-plan-code.py` (`early_path_allowed`, `early_must_run_full`,
`early_stop_ci`, the `run_mutations` call site), `scripts/mutations/check-plan-code.json`, and the `ci.yml`
comment. Read first: `docs/reviews/coordinator/mutation-early-stop-r4-coordinator.md` and `git diff 9b9944e2..fa778c50`.

Mandate: refute *"a changed-path set made only of docs, `*.md` and `scripts/mutations/*.json` cannot make
early stop record a mutant KILLED that a full run records SURVIVED."*

`python3 scripts/check-plan-code.py --self-test` at this head: **362/362 passed**, rc 0.

The reproducers live in this session's scratchpad (`$SCRATCH`), which is not committed. Each one imports
`check-plan-code.py` and calls `run_mutations` on a temp tree, in the same shape as the self-test's `_d405` fixtures.
The suite source for each is described inline below, so it can be rebuilt as a self-test case.

```yaml
round: 5
subject: mutation-early-stop
findings:
  - {id: C5-B1, severity: Blocker, fix_induced: false, component: stop-rule}
  - {id: C5-M1, severity: Medium, fix_induced: false, component: stop-rule}
  - {id: C5-L1, severity: Low, fix_induced: true, component: self-test-timing}
  - {id: C5-L2, severity: Low, fix_induced: true, component: self-test}
```

## Findings

### BLOCKER C5-B1: the allow list rests on "a doc cannot change what a printed red exits with". That is false for any suite that READS a staged doc, and early stop then records KILLED where full records SURVIVED.

The r4 docstrings say it in two places: `early_path_allowed` (line 860, docs, `*.md` and manifests are "paths that
cannot change what a printed red exits with") and `early_must_run_full` (line 896, "can change WHICH case goes red,
never what a printed red exits with"). r1 already rejected predicting this from source ("a parsing surface with no
end") and replaced it with the principle *early stop only where master's full sweep measured the same thing*. But the
principle as written covers "the same file, the same manifest entries, the same code". It does not cover the same
DATA. `HARNESS_TREE` stages `docs`, `.agents/skills`, `.claude/hooks`, `.github/workflows` and `supabase`, all of
them whole. Every `*.md` in them is readable by every suite, and 69 of the 86 manifested scripts mention `docs`
paths. Whether a suite's exit status or its case list depends on what it reads is the same unbounded source question
r1 retired. The allow list only moves it from code to data.

**Reproducer, run** (`$SCRATCH/r5/repro.py`; the tree is assembled the way the self-test's `_d405` is). `tgt.py`
has the `_slow` shape, plus a trailer that reads `docs/policy.md` and returns 0 when it says `WARN-ONLY`, a
warn-only switch. The mutant is `return 1` -> `return 2`, expecting `value is one`. The PR changes
`docs/policy.md` and adds `scripts/skills/b.md`, both allowed paths.

```
R1 master FULL True [(True, None)] []                                   # killed on master
early_stop_ci: (True, 'a pull request that changes only docs, markdown and manifests: EARLY STOP ...')
must_run_full tgt/gen: False False
R1 PR FULL  ok= False [(False, None, None)] survivors= ['value is two'] # FULL: SURVIVED
R1 PR EARLY ok= True [(True, 'sigint', None)] survivors= []            # EARLY: KILLED, gate green
```

That is the r1 reproducer (*a trailer ending `return 0`*) with the trailer's input moved from code into a staged doc.

**Why the existing coverage does not close it.**
- **#173 does not cover it.** Backlog #173 (`SWEEP_SKIP_ROOTS = ("docs",)`) does already accept that a docs-only
  PR goes unmeasured. But that exemption is `docs/` only. A `*.md` under `scripts/`, `.agents/skills/`,
  `.claude/hooks/`, `.github/workflows/` or `supabase/` is in a sweep-relevant root, so that PR sweeps, and early
  stop lets it through. Its kill would have been wrong. The repo has never exempted those paths.
- **No production instance was found.** A one-line heuristic found none: a `return 0/2` or `sys.exit(0/2)` on a line
  that reads a file or names a `.md`, across the 86 manifested scripts. That search was not exhaustive. This is the
  same standing as r4's X4-B1, which was constructed with no production instance and was rated BLOCKER.
- **Master's push sweep is post-hoc.** It re-measures after merge when a relevant root changed, as with every
  early-stop wrong kill. The PR gate is still green when it should be red.

**Fix options (a decision, so stated, not chosen):**
- **(a) Make the principle the staged tree.** Early stop only when no changed path is under `HARNESS_TREE` except a
  manifest. Manifests are read by the harness's own suite, so `scripts/check-plan-code.py` would also need to run
  FULL. That leaves early stop with almost nothing to apply to: a manifest-only PR. Measure that, and reconsider
  whether #405's speed-up survives at all, before folding.
- **(b) Keep the allow list and state the bound honestly.** Replace the two "cannot change what a printed red exits
  with" sentences with the trust actually extended: "no suite's exit status or case list depends on a staged doc".
  Mark it as an owner-accepted bound alongside #173. Ideally also add a mechanical tripwire. For example, a mutation
  run could fail if a suite's self-test opens a staged `*.md`, observed by the harness with an audit hook in
  `mutation_env`, not predicted from source.

### MEDIUM C5-M1: a doc that generates a DUPLICATE case name. Full reads the `expect` as ambiguous (red); early stops at the first copy and records it attributed (green).

The file's own bound (3) lists "a later duplicate of the named case makes the `expect` ambiguous". Before r4 that
was covered only because a change to the suite's own source forced FULL. A suite that builds case names from staged
docs (`for md in skills/*.md: case(f"{title} ...")`) can get the duplicate from an allowed path alone.

**Reproducer, run** (`$SCRATCH/r5/repro2.py`). `gen.py` generates one case per `skills/*.md`, sleeping 1 s between
cases. The PR adds `skills/b.md` with the same title as `a.md`.

```
R2 master FULL True [(True, True)] []
R2 PR FULL  ok= False [(True, False, None)] ["... `expect` 'alpha value is one' matched 2 red case(s) ..."]
R2 PR EARLY ok= True [(True, True, 'sigint')] []
```

This is not a wrong KILL as the mandate defines one: full also records `caught`. But the gate verdict flips from
red to green, so it is the same family as C5-B1 and the same fix covers it. Without the inter-case sleep, early also
saw both lines before the SIGINT landed. So this is timing-dependent, which is one more reason it should not be
left to chance.

### LOW C5-L1: the BUFFERED mutant's runtime sits close to `SUITE_TIMEOUT`. The failure is LOUD, never a wrong kill.

**Measured.** The tree is a `git archive` of this head, and the mutant is applied to a copy of the file. Both runs
were on this laptop, one after the other, with other agents running.

| run | wall time | result |
|---|---|---|
| unmutated `--self-test` | 59 s | 355/362 |
| BUFFERED mutant (`-u` dropped) | **110 s** | 356/362; the expected case `#405 run_suite_early stops at the named case with SIGINT, before the suite ends` is red, so it is attributable |

**The failures in both runs, and what they say.**
- **Three failures in each run are the copy's, not the code's.** The archive has no `node_modules/typescript`
  (the `HARNESS_TREE` cases). The real staged tree has it, and the archive's base time is probably a few seconds
  low for that reason.
- **The unmutated run also failed four SIGINT cases with `sigkill`.** On this machine under load, the child did not
  exit inside `STOP_GRACE`. My run in the worktree passed 362/362, so this is load-sensitivity, not a defect. It is
  the same direction as the timeout risk.

**Is it real?** Yes, by 10 s of margin. The harness runs this mutant in FULL: `edit_needs_full_run`, and the file is
a changed `.py`. So it is bound by `SUITE_TIMEOUT = 120`. On a slower or contended CI runner, 110 s becomes more than
120 s, which is rc 2, NOT CHECKED, and a voided shard. That direction is loud: the gate goes red and never records a
false kill. So it is LOW, a flake risk, not a soundness one.

**Where the time goes.** The disabled stop makes every early-stop fixture wait out its whole sleep. The largest
single wait is `slow.py`'s `SLEEP 20`. Its case only needs it to exceed the `< 10` s stop bound. The r4 additions
(`nmt.py`, `zq.py`, `SLEEP 2` each) added more.

**Cheap fixes, in order of cost:**
1. **Lower `slow.py` from `SLEEP 20` to `12`.** It still exceeds the `< 10` s bound, and it saves about 8 s per run
   that waits on it. That is one literal.
2. **Make the stop observable without a long sleep.** Pass an explicit short `timeout=` to the direct
   `run_suite_early` cases, as the hang case already does with `timeout=0.5`. Then a disabled stop costs at most that
   timeout, never the fixture's sleep.
3. **Give `run_mutations` a test-only `suite_timeout` passthrough** for the fixture runs. This is the most general
   fix, and it is a new seam.

### LOW C5-L2: the remaining `early_must_run_full` cases for "the target file itself" and "a shared module" now hit the same `.py` refusal arm.

`#405 ...the PR changed the target file itself: FULL` and `...a shared module the source imports (fixture_git):
FULL` both go True through `early_paths_outside`. The per-file rule has no own-file or stem arm left, so the two cases
duplicate each other and the `.py` refusal cases. The fold deleted `early_stop_ci`'s check-plan-code arm for exactly
this kind of masking, and the per-file cases were left. This is harmless; they are now names for one assertion.

## Checked and clean

- **Manifest for one file whose entries mutate another.** Blocked. `load_manifests` derives the target from the
  manifest FILENAME (`scripts/<stem>.py`) and refuses any entry whose `file` disagrees, so a changed
  `scripts/mutations/a.json` can only add entries for `scripts/a.py`, which `early_must_run_full` sends FULL.
- **Path-normalisation tricks against `early_path_allowed`.** None reach it. CI passes `git diff --name-only -z
  --no-renames`. `changed_from_nul` refuses non-NUL input, and `-z` emits no C-quoting. `PurePosixPath` folds `.`
  and `//`, and git never emits `..`. A case variant (`x.MD`, `x.PY`) is REFUSED, which is the safe direction. A
  `.py` or `.pth` under `docs/` is refused before the docs arm. A rename lists its source.
- **Dead code and orphaned anchors.** None found. `EARLY_STARTUP_NAMES`, `early_sources`, `early_close_changed`,
  `early_names_stem` and `EARLY_SOURCE_SKIP` have no remaining reference outside historical comments
  (`check-plan-code.py:1769,1773`, `EXPECTED_MUTATIONS` notes). The manifest has 198 entries, matching
  `EXPECTED_MUTATIONS`, and every edit anchor occurs exactly once in the source (scripted count, 0 missing, 0
  duplicated).

VERDICT: NOT CONVERGED
