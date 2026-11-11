Reviewed head: 5ee0b6d778ed3074ab3cb86e83096949bd52759a

# observed-reach-spec — round 1 — Claude half (adversarial, REFUTE mandate)

**Scope.** The design spec `docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md` at `5ee0b6d7`,
its evidence `docs/reviews/measurements/2026-11-09-observed-reads-spike.md`, against the code it changes:
`select_manifests` and helpers, `run_suite_parts`, `child_env`, `stage_tree`, `shard_slice` in
`scripts/check-plan-code.py`, and the `mutation-sweep` / `mutation-sweep-complete` jobs in `.github/workflows/ci.yml`.

**Ran:**
- **Today's selector on the real tree** (91 manifests at this head), by importing `check-plan-code.py` and calling
  `select_manifests("pull_request", paths, …, sweep_sources(.), modules=module_sources(.))` from a scratch script:

| Changed paths | Picked today |
|---|---|
| PR #545's diff (`docs/backlog.md`, `docs/dashboard-entries.md`) | 64 of 91 |
| PR #543's full diff (17 files) | 68 of 91 |
| PR #543's 11 ADDED files only | **52** of 91 |
| ONE added review file, `docs/reviews/claude/answer-binds-file-r1-claude.md` | **52** of 91 |
| ONE brand-new `docs/zzz-brand-new.md` | **51** of 91 |
| This spec's own PR (5ee0b6d7: 4 modified + 2 added) | 64 of 91 |
| each of this PR's 2 added files alone | 51 of 91 |

- `git diff --name-only --diff-filter=AD` over the last 30 master commits up to 4a6f1577: **25 of 30 add or delete
  at least one file** (counts 0 11 36 0 2 24 11 2 27 21 21 18 8 5 11 0 15 17 0 21 19 28 17 14 18 17 12 15 6 31).
- Read `run_suite_parts` (:1255-1283), `child_env` (:179-249), `stage_tree` (:917-948), `select_manifests`
  (:764-831), the sweep step (ci.yml :1287-1317) and `mutation-sweep-complete` (:1319-1400), `sweep-red-alert.py`'s
  docstring and `red_body`, and backlog #560 / #586 rows.
- No CI run; no hooked run of any suite (the spike's scripts and data are not in the repository).

## Findings

### F1 — HIGH — §3 (added/deleted naming union) and §5 (expected saving)

**The fail-closed rule for ADDED and DELETED paths gives back most of the saving on the typical PR, and §5's
numbers do not apply it.**

§3 says every added or deleted path is ALSO run through the naming rule. For a new file nobody names yet, the naming
rule's last branch fires: `hit = {t for t, s in readers.items() if _quotes_dir(s, root)}` (`check-plan-code.py:820`)
— every target that quotes `docs`. Measured above: **one added docs file picks 51-52 of 91 targets**. 25 of the last
30 master commits add or delete files (review files, verdict JSONs, specs, measurement docs). This spec's own PR picks
64 under today's rule, and would pick at least 51 under the proposal (its two added files alone).

§5 says "The selection rows apply §2 and §3 to the spike's measured reads". For PR #543 they do not: its 11 added
files alone pick 52 by naming, so the union is at least 52, not 41. The spike's estimate uses its cache-hit rule
(listing only), not §3's naming union. The PR #545 figure (36) holds only because #545 added nothing — the
uncommon shape. §1's "none of the last 60 merged PRs changes only `scripts/`, so the docs-only shape is every PR's
shape" is a non sequitur: not-scripts-only is not docs-only-and-modify-only.

**Fix.** Either narrow the union for added/deleted paths to the namers of the literal path or its basename (drop the
root-quote fallback and the `between` directory quotes, which are not "a literal name"), and justify that against
§4.2; or rely on `listed` plus recorded failed opens (F5). Re-measure §5 on a PR with added files (#543, and this
spec's PR), with the rule as written. This trade is an owner decision, since it changes the soundness bound for
the saving. Add it to §7.

### F2 — HIGH — §2 Record ("Only the control is wrapped … a verdict is never computed under the hook")

**Wrapping the real control is not neutral, because the control is the gate for every verdict.** `run_suite_parts`
is the only producer (:1255) and runs `[sys.executable, name, "--self-test"]` (:1274). The control's green is what
makes a "caught" meaningful, and a red control is CANNOT RUN for that target (:2146). Its seconds price every mutant's
timeout (`control_seconds[name]` :2141 → `suite_limit` :2153, backlog #558). So putting the control under
`runpy.run_path` plus an audit hook changes:
- whether the control is green. The spike itself MEASURED one suite failing under the hook: `push-command.py`
  349/352, rc 1, cause unknown, never re-run unhooked;
- `sys.argv[0]`, `sys.path[0]` and `__main__` identity, which `runpy.run_path` from a launcher sets differently
  from a direct run;
- the control's seconds, so the mutant limits, which the spec admits were never timed.

A hook-induced red control on master turns that target CANNOT RUN on every full sweep. That is a red `sweep-red`
alarm caused by the recorder, not by a defect.

**Fix.** Record in a SEPARATE run that feeds neither `control_is_green` nor `control_seconds`: an extra hooked pass
on master only, after the shard's verdicts. Its rc and case count must equal the real control's, or that target
gets no read set. Time it on one full sweep before choosing.

### F3 — HIGH — §2 Store/Use, with `shard_slice`

**Each PR shard restores the cache on its own, so shards can select different sets and drop mutants.** Selection
is computed independently in every matrix shard (ci.yml :1306-1317). Then `shard_slice` splits the SELECTED entries
round-robin (:1582). Today that is consistent because every shard's inputs (tree, diff) are identical. With a cache
restore per shard, a master sweep that saves a newer `readsets-…` entry between two shards' restore steps gives two
selections. That happens easily: queued shards start minutes apart, and master's sweep completes continuously.
Two selections mean two different entry lists under one stride: some mutants are assigned to no shard, others to
two. That is a silent loss of mutants that even TODAY's rule would have run, which §3's "Nothing here can pick
fewer targets than today" denies.

Related: `actions/cache/restore` returns the newest entry by prefix and cannot filter by ancestry. So "the newest
entry whose `<sha>` is an ancestor of the PR's base" is not something one restore step can do.

**Fix.** Resolve the read set ONCE, in a job before the matrix, and pass the exact key and sha to every shard as
outputs. Each shard must refuse (and fall back to the naming rule for all) a restored set whose sha differs. Add a
self-test with an ADJACENT negative: two shards given different sets must not both proceed.

### F4 — HIGH — §3 staleness rule

**Staleness checks `reads` only, never `listed`.** Construct it this way:
1. Master's read set for target T is recorded at commit A. T walks `docs/reviews/claude/` and opens every file.
2. PR X merges, adding `docs/reviews/claude/x-r1-claude.md`. No full sweep has yet recorded a set past A, which
   is common: concurrency queues master runs and supersedes pending ones.
3. PR Y, based after X, MODIFIES `x-r1-claude.md`.

§3's staleness rule asks whether a path in `reads` changed between A and base. None did, because the new file was
not in `reads`. §2 rule 2 matches `listed` only for paths the PR ADDS or DELETES, and Y modifies. The naming union
covers added/deleted paths only. So T is skipped, although on Y's tree it reads the file Y changed.

**Fix.** A read set is stale if any path ADDED or DELETED between its sha and the base lies under a directory in its
`listed`. Add a §8.3 case with an adjacent negative: added under an unlisted directory stays usable.

### F5 — MEDIUM — §3 / §4.2 (existence), with the spike's filter

**Failed opens are dropped, but they are visible.** The `open` audit event fires before the open is attempted, so
`try: open(p) except FileNotFoundError` on an absent path IS observed. But the spike kept "only paths tracked under
the staged roots" (spike, caveat 5), and an absent path is not tracked. That throws away exactly the
existence-dependency evidence §4.2 says is missing. The same applies to an untracked path generated into the staged
tree by an earlier suite (caveat 8).

**Fix.** Record every attempted path under the staged roots, tracked or not, present or not. Match a PR's
added/deleted path against them. Solve `dir_fd` noise by resolving against the fd's directory, not by the
tracked-path filter.

### F6 — MEDIUM — §3 "The suite spawned nothing"

**"Spawned" is defined by argv kinds (git, python, node, shell), not by the full set of process-creation events.**
A `fork` without `exec` (`os.fork`, `multiprocessing`'s fork start method, `pty.fork`) runs the same image with the
hook installed. The reads happen in the child's memory, though, and are never written back, so they are lost.
`os.system`, `os.posix_spawn`, `os.exec*` and `os.spawn*` each have their own audit events.

**Fix.** Define the condition as "no `os.fork`, `os.forkpty`, `os.system`, `os.exec`, `os.posix_spawn`,
`os.spawn`, `subprocess.Popen` event", and case at least `os.fork` and `os.system` (the spike saw `fixture_git` call
`os.system`).

### F7 — HIGH — §7 Q4 (shadow mode) and §8.1

**The shadow-mode switch criterion cannot fire for the defect it is meant to catch.** In shadow mode the PR still
runs today's selection. Take a target the shadow WOULD have skipped, but which the PR broke: it ran on the PR, went
red there, and was fixed before merge. So "no shadow-skipped target was red on that PR's merge sweep" passes by
construction. The observable that tests the proposal is: **a shadow-skipped target that was RED (or whose verdicts
changed) on the PR's own sweep, at any push.**

Also:
- **5 PRs is a weak bound.** 0 events in 5 bounds the per-PR miss rate only below about 45% (rule of three, 95%).
  State the bound, or size the trial from it.
- **§8.1's detection has no data source.** It says "comparing the PR's logged selection with the `sweep-red`
  issue's targets", but `red_body` records only the sweep result, the event, the SHA and the run URL. There are no
  targets, and the alert only ever comments on one open issue. "The cause is the PR's change" is judgment. Master
  went red 12 times since 11-01 (backlog #560's row), so attribution needs a mechanism.

**Fix.** Use the PR-own-sweep criterion for Q4, state its bound, and make shadow mode log the would-skip set in a
parseable line. Make §8.1 mechanical: on a red master sweep, list the red targets from the shard logs, and
intersect them with the skipped sets of the PRs merged since the last green sweep.

### F8 — MEDIUM — §8.2 "No saving"

**A broken selector passes it.** A selector that skips EVERY traceable target, readers included, picks fewer than 64
and picks no traceable non-reader, so §8.2 passes. §8.3 tests only the fallbacks. Only §8.1, after merge, would see
it.

**Fix.** Assert the exact set for the PR #545 replay: the 33 spawners plus `check-canonical-source`,
`check-dashboard-entry` and `check-features` (spike table). Assert also that a traceable READER of a changed path is
picked.

### F9 — MEDIUM — §4 "INFERRED cost of a miss: one red master sweep and one fix PR"

The row it cites says otherwise: backlog #560 records "10 survivors = 3 distinct defects, each red 1-3 days". While a
defect stays unfixed, every later full sweep is red, and the single open `sweep-red` issue absorbs new reds as
comments. A new miss can therefore hide behind an old one.

**Fix.** Quote the row's figure as the cost of a miss, and note the masking under one open issue.

### F10 — LOW — §1 / §6 numbers

- "43 of 90 targets are traceable … 46 spawn and 1 failed" sums to 90 only if the failed one is not a spawner. But
  the spike lists `push-command` (the failed one) among the 46 spawners (python and shell-mixed lists). I counted 46
  unique names there, all with manifests, `push-command` included. So 43 + 46 = 89, and one target is unaccounted
  for, or double-counted. The spike's raw data is not in the repository, so I could not resolve it.
- §6 "MEASURED estimate … 40 of 90 reused" should be INFERRED: measured reads, rule applied by hand. That is how §5
  labels the same kind of figure.
- Every MEASURED read and spawn figure is from a LOCAL run, not CI. The spike blames "this local environment" for
  push-command's red. `child_env` copies `os.environ` (:221), so in CI `GITHUB_EVENT_NAME` and the other `GITHUB_*`
  variables reach the suites. Push-event reads recorded on master are then used for pull_request-event selection.
  The spike measured neither. Say so in §4.4.

Verified correct: 64−28 = 36 = 33 + 3; 68−27 = 41 = 35 + 6; "1 commit after #545, 4 after #543" (git log);
"67 of 89" on PR #539 (backlog #586 row); "12 red since 11-01" (backlog #560 row).

### F11 — LOW — §2 descriptions and the cache key

- §2 rule 1 says "a target's own manifest … Each of these runs ALL". In the code, a manifest path adds only its own
  target (`own = MANIFEST_PATH.fullmatch` :795 → `hit.add(target)`). Only the harness, the dependency manifests,
  a shared module and an unrecognised path run ALL.
- **The launcher's location and the "harness hash" are undefined.** `harness_files` is DERIVED from
  `check-plan-code.py`'s top-level imports. A launcher run as a subprocess (`audit_wrap.py`) is not imported, so a
  change to it would be neither harness nor in the key. Name the files the hash covers, and put the launcher in
  both.
- `push` also fires for `batch/**` (ci.yml :22), with fail-fast shards (:1081). The save must be limited to
  `refs/heads/master` and the schedule. A batch-branch cache is also invisible to PRs.
- Define "the PR's base" as the run's `origin/$BASE_REF` tip, which is the diff's base (ci.yml :1308). It is not
  the PR's original fork point.

### F12 — LOW — §7 owner questions

- Q3 (master-only recording) is an engineering decision. A PR run's tree is untrusted by the same argument the spec
  gives, so it needs no owner.
- Missing: F1's trade, between a narrower added-path rule (keeps the saving, widens §4's bound) and §3 as written
  (sound, little saving on PRs that add files). That one really is the owner's.

## What held up

- The target's own source and its imports do arrive as `open` events, so a PR changing T's code or a module T
  imports picks T (§4.4). That leaves only lazy imports in mutant-only branches (§4.1, stated).
- Harness-, workflow-, `stage_tree`-, `mutation_env`- and `HARNESS_TREE`-changes all live in `check-plan-code.py`
  or `ci.yml`, which `harness_files` makes FULL (:592-603), as before.
- Paths outside the staged roots are already ignored (:790), and reads are recorded only under them, so nothing
  regresses there. `node_modules/typescript` is covered by `DEPENDENCY_MANIFESTS`.
- The whole-manifest checks (`pin_drift`, `anchor_problems`, the home-escape scan) still run over every manifest in
  every shard, so a manifest-JSON anchor orphaned in another manifest is still caught.
- A PR can restore caches made on its base branch (master) and on the schedule, so the recording point is
  reachable — subject to F3.

## Could NOT check

- No hooked or unhooked run of any suite. The spike's `observed.json` and scripts are not in the repository, so
  every read set, spawn count and the 43/46/1 partition are taken from the report, unverified.
- No CI run. Cache scoping, eviction and the restore-ordering race (F3) are reasoned from `actions/cache`'s
  documented behaviour, not observed.
- I did not enumerate the suites that branch on `GITHUB_*` in their self-tests (F10). Candidates whose source
  mentions such variables: `batch-ci`, `check-merge-ready`, `check-review-recorded`, `ci-durations`,
  `gates-for-pr`.
- Whether suites write tracked files into the shared staged tree (spike caveat 8), and so change a later suite's
  reads.

VERDICT: NOT CONVERGED
