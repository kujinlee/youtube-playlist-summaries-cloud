# Observed-reach selection — implementation plan (backlog #586, prerequisite backlog #590)

> **Anchor:** `dev-speed-first` — **ADR:** none
> **Goal:** A change gets its verdict as fast as the evidence allows, with mutation coverage identical.

**Status:** 📝 DRAFT, written 2026-11-09 from the approved spec at `1a6004c1`. Phase 2: dual adversarial review
to convergence or the round cap (`docs/review-method.md` §0 Q4c) before any task is dispatched. Nothing is built.
Round 1 (both halves, 30 findings incl. 1 BLOCKER) is folded: `docs/reviews/coordinator/plan-586-r1-coordinator.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a pull request's mutation sweep runs a guard's mutants only when that guard's suite was SEEN (under
`strace -f`) to read, probe or list a path the comparison set changed; every doubt gives today's selection or more.

**Architecture:** a pure strace-log parser and default-deny classifier (`scripts/strace_reads.py`) turns one traced
`--self-test` run into a read set or a named refusal. A dedicated `record-reads` job on each master push and the
schedule records every manifest target under two fixed seeds and saves `readsets.json` to `actions/cache`. A pure
selector (`scripts/reach_select.py`) applies spec §2 rule 3 over `Δ = (R..BASE) ∪ (BASE..HEAD)`. A `sweep-select` job
computes the selection once; in SHADOW it only reports `WOULD-SKIP`, and a comparator (`scripts/shadow-compare.py`)
checks every would-skip against the base's full sweep. Only the last slice lets a shard skip a target.

**Tech Stack:** Python 3.12 (stdlib only), `strace` on GitHub-hosted `ubuntu-latest`, GitHub Actions
(`actions/cache/save` + `restore`, `actions/upload-artifact`), read-only `gh api`.

**Spec:** `docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md` (approved 2026-11-09). Executors
read the spec section each task cites; this plan does not restate its rules.

## Global Constraints

- **Fail closed, everywhere.** Any doubt (a refusal, a parse failure, a cache miss, an API failure, a key mismatch)
  gives that target today's rule (`select_manifests`), or FULL. Never fewer picks than today for a doubted target
  (coordinator rounds 1-3: "any doubt gives today's selection or more").
- **Prefer a refusal to a model** (coordinator rounds 2-4). Where an implementer is tempted to resolve, map or
  reconstruct something the spec does not explicitly model, emit an INCOMPLETE reason instead and add it to
  `REASONS`.
- **Default-deny (backlog #590).** A syscall name, an `ioctl` request token, or an unlink/rename/replace of a
  PRE-EXISTING path outside the staged copy that the measured allowlist does not hold makes the trace INCOMPLETE.
  The allowlist is a SUBSET of what slice 1 measured, never authored beyond it.
- **No skip takes effect before slice 8, and none after it unless a MACHINE says so (r1 Claude F2).** Under the
  owner's merge-when-READY rule a prose precondition is worthless: `check-merge-ready.py` holds only on its
  syntactic proxies (`hold_reasons`: pinned baselines, falling pins or case counts, failure-path lines, dropped gate
  invocations, scope exits, migrations, `NO-REVIEW:`, app code), and no PR-body marker forces a HOLD. So slice 8's
  preconditions are a pure `reach_select.switch_gate` that `sweep-select` runs on EVERY pull request (Task 8.1):
  while backlog #590's row at BASE lacks ✅, or the newest TRUSTED `shadow-ledger` holds fewer than 20 consecutive
  COMPLETE clean PRs (spec §7 Q4), or any latched miss, or Q1 (read at BASE) is undecided, it emits TODAY's
  selection and logs `SWITCH GATE: <why>`. Slice 8 merged early is therefore inert, not unsafe.
- **Trust and provenance (r2 Codex F1-F6).** Nothing a pull request produces or edits may open the switch for that
  PR or any other. Three refusals carry it, each falling back to today's rule: (a) the shard, which runs the
  HARNESS (`check-plan-code.py`, whose own change already forces FULL), re-derives rules 1 and 2 itself and
  refuses a list that omits a mandatory pick, names an unknown target, or arrives on a PR that changes a selector
  file (Task 8.1 `shard_targets`); (b) every decision input is read at BASE (`docs/backlog.md`, `Q1_DECISION`);
  (c) a ledger counts only if its producing run was the `ci.yml` `schedule`/`workflow_dispatch` run on the
  default branch of this repository, checked through the run's API metadata, never the artifact's name (Task 7.2
  `trusted_ledger`). Ledger writers are serialized (one concurrency group, no cancel-in-progress), and a ledger
  belongs to one EPOCH (`shadow_start`). **Bound, stated:** `ci.yml` is a harness file, so a PR that edits
  it gets FULL from `shard_targets`, but the edit could stop calling `shard_targets` at all, exactly as it can
  delete the sweep today; that is review's to catch, not this plan's.
- **The sweep never stops running because selection did (r1 Codex F1).** `mutation-sweep` runs on every event
  whatever `sweep-select`'s result (skipped on master and the schedule, failed, cancelled), and a shard with no
  usable list runs today's rule (FULL on master and the schedule). Task 8.1 cases it at workflow level.
- **Coverage is identical:** no mutant, case or pin is removed by any slice. Master pushes and the schedule keep
  running the WHOLE manifest.
- Python pinned `3.12` in every new CI job, with the `scripts/check-python-pin.py` step (it fails any job that does
  not pin). Node `'22'` where a job stages `node_modules/typescript`.
- `record-reads`, `sweep-select` and `shadow-compare` are NOT required checks; `mutation-sweep-complete` ignores them.
- Read-only tokens: `contents: read`, plus `actions: read` where a job lists caches or downloads artifacts. **ONE
  exception, already in `ci.yml` (r1 Codex F6, Claude F13):** `mutation-sweep-complete` holds `issues: write` for
  `scripts/sweep-red-alert.py` (backlog #330). Slice 8's post-switch detector runs as a step of THAT job and hands
  its report to `sweep-red-alert.py`, the one writer of the `sweep-red` issue; the job gains `actions: read` only.
  No new job gets a write permission.
- No tool call over 270 s while executing this plan: long CI waits are backgrounded and polled.
- Every number written into code comments, docs or the dashboard is marked MEASURED (with what was run) or INFERRED.

## Review Focus

1. **A trace that reads `complete` while a read was lost** — the parser meets a line shape the fixtures never had
   (a signal line `--- SIGCHLD`, `+++ exited`, a `<... resumed>` split across pids, a path with `\x` escapes). Expected:
   any line the tokenizer cannot place is `log did not parse`, never skipped. Test owner: Task 2.1.
2. **The cache restored from a different world** — a payload whose sha is not an ancestor of BASE, or whose key
   differs in one element. Expected: today's rule for every target, one log line naming the element. Owner: Task 5.3.
3. **A shard that runs a list other than `sweep-select`'s, or does not run at all,** after the switch (the job
   output truncated, empty, or absent because `sweep-select` was skipped or failed; `mutation-sweep` skipped by a
   `needs:` on a skipped job). Expected: the shards always run; empty or absent output is today's rule, never
   "nothing selected". Owner: Task 8.1.
4. **A shadow comparison counted clean on missing evidence** — an expired artifact, a `complete: false` verdict file,
   a base whose shard was budget-stopped. Expected: INCONCLUSIVE, never clean. Owner: Task 7.2.
5. **A recording job killed mid-way that still saves** (the `timeout-minutes` kill, a cancelled run, a target listed
   twice). Expected: no save. Owner: Task 4.3.

---

## Slice map

Each slice is ONE pull request off fresh `origin/master`, independently mergeable, with its own dual review.

| # | Slug / branch | What merges | Skips a target? | Merge gate beyond READY |
|---|---|---|---|---|
| 1 | `measure-strace-runner` / `build-586-s1-measure` | measurement workflow + driver + measured data + raw-log fixtures + doc | no | the measurement ran on GitHub-hosted ubuntu |
| 2 | `strace-parse` / `build-586-s2-parse` | `scripts/strace_reads.py`: tokenizer, process tree, cwd model, path refusals | no (no caller) | — |
| 3 | `strace-classify` / `build-586-s3-classify` | default-deny classifier, record assembly, seed + cross-run checks | no (no caller) | the measured-set EQUALITY case is green (Task 3.1) |
| 4 | `record-reads-job` / `build-586-s4-record` | `--record-reads` mode, `record-reads` job, cache save, live cases | no | — (post-merge, before slice 6 starts: Task 4.3) |
| 5 | `reach-select` / `build-586-s5-select` | `scripts/reach_select.py`: `Δ`, rule 3, validity; `select_reasons` split out of `select_manifests` | no | — |
| 6 | `shadow-select` / `build-586-s6-shadow` | `sweep-select` job (report-only), `verdicts.jsonl`, artifacts | **no** — shards still self-select | the first PR run uploads `selection-*` |
| 7 | `shadow-compare` / `build-586-s7-compare` | comparator, `--mutant` replay, scheduled job, ledger | no | — |
| 8 | `observed-reach-switch` / `build-586-s8-switch` | shards take `sweep-select`'s list behind `switch_gate`; post-switch detector | **YES, once `switch_gate` passes** | none: the preconditions are `switch_gate`'s, checked on every run (Global Constraints) |

"Skips a target?" is the question that matters. Slices that edit `check-plan-code.py` (4, 5, 6, 7, 8) make their
OWN PR's sweep run ALL, which is MORE, not fewer (r1 Codex's closing note: the old column, "Changes selection?",
was literally inaccurate for them).

Slices 2 and 5 can be built in parallel after slice 1, but they edit the same registries (`expected_mutations.py`,
the declared-counts case, `POPULATION`, `EXAMINED_KEYS`, `ci.yml`; r1 Claude F20): **merge slice 2 first**; slice 5
then merges `origin/master` in (never a rebase, which orphans its review verdicts) and re-derives its W3-W6 pins
before its push. Slice 3 needs slice 1's data; slice 4 needs 3; slice 6 needs 4 (and Task 4.3's post-merge
observations) and 5; slice 7 needs 6; slice 8 needs 7. Slice 8 does NOT wait for the shadow period: `switch_gate`
does.

## Wiring a new self-tested script (W1-W8) — the PR #551 lesson, named per task

Every task that creates a script with `--self-test` does ALL of these in the same commit as the script, and names
them in its file list. CI went red on PR #551 for missing the declared-count and examined-keys pair.

- **W1** the script's docstring declares `python3 scripts/<name>.py --self-test  # N cases`, N copied from the
  suite's own `N/N self-test cases passed` line (never typed from memory).
- **W2** `scripts/mutations/<stem>.json`: one entry per guard clause the task adds (`name`, `file`, `edits`,
  `expect`), each run red with `python3 scripts/check-plan-code.py --mutate . --only scripts/<name>.py`.
- **W3** `scripts/mutations/expected_mutations.py`: `"scripts/<name>.py": <entry count>`, with a dated comment
  naming the per-file move. There is NO typed total (the file's own "⛔ backlog #359: THERE IS NO TYPED TOTAL";
  `declared_total()` derives it), so never write a sum (r1 Codex F7).
- **W4** `scripts/check-plan-code.py`: the path in the sorted list of the case
  `"the declared counts name every manifest that ships"` (in `_self_test_body`). This edits the harness, so the
  PR's own sweep runs ALL; expected.
- **W5** `scripts/check-selftest-counts.py`: the file name in `POPULATION`, with a dated comment.
- **W6** `scripts/check-fixture-variation.py`: `EXAMINED_KEYS["<name>.py"]` set to the keys `analyse()` returns on
  the delivered source (its `main` prints only a summary, never the key set; r1 Codex F7), derived by running:
  ```bash
  python3 -c 'import importlib.util as u,sys; s=u.spec_from_file_location("fv","scripts/check-fixture-variation.py"); m=u.module_from_spec(s); s.loader.exec_module(m); p=sys.argv[1]; print("\n".join(sorted(m.analyse(open(p).read(), p)[1])))' scripts/<name>.py
  ```
  plus one written exemption per key a helper drives through a single call site. Every new pure function's
  parameters are varied in ≥ 2 cases.
- **W7** a caller: a `ci.yml` `verify` step `python3 scripts/<name>.py --self-test` (or, for a library imported by
  `check-plan-code.py`, `check-selftest-counts`' run, as `coverage_verdict.py` has). That step IS the caller
  evidence. `scripts/check-ratchet-contract.py` neither passes nor fails these three names: its population is
  `GUARD_PATH_RE = scripts/check-[\w.-]+\.py`, which `strace_reads.py`, `reach_select.py` and `shadow-compare.py`
  do not match (r1 Claude F15; `ci.yml` says the same of `page_markup`/`page_chrome`). Run it anyway; do not cite it.
- **W8** if the script uses `fixture_git`, it enters `fixture_git.isolated()` in the exact shape
  `scripts/check-fixture-git-isolation.py` reads (PR #546 tripped it).

**WM — a task that MODIFIES an existing self-tested script (r1 Codex F8, Claude F14).** W1-W8 above are for a
script a task CREATES. A task that adds functions or cases to an existing one (`check-plan-code.py` in Tasks 4.1,
4.2, 5.2, 6.1, 6.2, 7.1, 8.1; `strace_reads.py` in 2.2-3.2 and 4.2; `reach_select.py` in 5.2-5.3 and 8.1;
`shadow-compare.py` in 8.2; `sweep-red-alert.py` in 8.2) does, in the same commit: **W1** the declared count
re-copied from the suite's own pass line; **W2/W3** one manifest entry per new guard clause and the
`EXPECTED_MUTATIONS` pin moved by that number; **W6** `EXAMINED_KEYS` re-derived with the `analyse()` command
above. Each such task's file list names them as "WM pins". For `check-plan-code.py` the PR's own sweep runs ALL.

## Before every push (all slices)

Run in the slice's worktree; read each `rc` on its own line (`cmd; rc=$?; echo "rc=$rc"`), never after a pipe.

```bash
python3 scripts/check-docs.py
python3 scripts/check-reference-namespace.py --base origin/master
python3 scripts/check-doc-citations.py --base origin/master
python3 scripts/check-fixture-variation.py
python3 scripts/check-selftest-counts.py --changed
python3 scripts/check-ratchet-contract.py
python3 scripts/check-review-recorded.py --base origin/master --pr-body-file "$BODY"
python3 scripts/check-dashboard-entry.py --base origin/master --pr-body-file "$BODY"
python3 scripts/check-plan-leak.py --base origin/master --head HEAD
python3 scripts/check-python-pin.py            # any slice that adds a CI job
python3 scripts/gen-backlog-page.py --self-test # any slice that edits docs/backlog.md
```

Per-slice additions are listed in each slice's **Pre-push** line. `$BODY` is the PR body file the slice will open
the PR with (`--body-file`), written before the push.

---

## Slice 1 — measure strace on the runner (spec §2 "build plan's FIRST step"; backlog #590's measured set)

**Decides:** whether v1 records with strace or falls back to the audit hook, and supplies every MEASURED constant
the later slices pin: `STRACE_VERSION`, `MEASURED_SYSCALLS`, `MEASURED_IOCTLS`, `TRACE_FACTOR`, whether `-yy`
decorates `AT_FDCWD`, and which suites trip `io_uring_setup`, `unshare`, `setns`, the mount family, a ` (deleted)`
label, or an unlink/rename of a pre-existing external path.

### Task 1.0: preserve the spike's read sets as a committed fixture

The spike's data lives only in session `f7c144b8`'s scratchpad
(`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/f7c144b8-1b6c-4db3-8ef1-932d4e701b12/scratchpad/spike560/observed.json`,
90 targets, 620 KB) and is the input spec §8.2 names. Save a REDUCED copy (8.9 KB, MEASURED) before it is lost; if
the file is gone, §8.2's fixture is rebuilt from slice 4's first recording instead, and the expected set re-derived.

**Files:**
- Create: `scripts/fixtures/observed-reach-spike-pr545.json`

- [ ] **Step 1: write the reduction.** For each target keep `traced` (= no spawn and rc 0), and only the `reads`
  and `listed` entries at or above PR #545's two paths (`docs/backlog.md`, `docs/dashboard-entries.md`). Rule 3 reads
  nothing else for that diff, so the reduction is lossless for §8.2. Record the source commit `d206e066`.

```python
import json, sys
d = json.load(open(sys.argv[1]))
P = ["docs/backlog.md", "docs/dashboard-entries.md"]
above = set(P) | {"/".join(p.split("/")[:i]) for p in P for i in range(1, p.count("/") + 1)}
out = {"source": "observed-reads spike, audit hook, d206e066", "diff": [["M", p] for p in P],
       "targets": {t: {"traced": (not v["spawns"]) and v["rc"] == 0,
                       "reads": sorted(set(v["reads"]) & above),
                       "listed": sorted(set(v["listed"]) & above)} for t, v in sorted(d.items())}}
json.dump(out, open(sys.argv[2], "w"), indent=1, sort_keys=True)
```

- [ ] **Step 1b: record today's rule at the same commit (r1 Claude F7).** §8.2's expected set is "the 33 spawners
  named by today's rule plus" three readers, and today's rule is `select_manifests` over the targets' SOURCES at
  `d206e066`, which the reduced fixture does not hold. Run against the live tree instead, it drifts with every
  script that starts or stops naming `docs/backlog.md`. So, in a throwaway `git worktree add <tmp> d206e066`, load
  THAT tree's `check-plan-code.py` (`importlib`), build its `sources`/`harness`/`modules` exactly as its own
  `--mutate` path does, and call that tree's `select_manifests("pull_request", [path], …)` once per path of the
  diff (a one-path list, so each pick is attributable to its path). Store per target `"today": [<path>, ...]` (the paths that picked it, empty if none) and a top-level
  `"today_full": null | "<why>"`. Neither changed path is a script or a manifest, so every such pick is rule 4
  (naming), never rule 2. Task 5.2's case injects these as the rule-4 answer for the fixture's 90 targets, never
  recomputed from the live tree.
- [ ] **Step 2: verify.** Expected (MEASURED 2026-11-09 by this plan's author on the same file): 47 untraced
  targets; traced readers of a changed path exactly `check-canonical-source`, `check-dashboard-entry`,
  `check-features`. Expected from spec §8.2 (NOT yet measured by this plan): `today_full` is null and exactly 33
  untraced targets have a non-empty `today`. A different count STOPS the task: report it, do not adjust §8.2.
- [ ] **Step 3: commit** `git add scripts/fixtures/observed-reach-spike-pr545.json`.

### Task 1.1: the measurement driver and its workflow

**Files:**
- Create: `scripts/strace-measure.py` (a measurement instrument: no `--self-test`, not a guard; its output is
  reviewed by hand and pinned by slice 3's subset case)
- Create: `.github/workflows/strace-measure.yml`

**Interfaces:**
- Produces: `python3 scripts/strace-measure.py --shard I/N --seeds A,B --out DIR` writes `DIR/shard-I.json`;
  `python3 scripts/strace-measure.py --merge DIR... --out FILE` writes the merged summary.
- Consumes: `check-plan-code.py`'s `stage_tree`, `mutation_env`, `control_is_green`, `summary_total`,
  `shard_slice`, `load_manifests`, `SUITE_TIMEOUT`, loaded with `importlib` (the spike's method).

- [ ] **Step 1: write the driver.** Per target in its shard, per seed: a PLAIN run then a TRACED run
  (`strace -f -yy -o <log> python3 <target> --self-test`), each in a fresh `stage_tree` copy with fresh `CHILD_HOME`,
  `env=mutation_env(copy, seed)`, timeout `SUITE_TIMEOUT * 10`. Record per target and seed: `rc`, case count, wall
  seconds of each run; from the log: the multiset of syscall NAMES (the token before `(` on each line, `resumed`
  lines included), every `ioctl` request token (the second argument, verbatim), whether any line holds
  `AT_FDCWD<`, the count of ` (deleted)>` labels, every `unshare|setns|chroot|pivot_root|mount|umount2|open_tree|
  move_mount|fsopen|fsmount|fspick|mount_setattr|io_uring_setup` line, and every `unlink*`/`rename*`/`rmdir` whose
  path is outside the copy and was not created earlier in the same log by a creating call. Header: `strace -V`
  first line, `uname -r`, `ImageOS`, `ImageVersion`, `node -v`, `python3 -V`. Also per target and seed: whether
  the traced run hit its timeout, and strace's own stderr (to tell strace's failure from a red suite, since strace
  exits with the tracee's status; r1 Claude F10).
  **Raw lines (r1 Claude F6):** slice 2's fixtures must be copied from real logs (spec §8.4: "cased against
  recorded strace logs"), so the driver also keeps, per shard, (a) the WHOLE raw log of one spawner that runs `git`
  and one threaded suite, and (b) one sampled raw line per (syscall name, return shape: `= N`, `= -1 E…`,
  `<unfinished ...>`, `<... resumed>`, a `-yy` label, `AT_FDCWD<`), plus every `--- SIG`, `+++ exited`/`+++ killed`
  and `clone`/`clone3`/`vfork` line shape seen.
- [ ] **Step 2: write the workflow.** Triggers: `workflow_dispatch`, and `pull_request` with `paths:` limited to
  the workflow and the driver. One job, matrix `shard: [1..6]`, `runs-on: ubuntu-latest`, `timeout-minutes: 60`,
  checkout `fetch-depth: 0`, `setup-node 22`, `setup-python 3.12`, the Python-pin step, `npm ci`,
  `command -v strace || sudo apt-get install -y strace`, a ptrace probe
  (`strace -f -o /tmp/p.log git --version && grep -q execve /tmp/p.log`), then the driver with
  `--seeds <RECORD_SEEDS>` (two fixed distinct values chosen here and reused verbatim in slice 4; record them in
  the measurement doc). Upload `strace-measure-<run_id>-<shard>` (`retention-days: 90`, `if: always()`).
- [ ] **Step 3: commit.**

### Task 1.2: run it, merge the data, write the measurement doc

**Files:**
- Create: `docs/reviews/measurements/2026-11-NN-strace-on-runner.md` (NN = the run date)
- Create: `docs/reviews/measurements/2026-11-NN-strace-on-runner.json` (the merged summary)
- Create: `scripts/fixtures/strace-lines/` — the sampled raw lines and the two whole logs, trimmed (paths
  shortened to `/t/…`, consistently), each file headed with its run id; slice 2's cases read these
- Modify: `docs/backlog.md` (rows #586 and #590: the measured facts, one line each)
- Modify: `docs/dashboard-entries.md`

- [ ] **Step 1:** push the branch, open a DRAFT PR, wait for the run (background + poll in < 270 s chunks).
- [ ] **Step 2:** `gh run download <id> -D <tmp>`; `python3 scripts/strace-measure.py --merge <tmp>/* --out <json>`.
- [ ] **Step 3: the decision gate.** If the ptrace probe failed or strace is unavailable: write that in the doc,
  and slices 2-3 are REPLACED by slice 2F below; the rest of the plan is unchanged. Otherwise record, all MEASURED:
  the strace version line; the syscall-name union and per-name target counts; the ioctl tokens; AT_FDCWD decoration
  yes/no; each refusal-trigger hit by target; `TRACE_FACTOR` = the largest traced/plain wall-clock ratio over
  spawner targets, rounded UP to an integer; the targets whose traced and plain case counts differ; job durations,
  per shard AND their SUM (Task 4.2's unsharded `record-reads` budget comes from the sum; r1 Claude F11a).
- [ ] **Step 4:** commit, mark the PR ready.

**Pre-push:** `python3 scripts/check-python-pin.py`; `actionlint` if installed, else say NOT RUN.

**FAILS IF:** the doc states a constant the JSON does not hold; a figure appears without its run id.

### Slice 2F (only if slice 1 says strace is unavailable): the audit-hook recorder

Same interfaces as slices 2-3 (`Record`, `REASONS`), recorder `audit-hook`: `sys.addaudithook` on `open`,
`os.listdir`, `os.scandir`, `glob.glob`, `os.walk` and the process-creation events, with failed opens and wrapped
`os.stat`/`os.lstat`/`os.access` as `probed`. Any process-creation event is INCOMPLETE (`spawned a child`). Cross-run
flows stay bounded (spec §4.3). The spec's §8.3 audit-hook cases (`Popen`, `os.fork`, `os.system`) are its tests.
If this branch is taken, re-plan slices 2-3 as one slice before building; do not improvise.

---

## Slice 2 — parse a strace log (spec §2 "Normalising strace's paths"; §8.4 normalisation cases)

### Task 2.1: tokenizer and process tree

**Files:**
- Create: `scripts/strace_reads.py`
- Create: `scripts/mutations/strace_reads.json`
- Modify: W3-W7 files (`expected_mutations.py`, `check-plan-code.py` list, `check-selftest-counts.py`,
  `check-fixture-variation.py`, `ci.yml` `verify` step)

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Call: pid: int; name: str; args: str; ret: str; label: str | None; seq: int`
    (`label` = the `-yy` decoration of the return value, e.g. `/t/scripts/a.py`; `seq` = log line order)
  - `parse_log(text: str) -> tuple[list[Call], str | None]` — the second element is a `REASONS` member or None.
    `unfinished`/`resumed` pairs are joined per pid; `+++ exited`/`+++ killed` and `--- SIG… ---` lines are
    recognised and dropped; any other unplaceable line is `log did not parse`.
  - `decode_path(s: str) -> str | None` — strace's C escapes (`\"`, `\\`, `\n`, `\ooo`, `\xHH`); None = undecodable.
  - `process_tree(calls: list[Call], root: int) -> tuple[dict[int, tuple[int, int, bool]], str | None]` — child pid
    → (parent pid, the clone's ENTRY `seq`, shares-fs flag from `CLONE_FS`); pass one over all lines.
  - `REASONS: tuple[str, ...]` — every refusal string, spelled as spec §2's `trace` list.

- [ ] **Step 1: write failing cases** (`--self-test`, `case(name, got, want)` as the repo's suites do):
  - `"a resumed line joins its unfinished half"`: `"12 openat(AT_FDCWD</t>, \"a\", O_RDONLY <unfinished ...>"` +
    `"12 <... openat resumed>) = 3</t/a>"` → one `Call(name="openat", label="/t/a")`.
  - ADJACENT negative `"an unfinished half with no resume is refused"` → reason `"unmatched unfinished/resumed"`.
  - `"a child's lines before its parent's clone return are placed"` (child pid 13 lines first, then
    `"12 clone3({flags=CLONE_VM|CLONE_FS|…}, 88) = 13"`) → tree `{13: (12, seq, True)}`.
  - `"a pid no clone created is refused"` → `"unknown pid"`; negative: the root pid is not refused.
  - `"a clone whose flags do not parse is refused"` → `"unmodelled clone"`.
  - `"an octal-escaped path decodes"` `"\\303\\251.py"` → `"é.py"`; negative `"\\q"` → None → `"undecodable path"`.
  - `"an unknown line shape is refused, never skipped"` → `"log did not parse"`; negative: `"--- SIGCHLD {…} ---"`
    and `"+++ exited with 0 +++"` parse to no Call and no reason.
- [ ] **Step 2: run** `python3 scripts/strace_reads.py --self-test` → FAIL (module absent).
- [ ] **Step 3: implement** the four functions above. Every fixture line is COPIED from
  `scripts/fixtures/strace-lines/` (slice 1, Task 1.2), never typed from memory; a case may shorten a path, and
  one case parses each committed whole log end to end with no reason (r1 Claude F6).
- [ ] **Step 4: run** → `N/N self-test cases passed`.
- [ ] **Step 5: W1-W7**, then `python3 scripts/check-plan-code.py --mutate . --only scripts/strace_reads.py`
  (every entry killed). Commit.

### Task 2.2: cwd model and path resolution, with every refusal from §2

**Files:** Modify `scripts/strace_reads.py`, `scripts/mutations/strace_reads.json`, the W1/W3/W6 pins.

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Ctx: copy: str; workspace: str; staged_roots: tuple[str, ...];
     repo_links: frozenset[str]; cwd0: str`
  - `resolve_calls(calls: list[Call], tree: dict, ctx: Ctx) -> tuple[list[tuple[Call, list[str]]], str | None]` —
    each call with the absolute paths it names (kernel label for a successful open; cwd/dirfd join otherwise).
  - `rel_to_copy(path: str, ctx: Ctx) -> str | None` — the staged-tree relative path, or None if outside.
- Rules (spec §2, each a refusal, none modelled): `..` in a joined failed/path-only path → `unresolved ..`; a path
  through a link created during the trace → `through a runtime link`; a lexically-outside path whose
  longest-existing-prefix `realpath` lands in the copy → `through a pre-existing link`; at or under a
  `repo_links` prefix → `through a repo link`; at or under `ctx.workspace` → `real checkout`; a `/proc/*/fd/N`,
  `/proc/*/cwd`, `/proc/*/root` path without a same-line label → `unresolved /proc path`; ` (deleted)` label in the
  copy → `deleted label` (stripped outside); `rename*` with a side in the copy → `rename in the copy`; a `chdir` in a
  shared context between a clone's entry and return → `cwd race`; `AT_FDCWD<…>` disagreeing with the model →
  `cwd model disagrees` (only if slice 1 measured decoration); **backlog #590 R4-F1:** an `unlink*`/`rmdir` of a
  path outside the copy that no earlier call in the log created, or a `rename*` EITHER of whose sides is such a
  path (the source is removed; a destination that pre-exists is REPLACED, backlog #590's "unlink, rename or
  replace"; r1 Claude F18) → `external path removed`.
- `.git` (spec §2): a path with a `.git` component outside `ctx.workspace` is dropped; `.github/…`, `.githooks/…`
  are ordinary.

- [ ] **Step 1: failing cases**, one per §8.4 normalisation bullet, each with its adjacent negative:
  relative open after `chdir`; relative open in a `fork` child that copied the cwd (negative: the parent's later
  `chdir` does not move the child); a `CLONE_FS` thread's `chdir` moving ANOTHER thread's relative open and probe;
  `openat` through a directory descriptor label; a successful `..` open resolved by its label; failed
  `outside/link/../flag` → INCOMPLETE; a successful open via a since-deleted temp link → its staged name; a failed
  probe through a runtime link → INCOMPLETE; failed `L/<copy>/docs/x` with `L -> /tmp` → INCOMPLETE vs failed
  `/tmp/other/x` → not refused; a read under `docs/alias` (repo link) → INCOMPLETE; `.git` in a temp repo dropped
  vs the same process's working-tree read counted; `.github/workflows/ci.yml` and `.githooks/pre-push` counted; a
  path under the workspace → `real checkout`; **R4-F1:** a probe of `L/<copy>/docs/value` then `unlink("L")`, `L`
  pre-existing → `external path removed`, negative: `unlink` of a file the trace itself created under `/tmp` is not
  refused; `rename("/tmp/new", "L")` with `L` pre-existing (a replace) → `external path removed`, and
  `rename("L", "/tmp/x")` → the same, negative: `rename` between two paths the trace created is not refused. The `realpath` cases build real links in a temp dir (`tempfile`), so they run on macOS and Linux.
- [ ] **Steps 2-5:** run red, implement, run green, W1/W2/W3/W6 updated, mutate `--only`, commit.

**Pre-push (slice 2):** `python3 scripts/strace_reads.py --self-test`;
`python3 scripts/check-plan-code.py --mutate . --only scripts/strace_reads.py`.

---

## Slice 3 — classify by default-deny and assemble the record (spec §2 classes; backlog #590)

### Task 3.1: the measured allowlist and the classifier

**Files:** Modify `scripts/strace_reads.py`, its manifest, W1/W3/W6 pins.

**Interfaces:**
- Produces:
  - `STRACE_VERSION: str` — slice 1's `strace -V` line, verbatim.
  - `MEASURED_SYSCALLS: frozenset[str]`, `MEASURED_IOCTLS: frozenset[str]` — slice 1's unions, verbatim, with the
    run id in a comment.
  - `DENIED_SYSCALLS: frozenset[str]` — `unshare`, `setns`, `chroot`, `pivot_root`, `mount`, `umount2`,
    `open_tree`, `move_mount`, `fsopen`, `fsmount`, `fspick`, `mount_setattr`, `io_uring_setup`,
    `io_uring_enter`, `io_uring_register`.
  - `DENIED_IOCTLS: frozenset[str]` — `FS_IOC_SETFLAGS`, `FS_IOC_FSSETXATTR`, `FS_IOC_SETVERSION`, and any token
    whose direction is `_IOC_WRITE` on a regular file label (refused by token shape, not resolved).
  - `READ_ONLY: frozenset[str]`, `WRITES: frozenset[str]`, `PROCESS: frozenset[str]` — spec §2's three classes,
    restricted to `MEASURED_SYSCALLS - DENIED_SYSCALLS`. **The rule for a measured name the spec's lists do not
    name (r1 Claude F5):** it goes to WRITES (spec §2: "a call is a WRITE unless the table names it READ-ONLY"),
    which can only add cross-run refusals. It never goes to PROCESS by judgement: PROCESS admits a measured name
    only if it is in spec §2's process list (`clone`, `clone3`, `fork`, `vfork`, `wait4`, `exit_group`, `brk`,
    `futex`, `rt_sig*`, `getpid`) or takes NO fd and NO path argument in its strace line shape (checked against
    `scripts/fixtures/strace-lines/`); each PROCESS member beyond the spec's list carries a one-line reason.
  - `ALLOWED_SYSCALLS = READ_ONLY | WRITES | PROCESS`; `ALLOWED_IOCTLS = MEASURED_IOCTLS - DENIED_IOCTLS`.
  - `classify(call: Call) -> tuple[str, str | None]` → (`"read"`/`"write"`/`"process"`/`"list"`, refusal or None).
    An `open*` with `O_CREAT|O_WRONLY|O_RDWR|O_TRUNC|O_TMPFILE` is a write; `mmap` with `MAP_SHARED` and
    `PROT_WRITE` on a file label is a write.

- [ ] **Step 1: failing cases:**
  - `"the measured constants ARE the committed measurement"` (r1 Claude F4; a subset test against a constant
    typed into the same module holds by construction): the case LOADS
    `docs/reviews/measurements/2026-11-NN-strace-on-runner.json` (`docs` is a staged root, so it is in the
    mutation tree) and asserts `MEASURED_SYSCALLS` and `MEASURED_IOCTLS` EQUAL its unions and `STRACE_VERSION`
    equals its version line. Adjacent negative: a copy of the JSON with one extra name makes the case red. Then
    `"the allowlist is a subset of the measured set"`: `ALLOWED_SYSCALLS <= MEASURED_SYSCALLS` and
    `ALLOWED_IOCTLS <= MEASURED_IOCTLS` (backlog #590's FAILS IF, second clause, now against the file).
  - `"an unlisted measured name is a write"`: a measured name in none of spec §2's lists (take one from the JSON,
    e.g. whichever of `memfd_create`/`prctl`/`pidfd_open` was measured) → `("write", None)`; negative: `futex` →
    process.
  - `"no denied name is allowed"`: `not (ALLOWED_SYSCALLS & DENIED_SYSCALLS)`, same for ioctls.
  - `"an unmeasured syscall is refused"`: a `name_to_handle_at(...)` line → `unclassified syscall`; negative: a
    measured `newfstatat` → `("read", None)`.
  - `"ioctl FS_IOC_SETFLAGS is refused"` (backlog #590 FAILS IF, first clause) → `unclassified ioctl`; negative: a
    measured `TCGETS` → read.
  - `read`, `close`, `lseek`, `fcntl`, `PROT_READ` `mmap` of a staged file → read; `ftruncate` of it → write
    (§8.4, r3 Claude F4).
  - `truncate`, `chmod`, `utimensat`, both sides of `rename` → write (§8.4, r2 Codex F6).
  - `openat(..., O_RDWR)` → write; `openat(..., O_RDONLY)` → read; `getdents64` → list.
  - every `DENIED_SYSCALLS` member → its named refusal (`io_uring`, `unmodelled clone/unshare`, `mount family`).
- [ ] **Steps 2-5:** red, implement, green, pins, mutate `--only`, commit.

### Task 3.2: the per-run record, the seed check and the cross-run check

**Files:** Modify `scripts/strace_reads.py`, its manifest, pins.

**Interfaces:**
- Produces:
  - **ONE path normal form, `norm(path, ctx)` (r1 Claude F1; spec §2: "Paths under a run's copy are compared
    relative to that copy").** A path at or under `ctx.copy` (its `.home` included) becomes `copy:<relative>`; any
    other path stays absolute. Every path set below is in this form, so two targets traced in two different copies
    meet on `copy:docs/generated/flag`, never miss on `/tmp/copyT/…` vs `/tmp/copyU/…`.
  - `@dataclass(frozen=True) class Record: reads: frozenset[str]; probed: frozenset[str]; probed_stat_only:
     frozenset[str]; listed: frozenset[str]; wrote: frozenset[str]; all_named: frozenset[str]; all_listed:
     frozenset[str]; trace: str` (`trace` = `"complete"` or a `REASONS` member). `reads`/`probed`/`listed` hold the
     `copy:` paths at or under a staged root, a root itself included, written without the prefix (the selector's
     form); `wrote`, `all_named` (every path the whole trace read or probed) and `all_listed` are in `norm` form and
     keep every path. **`probed_stat_only` (r1 Codex F3, Claude F3)** ⊆ `probed`: the paths whose ONLY calls were
     the `stat`/`lstat`/`newfstatat`/`statx`/`statfs`/`access`/`faccessat`/`faccessat2` family (never opened, never
     `execve`d, never listed, never `chdir`ed). A path probed by stat AND a failed open is NOT in it. Spec §2's Q1
     fallback measures "the same read sets without `probed`'s stat and access entries", i.e. `probed -
     probed_stat_only`; this is the provenance that makes it computable.
  - `record_from_log(text: str, ctx: Ctx, strace_version: str) -> Record` — version ≠ `STRACE_VERSION` →
    `strace version`.
  - `EXEMPT_WRITES` — `/dev/null`, `/dev/zero`, `/dev/full`, `/dev/random`, `/dev/urandom`, `/dev/tty`,
    `/dev/pts/*`, everything under `/proc` and `/sys` (spec §2; `/dev/shm` NOT exempt).
  - `merge_seeds(a: Record, b: Record) -> Record` (r1 Codex F2; spec §3: green and complete "under BOTH seeds") —
    if either seed's `trace` is not `complete`, the result carries that refusal (`a`'s first); else if
    `reads`/`probed`/`listed` differ → `seed-dependent reads`; else the shared sets, with `wrote`, `all_named` and
    `all_listed` the UNION of both seeds (a write that happens only under seed B still reaches `cross_run`) and
    `probed_stat_only` the INTERSECTION (a path is stat-only only if it was so under both seeds).
  - `cross_run(records: dict[str, Record]) -> dict[str, Record]` — target T refused (`cross-run flow`) when its
    `all_named` meets another target's `wrote` (exemptions dropped first), or its `all_listed` holds an ancestor
    of such a path, all compared in `norm` form.

- [ ] **Step 1: failing cases** (§8.4, §8.5): a read of a path another target wrote → refused; a listing of
  `docs/generated` when another wrote `docs/generated/flag` → refused, negative: a listing of a sibling directory;
  two targets each opening `/dev/null` `O_RDWR` → neither refused, while a `/dev/shm/x` write read later → refused;
  two seeds whose sets differ → `seed-dependent reads`, equal → kept; **(r1 Codex F2)** a complete seed A and a
  refused seed B with EQUAL sets → B's refusal, never `complete`, and the mirror (refused A); a write present only
  under seed B is in the merged `wrote` and refuses a target that reads it; **(r1 Claude F1)** two records built by
  `record_from_log` from two logs with DIFFERENT copy roots (`/tmp/cU`, `/tmp/cT`), U writing
  `/tmp/cU/docs/generated/flag` and T listing `/tmp/cT/docs/generated` → T refused, negative: T listing
  `/tmp/cT/docs/other`; **(r1 Codex F3)** `probed_stat_only` holds a path only `newfstatat`-probed, not one
  `newfstatat`-probed and failed-`openat`ed, nor one `access`-probed then `execve`d; a version mismatch →
  `strace version`;
  `probed` holds a failed open, a failed `execve`, a `chdir`, a `statfs`, an `inotify_add_watch` (spec's
  definition); `readlink` → `reads` of the link; `execve` of a staged script → `reads`; `openat2` recorded; a
  failed `unlink` → `wrote`.
- [ ] **Steps 2-5:** red, implement, green, pins, mutate `--only`, commit.

**Pre-push (slice 3):** as slice 2. **Merge gate:** the measured-set EQUALITY case (Task 3.1) is green; it reads the
merged slice 1 JSON itself, so no reviewer diff is needed.

---

## Slice 4 — the `record-reads` job (spec §2 Record, Store; §8.5)

### Task 4.1: `--record-reads` mode in `check-plan-code.py`

**Files:**
- Modify: `scripts/check-plan-code.py` (top-level `import strace_reads`, which makes it a harness file by
  `harness_files`; the new mode; self-test cases; its own declared count and `EXPECTED_MUTATIONS` entry)
- Modify: `scripts/mutations/check-plan-code.json`, `scripts/mutations/expected_mutations.py`,
  `scripts/check-fixture-variation.py` (`EXAMINED_KEYS["check-plan-code.py"]` gains the new functions' keys): the
  WM pins

**Interfaces:**
- Produces:
  - `RECORD_SEEDS: tuple[int, int]` — slice 1's two values.
  - `TRACE_FACTOR: int` — slice 1's measured value.
  - `recording_env(copy: pathlib.Path, seed: int) -> dict[str, str]` — `mutation_env(copy, seed)` plus the PR
    shard keys: `EVENT=pull_request`, `BASE_REF=master`, `GITHUB_EVENT_NAME=pull_request`,
    `GITHUB_BASE_REF=master`, `GITHUB_REF=refs/pull/0/merge`, and `SHARD_INDEX`, `SHARD_TOTAL`,
    `SWEEP_TIMEOUT_MINUTES` copied from the job env. Raises `RecordRefused("GIT_DIR/GIT_WORK_TREE set")` if either
    is in the result.
  - `record_target(root: pathlib.Path, target: str, seed: int, runner) -> strace_reads.Record` — traced run FIRST in
    a fresh `stage_tree` copy with a fresh `CHILD_HOME`, timeout `SUITE_TIMEOUT * TRACE_FACTOR`, then the plain run
    in ANOTHER fresh copy (`control_parts`). **The traced log is parsed (`record_from_log`) IMMEDIATELY after the
    traced run, while its copy still exists and BEFORE the plain run starts** (r1 Claude F11b; spec §2 resolves the
    pre-existing-link test "at parse time, before the copy is removed"); only then is the traced copy deleted. Not
    green by `control_is_green`, or case counts unequal → `trace="control red"` / `"case count differs"`. **Recorder
    failures (r1 Claude F10; spec §8.3, §2):** no `strace` on `PATH` → `strace missing`; strace's stderr carrying
    `PTRACE_TRACEME`/`ptrace` `EPERM`/`Operation not permitted` on attach → `ptrace denied`; strace's own failure
    (its stderr's `strace:` error line, told apart from the tracee's status, since strace exits with the tracee's
    code) → `strace exit`; the traced run killed at its timeout → `timeout`. Each is a `REASONS` member.
    `runner` is injected so the self-test fakes strace.
  - `record_reads(root: pathlib.Path, out: pathlib.Path, runner=…) -> int` — every manifest target, sorted, both
    seeds, `merge_seeds`, then `cross_run`; writes `readsets.json`
    `{sha, key: {...}, targets: {t: {reads, probed, probed_stat_only, listed, wrote, trace, recorder, rc, cases,
    seeds, blobs}}, tally: {reason: n}}` where `blobs` maps each tracked path in `reads` to its git blob id
    (`probed_stat_only` carried through serialisation for Q1; r1 Codex F3). rc 0 when every target appears exactly
    once. It also prints `key=readsets-<python>-<harness hash>-<sha>` to `$GITHUB_OUTPUT` when that variable is set
    (r1 Claude F19: the cache-save step's key has a producer).
  - `validity_key(root: pathlib.Path) -> dict` — Python `major.minor.micro`, `harness_hash` (sha256 over the sorted
    `harness_files` blob ids), `recorder`, `STRACE_VERSION`, `node -v` minor, `ImageOS`, `ImageVersion`, blob ids
    of `DEPENDENCY_MANIFESTS`.
- [ ] **Step 1: failing cases:** the traced run is first and in a different copy from the plain run (the fake
  runner logs the cwd of each call); the traced log is parsed before the traced copy is removed and before the
  plain run (the fake runner's call log orders `run traced`, `parse`, `rm traced copy`, `run plain`); each recorder
  failure above refuses with its reason (missing binary, the `ptrace` EPERM text, a `strace:` error line, the
  timeout), each with its adjacent green (a red SUITE under a working strace is `control red`, not `strace
  exit`); `key=` reaches a fake `$GITHUB_OUTPUT`; a red plain control refuses only its own target; unequal case counts refuse;
  a target missing or doubled → rc ≠ 0; a recording under one seed only is impossible (both seeds always run);
  the child env carries `EVENT=pull_request` and the shard keys; `GIT_DIR` in the env refuses every target;
  the key changes when each element changes (one case per element, adjacent: unchanged element → equal key).
- [ ] **Steps 2-5:** red, implement, green, update `check-plan-code.py`'s declared count and its manifest entries,
  mutate `--only scripts/check-plan-code.py` is the WHOLE harness: run the full `--mutate .` locally only if the local
  budget allows, otherwise rely on the PR's ALL sweep and say so in the PR body. Commit.

### Task 4.2: the job, the save condition, the live cases

**Files:**
- Modify: `.github/workflows/ci.yml` (new job `record-reads`; a YAML anchor `&shard-env` on the `mutation-sweep`
  step's `env` reused by `record-reads`)
- Modify: `scripts/strace_reads.py` (`--live-cases`: Linux only; elsewhere prints `CANNOT RUN — needs Linux and
  strace; treat as NOT RUN` and exits 2)

**Interfaces:**
- `record-reads`: `if: github.event_name == 'schedule' || (github.event_name == 'push' && github.ref == 'refs/heads/master')`;
  `runs-on: ubuntu-latest`; `timeout-minutes:` the SUM of slice 1's six shards' driver times × 1.5, rounded up
  (r1 Claude F11a: `record-reads` is ONE unsharded job, so one shard's time would be about 6× short and no recording
  would ever save; INFERRED until the first run, then re-set from it); steps: checkout `fetch-depth: 0`, setup-node
  22, setup-python 3.12, Python pin, `npm ci`, strace install, `python3 scripts/strace_reads.py --live-cases`, then
  the recording step (`id: rec`) `python3 scripts/check-plan-code.py --record-reads "$RUNNER_TEMP/readsets.json"`
  with `env: *shard-env`, which writes `key=` to `$GITHUB_OUTPUT` (Task 4.1), then `actions/cache/save@v4` with
  `key: ${{ steps.rec.outputs.key }}` (r1 Claude F19), `if: success()`. The step that records exits nonzero when a
  target is missing or doubled, so `success()` is the save condition; a cancelled or timed-out job never reaches it.
  A schedule run at the same sha as a master push produces the same key; the save is refused for an existing key,
  which is harmless (the payload for that sha already exists). If the action FAILS the step on a duplicate rather
  than warning (UNVERIFIED, r1 Claude "could not check"), the save step gets `continue-on-error: true` and the
  case below pins it.
- `--live-cases`: runs, under `strace -f -yy`, a real child that calls `os.unshare(os.CLONE_FS)` and one that calls
  `setns` on `/proc/self/ns/mnt` (it may fail with EPERM; the call is still logged), and asserts each record's
  `trace` is the refusal (spec §8.4, r2 Codex F2: EXECUTED, not synthetic).

- [ ] **Step 1:** failing self-test case in `check-plan-code.py`: `sweep_limit_pin`-style read of `ci.yml` asserts
  `record-reads` has no `needs:` on `mutation-sweep`, never runs on `pull_request` or `batch/**`, and saves only
  under `if: success()` (spec §8.5), with its key read from `steps.rec.outputs.key`. Adjacent negative: the
  `mutation-sweep` job keeps its triggers.
- [ ] **Steps 2-4:** implement, green, WM pins for `check-plan-code.py` and `strace_reads.py`, commit.

### Task 4.3 (POST-MERGE; blocks slice 6, not slice 4's merge): the first master run, measured; backlog #590 closed

Both observations exist only after slice 4 merges (r1 Claude F17), so they are not slice 4's merge gate. Slice 6
does not start until both hold.

**Files:** Modify `docs/reviews/measurements/2026-11-NN-strace-on-runner.md` (a "first record-reads run" section),
`docs/backlog.md` (#590 ✅ with the evidence; #586 progress), `.github/workflows/ci.yml` (`timeout-minutes` re-set
in a follow-up commit on the next docs batch if the measured duration differs).

- [ ] After merge, wait for the first master `record-reads` run (background poll). Record MEASURED: duration, the
  refusal tally by reason, how many targets got a complete read set, the save's key. This is the spec's "build step
  1 counts refusals by reason" (cross-run, seed-dependent, external path removed, …).
- [ ] Backlog #590 closes when: Task 3.1's measured-set equality, subset and FS_IOC_SETFLAGS cases, Task 2.2's R4-F1 case and Task 4.2's
  live cases are green on master. Its FAILS IF are those cases' adjacent pairs.

**Pre-push (slice 4):** `python3 scripts/check-python-pin.py`; `python3 scripts/check-plan-code.py --self-test`;
`python3 scripts/strace_reads.py --self-test`; and the harness note: this PR's own sweep runs ALL.

---

## Slice 5 — the pure selector (spec §2 diff, comparison set, Use; §3; §8.2, §8.3)

### Task 5.1: `Δ` and the diff parser

**Files:**
- Create: `scripts/reach_select.py`, `scripts/mutations/reach_select.json`; W3-W7 files.

**The import direction, decided (r1 Claude F9).** `reach_select.py` loads `check-plan-code.py` ONCE, at module
level, through `importlib` (the spike's method), and owns every selection mode, `--select-only` included (Task
6.1). `check-plan-code.py` NEVER imports `reach_select`: no cycle, no re-execution of the harness inside it.
Consequence, stated: `reach_select.py` is NOT in `harness_files`, so it is not in the recording's validity hash.
That is correct, because the hash pins what a RECORDING depended on (the harness that ran the suites), and
`reach_select` takes no part in recording. A change to `reach_select.py` is an ordinary staged path: its own
manifest picks it.

**Interfaces:**
- `parse_status(raw: str) -> list[tuple[str, str]] | None` — `git diff --name-status -z --no-renames` output;
  None for a non-NUL list, a C-quoted path, or any status outside `A`/`M`/`D`.
- `delta(r_base: list | None, base_head: list | None) -> frozenset[tuple[str, str]] | None` — the UNION of
  (status, path) pairs, never netted; None if either is None.
- [ ] **Failing cases:** a `T` in either list → None (FULL); a `D`+`A` rename arrives as two pairs; a PR that deletes
  a file master added over R..BASE keeps both pairs (Codex F1's `docs/activated`), negative: a path changed in only
  one list; an empty list → empty set.

### Task 5.2: rule 3 and the observed selection

**Files:** Modify `reach_select.py` and its manifest; `scripts/check-plan-code.py` (the `select_reasons` split
below) with its WM pins. Editing the harness makes this slice's own PR sweep run ALL.

**Interfaces:**
- **`select_reasons` in `check-plan-code.py` (r1 Claude F8).** Today `select_manifests` unions own-source,
  own-manifest and namer hits into one `hit` per path, so its return value cannot say WHY a target was picked, and
  rule 3 must replace rule 4 (naming) but never rule 2 (own source / own manifest). Split it:
  `select_reasons(event, changed, why, sources, harness, roots=HARNESS_TREE, modules=None) -> tuple[str | None,
  dict[str, dict[str, set[str]]], int]` — (`full: <why>` or None = rule 1, `{target: {path: {"own-source" |
  "own-manifest" | "named" | "dir-quote" | "walks-root" | "root-quote"}}}`, paths outside the staged tree), the SAME
  body, recording the clause that added each target. `select_manifests` becomes a thin wrapper over it whose
  return value and log lines are unchanged. Rule 2 = `own-source`/`own-manifest`; rule 4 = every other reason.
- `pick_reason(rec: dict, delta: frozenset, named_added_deleted: set[str]) -> str | None` — `"reads"`, `"probed"`,
  `"probed ancestor"`, `"listed ancestor"`, `"named"` or None (spec Use 3(a)-(c)).
- `observed_selection(event: str, changed: list[tuple[str, str]] | None, delta, sources: dict, harness: frozenset,
  readsets: dict | None, modules: dict | None, key_ok: list[str], *, reasons=None) -> tuple[frozenset | None,
  list[str], dict[str, str]]` — (picks, log lines, would-skip `{target: why}`). Rules 1, 2, 4 come from
  `select_reasons` (never re-typed); `reasons`, when given, REPLACES that call (Task 5.2's §8.2 case injects the
  fixture's `today` answers from Task 1.0 Step 1b, so the expected set does not drift with the live tree; r1 Claude
  F7). Rule 3 replaces rule 4 only for a target with a usable set. Log lines `  <t> <- <path> (observed)` /
  `(named: untraced)`; one `WOULD-SKIP:` line.
- [ ] **Failing cases (spec §8.2 and §8.3, each with its adjacent negative):** `select_manifests`' result and log
  lines are byte-identical to before the split over the repo's own sources for three recorded diffs (PR #545,
  #543, #539), and its existing cases stay green; a target picked ONLY because the changed path is its own source
  (or its own manifest) is picked even with a usable read set that does not hold the path, negative: the same
  target picked only by `named` is dropped by rule 3; the committed spike fixture
  (`scripts/fixtures/observed-reach-spike-pr545.json`, spawners marked untraced, `today` injected as `reasons`)
  plus PR #545's diff selects EXACTLY the fixture's untraced targets with a non-empty `today` (33 by spec §8.2)
  plus `check-canonical-source`, `check-dashboard-entry`, `check-features`, each with its reason; a traced spawner whose child read a changed path is picked and one whose children read none is not;
  a traceable non-reader with no mandatory reason is not picked; own-source and own-manifest changes pick with no
  read set; a FULL rule still runs ALL; a MODIFIED path in `probed` only (by size; by executable bit) picks, an
  unprobed modification does not; a master add over R..BASE probed under a computed name picks, an unprobed add in
  the same directory does not; a master delete of a `reads` path picks; an `A`/`D` at any depth below a listed
  directory picks, and a `D` of a directory's last file picks a target that listed only the grandparent, a `D`
  outside every listed directory does not; an added path named only by an imported module picks via `_importers`;
  an `A` of `docs/superpowers/archive/x.md` picks a target that only stat-probed the absent
  `docs/superpowers/archive`, and the mirror `D`, while an `A` under an unprobed sibling does not.

### Task 5.3: usability and the restored payload

**Interfaces:**
- `usable(rec: dict) -> str | None` — None when `trace == "complete"`, rc 0 and case counts equal under both seeds;
  else the reason.
- `key_mismatches(payload_key: dict, own_key: dict) -> list[str]` — the differing element names.
- `restore_check(payload: dict | None, base_sha: str, is_ancestor) -> str | None` — None when the payload parses,
  its sha is an ancestor of BASE (injected predicate) and every target appears once; else why.
- `pick_cache(entries: list[dict] | None, prefix: str, is_ancestor, distance) -> tuple[str | None, str]` (r1 Claude
  F12; `ci.yml`'s own rule that a `run:` block decides nothing) — from the Actions API's cache list (injected),
  keeps the keys with `prefix` whose sha `is_ancestor` of BASE, returns the one with the smallest `distance` (commits
  from it to BASE, injected), and why; None with the reason on an API failure (`entries is None`), no candidate, or
  a key whose sha does not parse.
- [ ] **Failing cases (§8.3):** missing, red, short-count, wrong-key (one case per key element: strace version,
  Node minor, runner image, a `package-lock.json` blob changed over R..BASE), wrong-recorder and unvalidated sets
  each give today's rule; an unparseable cache → today's rule for all; each with an equal-key negative.
  `pick_cache`: the nearest of two ancestors is chosen, a NEARER non-ancestor (a sibling branch's sha) is skipped,
  a key with another prefix is skipped, `None` entries → None with `cache list failed`, an empty list → None.
- [ ] **Steps (each of 5.1-5.3):** red, implement, green, W1-W7 (and, in 5.2, the WM pins for
  `check-plan-code.py`), mutate `--only scripts/reach_select.py`, commit.

**Pre-push (slice 5):** `python3 scripts/reach_select.py --self-test`; `python3 scripts/check-plan-code.py
--self-test`; `python3 scripts/check-plan-code.py --mutate . --only scripts/reach_select.py`; the harness note: this
PR's own sweep runs ALL (Task 5.2 edits `check-plan-code.py`).

---

## Slice 6 — shadow: `sweep-select` reports, nothing skips (spec §2 Resolve, shadow data; §7 Q1, Q4)

### Task 6.1: `--select-only` in `reach_select.py`, `--verdicts` in `check-plan-code.py`

**Files:** Modify `scripts/reach_select.py`, `scripts/check-plan-code.py`, both manifests; WM pins for both.

**Interfaces:**
- `python3 scripts/reach_select.py --select-only OUT --readsets FILE --r-base FILE --base-head FILE --image
  "$ImageVersion"` (in `reach_select`, per the import direction of Task 5.1) → writes the selection artifact
  `{pr, head, base, r, image, key_check, today: [...], observed: [...], would_skip: {t: why}, picks: {t: rule},
  q1_probe_delta}` and prints the log lines. `q1_probe_delta` = picks on PR #543's diff (its two commits pinned as
  constants) with the read sets as recorded, minus picks with each target's `probed` replaced by `probed -
  probed_stat_only` (Task 3.2's provenance; r1 Codex F3, Claude F3) (spec §2 Q1 fallback; > 5 → report
  `Q1 FALLBACK: revert 3(c) to option A`). It also writes `targets=<one line>` to `$GITHUB_OUTPUT` (the list, or
  `full: <why>`), unused until slice 8.
- `--verdicts FILE` → a FIRST header line `{image: <ImageVersion env>, shard, run_id}` (r1 Codex F9, Claude F16:
  the drift evidence), one JSON line per mutant run `{target, mutant, seed, verdict}` (`killed`, `survived`,
  `cannot-run`, `timeout`), one per control `{target, control: green|red}`, final `{complete: bool}` (false when
  budget-stopped or a control did not run). Written by `run_mutations`; no verdict changes.
- [ ] **Failing cases:** `today` in the artifact equals `select_manifests`' result on the same inputs (the shadow
  invariant: nothing the shard runs changes); a budget-stopped run writes `complete: false`; every mutant has
  exactly one line; adjacent: a complete run writes `complete: true`; the header carries the `ImageVersion` it was
  given, and an unset one is written `null`, never omitted; `q1_probe_delta` over a two-target fixture where one
  target's only probe of a changed path is a `newfstatat` (stat-only) gives 1, and where that path was ALSO a failed
  open gives 0.

### Task 6.2: the jobs

**Files:** Modify `.github/workflows/ci.yml`.
- `sweep-select`: `pull_request` only; NOT in `mutation-sweep`'s `needs:` in this slice; `permissions: contents:
  read, actions: read`. Steps (r1 Claude F12; spec §2 Resolve: it "runs the shards' `setup-node` step", since
  `node -v` is a key element): checkout `fetch-depth: 0` (the ancestor test and the R..BASE diff need history),
  setup-node `'22'`, setup-python `'3.12'`, the Python-pin step; then ONE step that fetches the cache list
  (`gh api repos/{owner}/{repo}/actions/caches?key=readsets-<python>-<hash>-`) to a file and passes it to
  `reach_select.py`, whose `pick_cache` decides (no ancestry or "nearest" logic in YAML); `actions/cache/restore`
  by the exact key it printed; `reach_select.py --select-only … --image "$ImageVersion"`; upload
  `selection-<run_id>-<run_attempt>` (`retention-days: 90`, `if: always()`). A miss or API failure is logged and
  the artifact says `full: <why>`.
- `mutation-sweep`: adds `--verdicts "$RUNNER_TEMP/verdicts.jsonl"` and an upload of
  `verdicts-<run_id>-<run_attempt>-<shard>` (`if: always()`, 90 days) on every event; its `ImageVersion` is in the
  verdicts header (Task 6.1).
- [ ] **Failing case:** a `ci.yml` read in `check-plan-code.py`'s self-test asserts `mutation-sweep` does not consume
  `sweep-select`'s output in this slice (the shadow invariant, made mechanical); slice 8 flips this case.

**Pre-push (slice 6):** `python3 scripts/check-python-pin.py`; `python3 scripts/check-plan-code.py --self-test`;
`python3 scripts/reach_select.py --self-test`; WM pins for both (Tasks 6.1, 6.2).
**Merge gate:** the PR's own run uploads one `selection-*` and every shard's `verdicts-*`.

---

## Slice 7 — the comparator (spec §2 "A MISS, precisely"; §8.6)

### Task 7.1: `--mutant` replay

**Interfaces:** `check-plan-code.py --mutate . --only <target> --mutant <name> --seeds <s>` runs ONE manifest entry
(matched by its `name`) in a fresh staged tree under ONE seed (the spelling spec §2 names). **Today's `parse_seeds`
refuses one seed** ("it takes two or more, because one seed cannot show a kill that depends on the seed"; r1 Codex
F4), and that refusal stays for every sweep: `parse_seeds(spec, minimum=2)` gains a `minimum` parameter, and only
the `--mutant` path calls it with `minimum=1`, because a replay's seed is FIXED by the comparator (it runs each
`RECORD_SEEDS` value separately, 3 times), not a sample of hash orders. Output: one line `verdict=<killed|survived|
cannot-run|timeout>` plus the control's, so the comparator reads a verdict, not prose.
- [ ] **Failing cases:** an unknown name → CANNOT RUN rc 2; a known name runs one mutant only; `--mutant X --seeds
  5` runs under seed 5 (the fake runner sees `PYTHONHASHSEED=5`) and prints one `verdict=` line; adjacent: a SWEEP
  (`--mutate .` without `--mutant`) with `--seeds 5` is still CANNOT RUN, and `--mutant X --seeds 5,5` repeats a seed
  and is refused. WM pins for `check-plan-code.py` (W6: `parse_seeds.minimum` varied).

### Task 7.2: `scripts/shadow-compare.py` and its job

**Files:** Create `scripts/shadow-compare.py`, `scripts/mutations/shadow-compare.json`; W1-W8 files;
modify `scripts/reach_select.py` (`trusted_ledger`, below, so that `sweep-select` in slice 8 uses the SAME
acceptance rule; its manifest and WM pins); `.github/workflows/ci.yml` (job `shadow-compare`, `schedule` daily +
`workflow_dispatch`, `contents: read`, `actions: read`, and **`concurrency: {group: shadow-ledger,
cancel-in-progress: false}`** at job level, r2 Codex F4).

**Why the job-level group (r2 Codex F4).** Two overlapping writers that both read ledger L0 let the later
finisher upload a ledger built on L0, erasing the earlier one's latched miss. Today's workflow-level group
(`ci-${{ github.workflow }}-${{ github.ref }}`, cancel only on `pull_request`) already serializes the schedule and
a dispatch on master, but nothing in this plan depended on it by name, and a group that is changed for another
reason would silently reopen the race. The job-level group states the dependency: one `shadow-compare` job runs at
a time; GitHub cancels only a PENDING job that a newer one replaces, never the running one, and a pending job has
read nothing. The predecessor is downloaded inside the job, so after the group is acquired.

**The job, step by step (r1 Codex F5, Claude F21).** checkout `fetch-depth: 0`; setup-node `'22'`; setup-python
`'3.12'`; the Python-pin step; `npm ci` (a replay stages `node_modules/typescript`); then ONE step,
`python3 scripts/shadow-compare.py --run --out "$RUNNER_TEMP/ledger.json"`, which (all `gh` calls injected in the
self-test): (1) finds the newest TRUSTED ledger (below) and downloads it; (2) lists merged PRs since
`SHADOW_START`, their pushes' runs, and downloads each `selection-*`/`verdicts-*` pair it needs; (3) compares,
replays, decides; (4) writes the ledger. Then `actions/upload-artifact` named exactly **`shadow-ledger`** (a FIXED
name; the run id is inside `ledger.json`; artifact names need be unique only within one run), `retention-days: 90`,
**`if: success()`**.

**Finding the ledger: exact name, every page, provenance checked (r2 Codex F3, F5).** The artifacts API's `name`
parameter is an EXACT match, not a prefix, so a suffixed name could never be found by it; hence the fixed name.
`gh api --paginate "repos/{owner}/{repo}/actions/artifacts?name=shadow-ledger&per_page=100"`, then locally: keep
`name == "shadow-ledger"` and `expired == false` (the `name` filter is re-checked, never trusted). A NAME proves
nothing, because any workflow run, a pull request's included, can upload an artifact with that name. So for each
candidate, newest `created_at` first, `gh api repos/{owner}/{repo}/actions/runs/<workflow_run.id>` and accept it
only if `trusted_ledger(run, default_branch)` holds: `run.event in {"schedule", "workflow_dispatch"}`, `run.path
== ".github/workflows/ci.yml"`, `run.head_branch == default_branch` (from `gh api repos/{owner}/{repo}`, never
typed), and `run.head_repository.id == run.repository.id` (a fork's branch may be NAMED `master`). An untrusted
candidate is skipped and logged `LEDGER IGNORED: <artifact id> <why>`; it is not ours, so skipping it loses
nothing. The newest TRUSTED one is the predecessor; it must then parse to the schema below (`schema == 1`, every
`counts` value an int, `shadow_start` a string). **A trusted ledger that fails the schema is a hard failure**
(nonzero, nothing uploaded), never "use the next one", because falling back to an older ledger could drop a miss
the newer one latched. `trusted_ledger` and the schema check live in `reach_select.py`, and `shadow-compare.py`
imports them, so the comparator and `sweep-select` cannot disagree on what counts.

**Fail closed on the ledger itself:** "no trusted `shadow-ledger` has ever existed" (no candidate passes) starts an
empty ledger; a FAILED listing, run lookup or download exits nonzero and uploads NOTHING, because an empty ledger
would erase a latched miss. A daily run re-uploads every decided row, so the newest ledger is never older than a
day while the job runs.

**The epoch (r2 Codex F6).** A ledger belongs to ONE `shadow_start`. The predecessor is merged only when its
`shadow_start` equals the running code's `SHADOW_START`; otherwise this run starts a NEW epoch: `prs` and `counts`
are rebuilt from `SHADOW_START` alone (previous-epoch decisions, misses and post-switch events are NOT carried),
the old epoch is kept as `previous_epoch: {shadow_start, counts}` for the record, and the run logs `EPOCH:
<old> -> <new>`. The old ledger artifacts stay until their 90-day retention. Moving `SHADOW_START` is the ONLY way
to clear a latch (Task 8.2). **Bound, stated:** that commit is a semantic loosening `check-merge-ready.py` cannot
see (its `hold_reasons` are syntactic); spec §7 Q5 makes it the owner's, so the commit's PR body says
`EPOCH RESET` and its author asks the owner before merging. That is a convention, not a machine.

**The ledger artifact's schema** (one JSON file, `ledger.json`): `{schema: 1, run_id, generated_at,
shadow_start, previous_epoch: {shadow_start, counts} | null, q1_probe_delta: <from the newest selection-* of a
PR this ledger lists as MERGED, or null; never an unmerged PR's run, whose selector code no review has passed>, prs: {"<N>": {decision:
"clean"|"miss"|"inconclusive"|"pending"|"not a sample", decided_at, pushes: [{head, base, result, differing:
[...], drift: bool}]}}, counts: {clean_consecutive_from_start, miss, inconclusive, unreproduced, drift_events,
post_switch_events}}` (`post_switch_events` is 0 until slice 8, Task 8.2).
`clean_consecutive_from_start` counts complete clean PRs in merge order from `SHADOW_START`, ignoring
`not a sample` PRs; an `inconclusive` PR does not reset it but is not counted (spec §7 Q4: "20 COMPLETE PRs").

**Interfaces:**
- `SHADOW_START: str` — the date slice 6 merged.
- `pushes(pr: dict, runs: list[dict]) -> list[dict]` — every push's PR run with its own BASE.
- `compare_push(pr_verdicts: list | None, base_verdicts: list | None, would_skip: set[str], select_image: str |
  None) -> tuple[str, list, bool]` — `"clean"`, `"difference"` (with the differing (target, mutant, seed)),
  `"inconclusive"` (missing, expired, `complete: false`, a CANNOT RUN control, a cancelled run), `"pending"` (either
  sweep not finished); the third element is DRIFT (r1 Codex F9, Claude F16; spec §2 Resolve, §4.4): any PR shard's
  verdicts-header `image` differs from the `selection-*` artifact's `image`, or either is null. Drift is COUNTED
  in the ledger, never a verdict change.
- `replay(diff, run_one) -> str` — 3 runs per side under EACH `RECORD_SEEDS` value through Task 7.1's option, in
  fresh trees: stable-and-different under any seed → `"miss"`; anything else → `"unreproduced difference"`.
- `decide_pr(push_results: list[str]) -> str` — any `miss` LATCHES `"miss"`; any pending → `"pending"`; any
  inconclusive or unreproduced → `"inconclusive"`; all clean and at least one would-skip target → `"clean"`.
- `ledger(previous: dict, decided: dict) -> dict` — a PR decided in `previous` keeps its decision, when
  `previous.shadow_start == SHADOW_START`; else a new epoch, as above.
- In `reach_select.py`: `trusted_ledger(run: dict, default_branch: str) -> str | None` (None = trusted, else the
  reason) and `ledger_schema_ok(doc) -> str | None`; `newest_trusted(artifacts: list[dict], get_run) -> tuple[dict
  | None, list[str]]` (the candidate and the `LEDGER IGNORED:` lines), with `get_run` injected.
- [ ] **Failing cases (§8.6, each adjacent):** a cancelled PR run, a missing base artifact, a red control →
  inconclusive; a pending PR not counted and decided by a later run; a miss at a non-final push then a clean final
  push → miss; a flip on re-run → inconclusive; stable on both trees under one seed → miss; reproduces under only
  one of the two seeds → miss; reproduces under neither → unreproduced, listed, never clean; a PR with no would-skip
  target → not a sample; an expired input with no decided row → inconclusive; a decided row survives its input's
  expiry; **(r1 Codex F5) a LATER run after the inputs expired:** run 1 (fake `gh`) decides PR 7 `miss`, writes
  ledger L1; run 2 sees PR 7's artifacts gone and L1 as the newest ledger → PR 7 still `miss` in L2; a failed
  artifact listing in run 2 → nonzero, no ledger written (adjacent: an empty listing at the very first run → an
  empty ledger, rc 0); the newest of two ledgers is the one read; **(r2 Codex F3)** a NEWER ledger uploaded by a
  `pull_request` run with fabricated clean counts is ignored and the older schedule one is read; adjacent, each
  provenance clause alone: `workflow_dispatch` on master → trusted, on a feature branch → ignored; a fork whose
  branch is named `master` (`head_repository.id` ≠ `repository.id`) → ignored; `path` of another workflow →
  ignored; the newest trusted ledger with `schema: 2` → nonzero, nothing uploaded (adjacent: `schema: 1` → read);
  **(r2 Codex F5)** the fake `gh` serves two pages and the trusted ledger is on page 2 → found, never "first run";
  an artifact named `shadow-ledger-old` on page 1 is not a candidate; an `expired: true` one is skipped;
  **(r2 Codex F4)** a `ci.yml` read asserts `shadow-compare` has `concurrency.group == "shadow-ledger"` and
  `cancel-in-progress` false (never absent); **(r2 Codex F6)** L1 at epoch E1 holds `miss: 1`; with `SHADOW_START =
  E2`, L2 has `miss: 0`, no E1 rows and `previous_epoch.counts.miss == 1`, adjacent: same epoch → `miss: 1` kept;
  `q1_probe_delta` comes from a merged PR's `selection-*`, and an unmerged PR's newer `selection-*` with a smaller
  delta is not read; `clean_consecutive_from_start` over
  clean/inconclusive/not-a-sample sequences; **(drift)** a shard image ≠ the selection image → `drift: true`,
  `drift_events` 1, the result unchanged; equal images → `drift: false`; a null image → drift.
- [ ] **Steps:** red, implement with `gh` injected, green, W1-W8, mutate `--only scripts/shadow-compare.py`, commit.

**Pre-push (slice 7):** `python3 scripts/shadow-compare.py --self-test`;
`python3 scripts/check-plan-code.py --mutate . --only scripts/shadow-compare.py`; `python3 scripts/reach_select.py
--self-test`; `python3 scripts/check-plan-code.py --mutate . --only scripts/reach_select.py`;
`python3 scripts/check-python-pin.py`.

---

## Slice 8 — the switch (LAST; spec §7 Q4, §8.1)

**The preconditions are a MACHINE, not a paragraph (r1 Claude F2).** The spec's are: backlog #590 ✅ ("must close
before any skip takes effect; shadow mode alone is not enough"), ≥ 20 COMPLETE clean PRs from `SHADOW_START` with 0
latched misses (§7 Q4), and Q1 decided (§2: probe delta ≤ 5 on PR #543's diff, or 3(c) reverted to option A). The
owner's merge-when-READY rule would merge a slice-8 PR whose prose says "do not merge yet", and
`check-merge-ready.py` cannot HOLD it: `hold_reasons` reads syntactic proxies only (its own comment: "A SEMANTIC
loosening … is outside what a diff rule can see"), and no PR-body marker forces a HOLD (the only body-driven HOLD is
`NO-REVIEW:`, a waiver, not a precondition). So `switch_gate` (Task 8.1) checks all three on EVERY pull request, at
run time, and a refused gate leaves the selection at today's rule. Slice 8 can then be built and merged whenever it
is ready; it skips nothing until the evidence exists, and it STOPS skipping by itself if a miss latches later
(spec §8.1: one case "stops the switch, or reverts it"): a shadow miss, or a post-switch event (Task 8.2), is
counted in the ledger and closes the gate on the next PR. The PR body quotes the gate's line from its own
`sweep-select` log (`SWITCH GATE: refused — <why>` is the expected line while shadow mode runs). A latched miss
goes to the owner (spec §7 Q5: revisit).

### Task 8.0 (only if `q1_probe_delta` > 5): rule 3(c) reverts to option A in `reach_select.py`, with the fixture
case updated, and `Q1_DECISION = "A"`. A separate commit, reviewed on its own. Its own PR cannot open the gate
with the new value: `switch_gate` reads `Q1_DECISION` at BASE, and `shard_targets` refuses any list on a PR that
changes `reach_select.py` (Task 8.1; r2 Codex F2).

### Task 8.1: `switch_gate`, and shards run `sweep-select`'s list

**Files:** Modify `scripts/reach_select.py` (`switch_gate`, `Q1_DECISION`), `.github/workflows/ci.yml`,
`scripts/check-plan-code.py` (`--targets FILE`, `shard_targets`), both manifests and WM pins; the slice-6 invariant
case flipped.

**Interfaces:**
- `Q1_DECISION: str` — `"B"` (the owner's choice) until Task 8.0 sets `"A"`.
- `q1_at_base(src: str | None) -> str | None` — `Q1_DECISION`'s literal from `git show BASE:scripts/reach_select.py`
  (`ast`, the module-level assignment only), or None when the file is absent, unparseable, the name is missing, or
  its value is not exactly `"A"` or `"B"` (r2 Codex F2). Before slice 8 merges, BASE has no `Q1_DECISION`, so
  slice 8's own PR is refused here too.
- `switch_gate(backlog_at_base: str | None, ledger: dict | None, q1_decision: str | None) -> str | None` — None = the
  switch may take effect; else the refusal, checked in this order: `backlog_at_base` is None (`git show
  BASE:docs/backlog.md` failed) → refused; row `| 590 |`'s status cell does not begin with `✅` → `backlog #590
  open`; `ledger` is None (no TRUSTED `shadow-ledger`, its schema failed, or the listing, run lookup or download failed) → `no shadow ledger`;
  `ledger.counts.miss + ledger.counts.post_switch_events > 0` → `latched miss`; `clean_consecutive_from_start < 20` → `N of 20 clean PRs`;
  `q1_decision` is None → `Q1 decision unreadable at BASE`; `q1_decision == "B"` and `ledger.q1_probe_delta` is
  null or > 5 → `Q1 undecided`. **The backlog AND `Q1_DECISION` are read at BASE, never at HEAD** (`q1_decision`
  is `q1_at_base(...)`, never the running module's constant), so a PR cannot enable its own skips by ticking #590
  or by flipping the decision in its diff.
- `sweep-select` (now also in slice 8's `needs:` graph) finds the newest TRUSTED `shadow-ledger` by Task 7.2's
  `newest_trusted` (exact name, every page, run provenance, schema) (`actions: read`,
  already held), runs `switch_gate`, and when refused writes TODAY's selection (`select_manifests`) as `targets`,
  logging `SWITCH GATE: refused — <why>`; when passed, writes the observed list and logs `SWITCH GATE: open`. It
  also runs `git show "$BASE":scripts/reach_select.py` into a file and passes it as `--q1-base FILE` (absent file
  → `q1_at_base(None)`).
- `shard_targets(event: str, select_result: str, output: str | None, full: str | None, reasons: dict, known:
  frozenset, changed_paths: set[str]) -> tuple[list[str] | None, str]` in `check-plan-code.py` — the list a shard
  runs, None = its own rule (today's `select_manifests`, which is FULL on a push or the schedule). **The shard does
  not trust the list (r2 Codex F1, F2): it re-derives `full, reasons` by calling `select_reasons` on its OWN diff**
  (the call `select_manifests` already makes there), and `known` is the manifest target set. Checked in order, the
  first failure → None with that reason: `event != "pull_request"`; `select_result != "success"`; `full` is not
  None (`full: <why>`: rule 1 runs ALL whatever the list says); any `changed_paths` member in `SELECTOR_FILES`
  (`selector changed`; `SELECTOR_FILES = frozenset({"scripts/reach_select.py"})`, so the PR that edits the selector,
  `switch_gate` or `Q1_DECISION` runs today's rule); `output` is not a non-empty JSON list of distinct strings;
  an element not in `known` (`unknown target <t>`); a target whose `reasons` hold `own-source` or `own-manifest`
  missing from the list (`missing mandatory <t>`). Else the list. These checks live in the HARNESS, so a PR that
  edits them gets FULL from `full`. `--targets FILE` reads the file the step wrote from
  `needs.sweep-select.outputs.targets` and calls it.
- **`ci.yml` (r1 Codex F1, BLOCKER).** `mutation-sweep` gets `needs: sweep-select` AND `if: ${{ !cancelled() }}`.
  GitHub skips a job whose `needs:` job was skipped or failed unless its `if:` says otherwise, and `sweep-select`
  is `pull_request`-only, so without that `if:` the master push and the schedule (the FULL sweeps, the backstop of
  spec §4) and every PR whose selector failed would run NO sweep, and `mutation-sweep-complete` (`if: always()`,
  which fails any result but `success`) would report FAILED on every master push. The shard step passes `SELECT_RESULT: ${{ needs.sweep-select.result }}` and the output to
  `shard_targets`, so the decision is in Python, not YAML.
- [ ] **Failing cases, WORKFLOW level (r1 Codex F1):** a `ci.yml` read (the `sweep_limit_pin` style) asserts
  `mutation-sweep`'s `if:` is exactly `${{ !cancelled() }}` (never `success()`, never absent while `needs:` names
  `sweep-select`), that the shard step passes `needs.sweep-select.result` and the output, and that `sweep-select`
  stays out of `mutation-sweep-complete`'s `needs:`. Then `shard_targets`, one case per path: **master push**
  (`event="push"`, `select_result="skipped"`) → None, FULL by `select_manifests`; **schedule** (`"schedule"`,
  `"skipped"`) → None, FULL; **selector failure on a PR** (`"pull_request"`, `"failure"`, any output) → None,
  today's rule; **selector skipped on a PR** (`"pull_request"`, `"skipped"`) → None; **selector cancelled**
  (`"cancelled"`) → None; an empty, truncated (unparseable) or `full: <why>` output with `"success"` → None;
  adjacent: `"pull_request"`, `"success"`, a valid list → that list, sliced by `shard_slice`, nothing else run;
  a valid list on a `push` event → None (a push never honours a list). **(r2 Codex F1, the exact construct)** the
  diff changes `scripts/check-docs.py`, `"success"`, output `["scripts/nonexistent.py"]` → None, `unknown target`;
  output `["scripts/check-features.py"]` (known, but omits `check-docs.py`, which `reasons` mark `own-source`) →
  None, `missing mandatory scripts/check-docs.py`; adjacent: `["scripts/check-docs.py",
  "scripts/check-features.py"]` → that list; a change to `scripts/mutations/check-docs.json` omitted → None (the
  `own-manifest` clause alone); `[1, 2]` and a duplicated element → None; a diff that `select_reasons` calls FULL
  (a harness file) with a valid list → None; **(r2 Codex F2)** a diff touching `scripts/reach_select.py` with a
  valid list holding every mandatory pick → None, `selector changed`; a case asserts every module
  `reach_select.py` imports from `scripts/` (by `ast`, as `harness_files` reads imports) is in `SELECTOR_FILES` or
  in `harness_files`, so a new selector module cannot escape the refusal. `SKIPPED:` replaces `WOULD-SKIP:` in the log.
- [ ] **Failing cases, `switch_gate`:** each refusal above with its adjacent pass: #590's row with `🟠` → refused,
  with `✅ (was 🟠)` → passes that clause; a ledger with 19 → refused, 20 → passes; 20 clean and one `miss` →
  refused; no ledger → refused; `Q1_DECISION="B"` with delta 6 → refused, 5 → passes, `"A"` with delta 6 → passes;
  **(r2 Codex F2)** BASE source with `"B"`, delta 6, while the RUNNING module says `"A"` → refused (the gate takes
  BASE's); `q1_at_base` of a source with `Q1_DECISION = "C"`, of one with no assignment, of `None` and of
  unparseable text → None → refused, adjacent: `"A"` → `"A"`;
  a HEAD backlog with ✅ and a BASE backlog without → refused (the gate reads BASE).
- [ ] **A live check before merge:** the slice-8 PR's own run shows `SWITCH GATE: refused — …` or `open`, its
  shards ran (none skipped by `needs:`), and `mutation-sweep-complete` is green. After merge, the first master
  push's sweep ran FULL with `sweep-select` skipped (the case the BLOCKER was about, observed live).

### Task 8.2: the post-switch detector (§8.1), wired and authorised (r1 Codex F6, Claude F13)

**Files:** Modify `scripts/shadow-compare.py` (`--post-switch`), `scripts/sweep-red-alert.py` (reads an optional
report file), `.github/workflows/ci.yml` (`mutation-sweep-complete`), the manifests and WM pins of both scripts.
- `post_switch(red_targets: set[str], merged: list[dict]) -> list[str]` — the PRs merged since the last green full
  sweep whose `selection-*` `SKIPPED` set meets the red targets (red targets read from each shard's `verdicts-*`;
  the PR from the squash subject's `(#N)`).
- **Where it runs.** A new step in the EXISTING `mutation-sweep-complete` job, before the alert step, with the
  same condition as the alert (`!cancelled() && github.event_name != 'pull_request' && !startsWith(github.ref,
  'refs/heads/batch/')`) plus `needs.mutation-sweep.result != 'success'`: `python3 scripts/shadow-compare.py
  --post-switch --out "$RUNNER_TEMP/post-switch.md"`. The job gains `actions: read` (to list and download
  artifacts); it already holds `issues: write` for `sweep-red-alert.py` (backlog #330). No new job, and no new
  write permission.
- **Its output contract.** The file is Markdown: `POST-SWITCH: <N> merged PR(s) skipped a now-red target` and one
  line per PR (`#N skipped <targets>`), or `POST-SWITCH: none`, or `POST-SWITCH: NOT CHECKED — <why>` (a missing
  selection artifact, an API failure). The step never fails the job. `sweep-red-alert.py` gains env
  `POST_SWITCH_REPORT` (a path): `red_body` APPENDS the file's text when it exists, and appends
  `POST-SWITCH: NOT CHECKED — no report file` when the variable is set but the file is absent. It remains the ONE
  writer of the `sweep-red` issue.
- **It also LATCHES.** `shadow-compare.py --run` (Task 7.2's daily job) calls `post_switch` over every red master
  full sweep since `SHADOW_START` and records each hit in the ledger as `post_switch_events`; `switch_gate` refuses
  on any. So the first §8.1 event turns the switch off by itself, and turning it back on is the owner's (spec §7
  Q5: "revisit on the first §8.1 event"), by a reviewed commit that moves `SHADOW_START` forward, which starts a new EPOCH (Task 7.2: the previous
  epoch's misses and post-switch events are not carried) and so restarts the 20-PR count.
- [ ] **Failing cases:** a red target in a merged PR's SKIPPED set → reported; a red target skipped by no PR → not;
  a missing selection artifact → reported as NOT CHECKED, never silent; the daily run records a hit as
  `post_switch_events: 1` and a later run keeps it after the inputs expire; `sweep-red-alert.py`: with a report file
  the issue body (its fake `gh` state) contains the report's lines; with the variable set and no file → NOT
  CHECKED in the body; without the variable → the body is byte-identical to today's (adjacent); a `ci.yml` read
  asserts the step is in `mutation-sweep-complete`, precedes the alert step, and that the job's permissions are
  exactly `contents: read`, `actions: read`, `issues: write`.

**Pre-push (slice 8):** all slice-6 and slice-7 lines; `python3 scripts/sweep-red-alert.py --self-test`;
`actionlint` if installed, else say NOT RUN.

---

## Self-review notes (coverage of the spec)

- §2 Record, cold traced run first, two fixed seeds, env reproduction, timeout: Tasks 4.1-4.2. Recorder, classes,
  INCOMPLETE triggers, normalisation: Tasks 2.1-3.2. Record fields: Task 3.2/4.1. Store/save condition: Task 4.2.
  Validity key: Task 4.1/5.3. Resolve: Task 6.2 (report-only), 8.1 (effective). Diff + `Δ` + Use: Tasks 5.1-5.2.
  Q1 fallback: Task 3.2 (`probed_stat_only`), 6.1, 8.0, 8.1 (`Q1_DECISION`). Shadow data + comparator + MISS +
  ledger persistence: Tasks 6.1-7.2. Image drift (§2 Resolve, §4.4): Tasks 6.1 (headers), 7.2 (counted).
- §2 "backlog #590 must close before any skip takes effect" and §7 Q4: `switch_gate` (Task 8.1), at run time, so
  no merge rule can bypass it.
- Trust in the gate's inputs (r2): the list is re-validated by the harness (`shard_targets`), every decision input
  is read at BASE, and a ledger counts only from the default-branch comparator run (`trusted_ledger`), one writer
  at a time, within one epoch (Global Constraints, *Trust and provenance*; Tasks 7.2, 8.1).
- §3 fail-closed rows: Task 5.3 (key, restore, usable), Task 4.1 (`GIT_DIR`), Tasks 2.2-3.2 (complete).
- §4 bound 6 / backlog #590: Tasks 2.2 (R4-F1), 3.1 (R4-F2, default-deny), 4.2 (live cases), 4.3 (closure).
- §8.1-8.6: Tasks 8.2/7.2, 5.2, 5.1-5.3, 2.2-3.2, 4.1-4.2, 7.2 respectively.
- §6 (backlog #560 reuse) needs nothing here: the record carries blob ids (Task 4.1).
