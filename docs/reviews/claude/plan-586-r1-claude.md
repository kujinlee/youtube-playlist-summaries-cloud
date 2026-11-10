Reviewed head: 20aa6e1b887dfe0b77d804fee7bd700b68851f02

# plan-586 (observed-reach selection): round 1, Claude half

Subject: `docs/superpowers/plans/2026-11-09-observed-reach-selection.md` against the approved spec
`docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md` (PR #552). Mandate: REFUTE. The spec is
not re-litigated; each finding is a place where the PLAN does not deliver it, cannot be built from its text, or
leaves a gate to memory.

## What I checked by running or reading the repo (not the plan's claims)

- **Task 1.0's numbers hold.** I ran the reduction's logic over the spike file in this session's scratchpad
  (`spike560/observed.json`, present, 90 targets): 47 untraced (`spawns` non-empty or rc ≠ 0); traced readers of
  PR #545's two paths are exactly `check-canonical-source`, `check-dashboard-entry`, `check-features`.
- **Every symbol the plan consumes from `check-plan-code.py` exists:** `stage_tree` (:917), `mutation_env` (:256),
  `control_is_green` (:1066), `summary_total` (:1053), `shard_slice` (:1582), `load_manifests` (:1425),
  `SUITE_TIMEOUT` (:110), `control_parts` (:438), `select_manifests` (:764), `_importers` (:751),
  `harness_files` (:592), `HARNESS_TREE` (:467, includes `docs`), `CHILD_HOME` (:176, inside the copy),
  `DEPENDENCY_MANIFESTS` (:580), `sweep_limit_pin` (:1338), `--only` and `--seeds` (:7053, :7057).
- **W4-W6 registries exist where the plan says:** the case `"the declared counts name every manifest that ships"`
  (:4587, `sorted(EXPECTED_MUTATIONS)`), `POPULATION` in `check-selftest-counts.py` (:122), `EXAMINED_KEYS` in
  `check-fixture-variation.py` (:316, keyed by basename). Top-level `import strace_reads` makes it a harness file
  through `harness_files`, as `coverage_verdict` is today (:104).
- **Ordering (mandate 2): no slice before 8 changes which targets a sweep runs.** Slices 2, 3, 5 add callers-less
  modules; slices 4 and 6 edit the harness (their own PRs run ALL, more, not fewer); slice 6's `sweep-select` is
  not in `mutation-sweep`'s `needs:` and Task 6.2 pins that with a case. The one way slice 8 lands early is F2.

## Findings

### F1 — HIGH — the cross-run check compares absolute paths with copy-relative ones, so it cannot fire on an in-tree flow

Task 3.2: `Record.wrote` is "absolute or copy-relative", and the whole-trace sets the cross-run check reads,
`all_named` and `all_listed`, are "(absolute)". Every target is traced in its OWN fresh copy (Task 4.1), so T's
absolute read `/tmp/copyT/docs/generated/flag` never equals U's write `/tmp/copyU/docs/generated/flag`, nor its
copy-relative form. The spec is explicit: "Paths under a run's copy are compared relative to that copy". As
written, the refusal for spec §2's laundered dependency (U writes under the tree, T reads it) never fires, and
T's trace reads `complete` with the dependency lost, which is §8.4's own FAILS IF. The Task 3.2 fixtures
("a listing of `docs/generated` when another wrote `docs/generated/flag`") are phrased in relative terms, so a
fixture written with both sides relative passes over the defect.

**Fix:** define ONE normal form in `Record` for every path set used by `cross_run`: copy-relative (prefixed, e.g.
`copy:docs/x`) for paths at or under the run's copy, `.home` included; absolute otherwise. Add a case whose two
records come from two DIFFERENT copy roots, built by `record_from_log` from two logs, not by hand.

### F2 — HIGH — the switch's preconditions (#590 closed, 20 clean shadow PRs) are prose; the house rule will merge slice 8 on READY

Slice 8's gate is "Do not start the build until ALL hold, each quoted with its evidence in the PR body". Nothing
mechanical holds it. Under the owner's merge-when-ready rule, `check-merge-ready.py` READY ⇒ squash; its loosening
detector is syntactic (its own comment at :654-:662: "A SEMANTIC loosening ... is outside what a diff rule can
see"), and slice 8 is exactly that: a shard honouring a shorter list lowers no pin, removes no failure-path line.
The spec's hardest precondition, "backlog #590 must close before any skip takes effect; shadow mode alone is not
enough", rests on whoever runs slice 8 remembering this paragraph.

**Fix:** make Task 8.1's `--targets` honour a list only when a self-test-pinned precondition holds: a case reads
`docs/backlog.md` and fails while row 590 lacks ✅, and the slice-8 PR body must carry a `LOOSENING-CHECK`-style
declaration so `check-merge-ready` HOLDs it (the owner's HOLD path), naming the ledger artifact id. At minimum,
state in the plan that slice 8 is a HOLD and why.

### F3 — HIGH — `q1_probe_delta` (the owner's Q1 fallback) cannot be computed from the Record the plan defines

Task 6.1 computes "picks with `probed` minus picks with `probed`'s stat/access entries removed" (spec §2, owner's
Q1 fallback). Task 3.2's `Record.probed` is a bare `frozenset[str]` of paths: it does not say which syscall
produced each probe, so the stat/access-only entries cannot be removed. Slice 8's gate ("the Q1 probe delta on PR
#543's diff is ≤ 5") is therefore unevaluable, and an implementer will guess (e.g. drop all failed opens too).

**Fix:** add `probed_stat: frozenset[str]` (paths probed ONLY by the `stat`/`statx`/`newfstatat`/`access`/
`faccessat*` family, never opened) to `Record` and `readsets.json` in Tasks 3.2/4.1, with a case, and define
`q1_probe_delta` over it.

### F4 — MEDIUM — the "allowlist ⊆ measured set" case is a tautology; #590's second FAILS IF is checked by a reviewer only

Task 3.1 defines `READ_ONLY/WRITES/PROCESS` as "restricted to `MEASURED_SYSCALLS - DENIED_SYSCALLS`", then asserts
`ALLOWED_SYSCALLS <= MEASURED_SYSCALLS`. That holds by construction against a constant typed into the same
module. Whether `MEASURED_SYSCALLS` IS slice 1's measurement ("verbatim") is left to "reviewer diffs them" (slice 3
merge gate). Backlog #590's FAILS IF ("the allowlist is longer than the measured set") is the clause this was
meant to make mechanical.

**Fix:** the case loads the committed `docs/reviews/measurements/2026-11-NN-strace-on-runner.json` (`docs` is a
staged root, so it is in the mutation tree) and asserts `MEASURED_SYSCALLS` and `MEASURED_IOCTLS` EQUAL its
unions, plus `STRACE_VERSION` equal to its version line.

### F5 — MEDIUM — the PROCESS class is still hand-authored for every measured name the spec does not list

Spec §2 completes the process class "from build step 1's measurement"; Task 3.1 gives no rule for which bucket a
measured name the spec does not name lands in. That is the hand classification backlog #590 says caused rounds
2-4's holes ("one component"). A name such as `memfd_create`, `pidfd_open`, `prctl`, `process_vm_writev` or
`copy_file_range`'s cousins placed in PROCESS loses its paths/descriptors from `wrote`.

**Fix:** state the rule: a measured name the spec's lists do not name goes to WRITES (fail closed: it can only
add cross-run refusals) or is left unallowed (refused), never PROCESS; PROCESS admits only names that take no fd
and no path argument, each with a case.

### F6 — MEDIUM — slice 1 does not keep the raw log lines slice 2 is told to copy

Task 2.1 Step 3: "Use real log lines from slice 1's artifacts as the source of every fixture line's exact shape".
Task 1.1's driver records only summaries (name multisets, ioctl tokens, an `AT_FDCWD<` flag, counts, and the
lines of refusal triggers). No `clone3` flag line, `<... resumed>` split, `-yy` labelled `openat`, `getdents64`,
`execve`, signal or exit line is kept. Spec §8.4 says the normalisation is "cased against recorded strace logs".

**Fix:** Task 1.1 uploads, per shard, a few full raw logs (one spawner that runs git, one threaded suite) and a
sampled line per (syscall name, return shape); Task 1.2 commits a trimmed set under `scripts/fixtures/` that slice
2's cases read.

### F7 — MEDIUM — the §8.2 EXACT-selection case depends on today's live sources, so its expected set drifts and the fixture cannot reproduce it

Task 1.0 keeps only `traced`, `reads`, `listed`. Task 5.2's case expects "EXACTLY today's spawner picks plus" the
three readers, but "today's spawner picks" is `select_manifests` over the 90 targets' SOURCES at `d206e066`, which
the fixture does not hold. Run against the live tree instead, the set moves with every script that starts or stops
naming `docs/backlog.md`, and targets absent from the fixture (no read set, so today's rule) join it: e.g.
`reach_select.py` itself, whose own cases will quote `docs/backlog.md`.

**Fix:** Task 1.0 also records, at `d206e066`, today's selection for PR #545's diff per target (computed by
`select_manifests` on that tree), and Task 5.2's case injects it (or the per-target "named" bits) as the rule-4
answer, restricted to the fixture's 90 targets.

### F8 — MEDIUM — rule 2 cannot be separated from rule 4 by calling `select_manifests`, as Task 5.2 says to

`select_manifests` returns `(frozenset | None, lines)`; inside, the own-source and own-manifest hits (rule 2) and
the namers (rule 4) are unioned into one `hit` (:788-:818). Task 5.2 says rules 1, 2 and 4 "come from calling
today's `select_manifests` per path ... never re-typed", and rule 3 "replaces rule 4 only for a target with a
usable set". From the return value there is no way to tell that T was picked because P is T's own source rather
than because T names P; the implementer must re-type rule 2 or parse log lines.

**Fix:** extract `mandatory(path, sources) -> set` from `select_manifests` (one function, both callers), or have
`select_manifests` return per-target reasons; Task 5.2 names which, with a case that a usable-set target whose
own source changed is picked although its read set does not hold the path.

### F9 — MEDIUM — the import direction between `reach_select` and `check-plan-code` is unspecified, and the obvious one is circular

`reach_select.py` loads `check-plan-code.py` through `importlib` (Task 5.2); Task 6.1 adds `--select-only` to
`check-plan-code.py`, which must call `reach_select`. A top-level `import reach_select` makes it a harness file
(changing every recording's validity hash, fine) AND re-executes `check-plan-code.py` inside it at import time;
a lazy import leaves `reach_select` outside `harness_files`. The plan picks neither.

**Fix:** state it: `--select-only` lives in `reach_select.py` (its `main`), which imports check-plan-code once; or
`check-plan-code.py` imports `reach_select` lazily inside the mode, and `reach_select` receives the needed
functions as arguments. Say which, and whether `reach_select.py` belongs in the harness hash.

### F10 — MEDIUM — four §8.3 refusal reasons have no case: strace missing, ptrace denied, strace's own exit, the traced timeout

Spec §8.3: "an incomplete trace for each reason (strace missing, ptrace denied, an unparseable log, an unresolved
relative path)", and §2 lists strace's nonzero exit and the timeout. Task 2.1 cases the unparseable log, 2.2 the
path refusals; Task 4.1's `record_target` names only `control red` and `case count differs`. Nothing cases a
missing `strace` binary, a ptrace `EPERM`, or a traced run killed at `SUITE_TIMEOUT * TRACE_FACTOR`. Note strace
exits with the tracee's status, so "strace's own exit" needs its stderr/log to be told apart from a red suite.

**Fix:** add the four to Task 4.1's cases through the injected `runner` (missing binary, `PTRACE` error text,
timeout), each with its adjacent green.

### F11 — MEDIUM — `record-reads`' `timeout-minutes` is derived from a 6-way sharded measurement; and the parse-time `realpath` test has no stated timing

(a) Task 4.2: "`timeout-minutes:` from slice 1's measured duration × 1.5". Slice 1 runs six shards (Task 1.1);
`record-reads` is one unsharded job. Taken per shard, the limit is ~6× too short and every recording times out,
so nothing is ever saved and shadow mode never starts. **Fix:** the SUM of the six shards' driver times × 1.5,
stated as such.

(b) Spec §2's pre-existing-link test is resolved "at parse time, before the copy is removed". Task 4.1 does not
say the traced log is parsed before the traced copy is deleted, nor before the plain run (which creates and
removes its own temp paths). **Fix:** `record_target` parses the log immediately after the traced run, with the
copy still present; a case asserts the order through the fake runner.

### F12 — MEDIUM — `sweep-select`'s job is underspecified: no `setup-node`, no `fetch-depth: 0`, and the cache choice lives in YAML

Spec §2 Resolve: `sweep-select` "runs the shards' `setup-node` step", since `node -v` is a key element. Task 6.2
lists no setup-node, Python pin or full fetch. Without `setup-node 22` the runner's default Node fails the key on
every PR: every target takes today's rule, there are no would-skip targets, and Q4's 20 never accrue. The
ancestor test and R..BASE diff need history. Choosing "the nearest ancestor" among listed caches is logic in a
`run:` block, the place `ci.yml`'s own comment (:1316-:1320) says logic must not live.

**Fix:** list the setup steps; move "list, filter by ancestry, pick nearest" into a pure `reach_select` function
with cases (`gh` output and `is_ancestor` injected).

### F13 — MEDIUM — the post-switch detector needs write access the plan forbids, and has no job

Task 8.2: "A non-empty result comments on the open `sweep-red` issue". Global Constraints: read-only tokens
(`contents: read`, `actions: read`). Neither Task 8.2 nor 7.2 names the job that runs `--post-switch`, its trigger
(after a red master sweep), or `issues: write`.

**Fix:** name the job (e.g. a step in the existing `sweep-red-alert` path, which already writes that issue) and its
permission, as an explicit exception to the read-only constraint.

### F14 — LOW — tasks that MODIFY an existing self-tested script carry no W-pins

Tasks 6.1, 6.2, 7.1 and 8.1 add cases to `check-plan-code.py` but list no declared-count (W1), manifest/
`EXPECTED_MUTATIONS` (W2/W3) or `EXAMINED_KEYS` (W6) update; only 4.1 and 8.2 do. That is the PR #551 failure the
W-list exists for. **Fix:** a one-line "W1/W2/W3/W6 for `check-plan-code.py`" in each.

### F15 — LOW — W7's stated reason is vacuous for these names

`check-ratchet-contract.py`'s population is `GUARD_PATH_RE = scripts/check-[\w.-]+\.py` (:116); `strace_reads.py`,
`reach_select.py` and `shadow-compare.py` are outside it, so it neither passes nor fails on them (the `ci.yml`
comments at :813 and :822 say this of `page_markup`/`page_chrome`). The real caller evidence is the `ci.yml` step
and `POPULATION`. **Fix:** reword W7; keep the step.

### F16 — LOW — image-drift counting is not planned

Spec §2/§4.4: each shard logs its `ImageVersion` beside `sweep-select`'s, "and shadow mode counts a mismatch as a
drift event". Task 6.2 logs it; Task 7.2's comparator does not read or count it. **Fix:** put `ImageVersion` in each
`verdicts-*` header and the `selection-*` artifact; `compare_push` reports drift events in the ledger.

### F17 — LOW — slice 4's map lists post-merge observations as its merge gate

Slice map row 4: "first master `record-reads` run saved; backlog #590 ticked" as "Merge gate beyond READY". Both
are observable only after the merge (Task 4.3 says so). **Fix:** move them to a post-merge step; keep slice 6
blocked on them.

### F18 — LOW — #590's "rename or replace" is only half-cased

Backlog #590: "any unlink, rename or replace of a path component OUTSIDE the staged copy". Task 2.2's rule names
`unlink*/rename*/rmdir` without saying a `rename` whose DESTINATION is a pre-existing external path (a replace)
counts; its only case is `unlink("L")`. **Fix:** both sides of `rename*`, with a `rename(tmp, L)` case.

### F19 — LOW — the cache key's `<python>` and `<harness hash>` have no producer step

Task 4.2's `actions/cache/save` key embeds both, but no step writes them to `$GITHUB_OUTPUT`. A schedule run at
the same sha as a master push also collides with the push's key (save is refused; harmless, but say so).
**Fix:** `--record-reads` prints `key=` to `$GITHUB_OUTPUT`.

### F20 — LOW — slices 2 and 5 "in parallel" edit the same registries

Both edit `expected_mutations.py`, the `check-plan-code.py` list, `POPULATION`, `EXAMINED_KEYS` and `ci.yml`. The
second to merge conflicts; say "merge 2 before rebasing 5" or serialise.

### F21 — LOW — `shadow-compare`'s replay needs the sweep's setup

Task 7.2's job lists triggers and permissions only; replaying a mutant on a staged tree needs `setup-node 22`,
`npm ci` (`node_modules/typescript` is staged) and the Python pin. **Fix:** list them.

## Could NOT check

- Anything on a GitHub runner: whether ptrace is allowed, `-yy` decorates `AT_FDCWD`, or the job durations.
- Whether `actions/cache/save` with a duplicate key fails the step or warns on the current action version.
- `check-merge-ready`'s verdict on a slice-8-shaped diff (F2 is from its own stated scope, not a run).
- I did not execute the plan's code blocks other than Task 1.0's reduction logic.

VERDICT: NOT CONVERGED
