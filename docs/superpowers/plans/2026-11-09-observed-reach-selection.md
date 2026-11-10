# Observed-reach selection — implementation plan (backlog #586, prerequisite backlog #590)

> **Anchor:** `dev-speed-first` — **ADR:** none
> **Goal:** A change gets its verdict as fast as the evidence allows, with mutation coverage identical.

**Status:** 📝 DRAFT, written 2026-11-09 from the approved spec at `1a6004c1`. Phase 2: dual adversarial review
to convergence or the round cap (`docs/review-method.md` §0 Q4c) before any task is dispatched. Nothing is built.
Round 1 (both halves, 30 findings incl. 1 BLOCKER) is folded: `docs/reviews/coordinator/plan-586-r1-coordinator.md`.
Round 2 (Codex, 6) is folded: `docs/reviews/coordinator/plan-586-r2-coordinator.md`. Round 3 (Claude, the cap, 8)
ARMED Phase 6 on `ledger-trust` (two consecutive fix-caused rounds). The architecture review
(`docs/reviews/architecture-review-2026-11-09-plan-586-ledger-trust.md`) recommends a redesign that changes one
sentence of spec §2, which is the owner's decision (`docs/reviews/coordinator/plan-586-r3-coordinator.md`).
**The owner approved it (D1) on 2026-11-09 at 14:55, by selection card, answer A "Committed ledger (recommend)".**
The spec §2 diff is applied and slices 6-8 are rewritten to review §6. Because this is a REDESIGN, review restarts
at round 1 (`docs/review-method.md` §0 Q4c, *A REDESIGN RESTARTS THE COUNT*): `plan-586-redesign-r1`, both halves,
scoped to the spec §2 change and slices 6-8. Slices 1-5 can be built now; slices 6-8 wait for that round.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a pull request's mutation sweep runs a guard's mutants only when that guard's suite was SEEN (under
`strace -f`) to read, probe or list a path the comparison set changed; every doubt gives today's selection or more.

**Architecture:** a pure strace-log parser and default-deny classifier (`scripts/strace_reads.py`) turns one traced
`--self-test` run into a read set or a named refusal. A dedicated `record-reads` job on each master push and the
schedule records every manifest target under two fixed seeds and saves `readsets.json` to `actions/cache`. A pure
selector (`scripts/reach_select.py`) applies spec §2 rule 3 over `Δ = (R..BASE) ∪ (BASE..HEAD)`. A `sweep-select` job
computes the selection once; in SHADOW it only reports `WOULD-SKIP`, and a comparator (`scripts/shadow-compare.py`)
checks every would-skip against the base's full sweep and writes a stateless report, which a guarded absorb PR
folds into the committed `docs/shadow-ledger.json` that the switch reads at BASE. Only the last slice lets a shard skip a target.

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
  preconditions are a pure `reach_gate.switch_gate` that `sweep-select` runs on EVERY pull request (Task 8.1; its
  refusals, in order, are listed THERE and only there): while any of them holds it emits TODAY's selection and
  logs `SWITCH GATE: <why>`. Slice 8 merged early is therefore inert, not unsafe (r1 redesign Claude F8).
- **Trust and provenance: ONE rule (design D1, owner 2026-11-09 14:55; architecture review §9).** *Inputs that can
  LOOSEN a gate come from where review lives; inputs that only TIGHTEN can come from anywhere.* So: **the switch
  opens only on what the default branch says, read at BASE; Actions storage can only close it.** Nothing a pull
  request produces or edits may open the switch for that PR or any other. Three clauses carry it, each falling back
  to today's rule: (a) the shard, which runs the HARNESS (`check-plan-code.py`, whose own change already forces
  FULL), re-derives rules 1 and 2 itself and refuses a list that omits a mandatory pick, names an unknown target,
  or arrives on a PR that changes a selector file (Task 8.1 `shard_targets`); (b) every input that can OPEN the
  switch is read at BASE (`docs/backlog.md`, `Q1_DECISION`, `docs/shadow-ledger.json` and the selector's blob);
  (c) the committed ledger changes only through an absorb PR that `scripts/check-shadow-ledger.py` checks against
  BASE's code: a report is absorbed only from a trusted run (`trusted_report_run`: the `shadow-compare.yml`
  `schedule`/`workflow_dispatch` run on the default branch of this repository, by run API metadata, never the
  artifact's name), and the guard REBUILDS the absorb from BASE plus the reports and refuses any other ledger, so
  no decided row or miss is ever lost (Task 7.3). A report is absorbed by its IDENTITY (`<run_id>.<run_attempt>`,
  listed in the ledger; r3 F7), never by a timestamp: publication order is not generation order (r1 redesign Codex X1, X2). A miss or
  post-switch event only tightens, so it is absorbed from ANY trusted report; a clean, inconclusive or
  not-a-sample row and Q1's value only from a report whose `code_sha` is an ancestor-or-equal of BASE, whose
  selector and comparator blobs equal BASE's, and whose epoch is the active one. An epoch change archives the old
  epoch VERBATIM and HOLDs in `check-merge-ready.py`; the gate reads only the active epoch (r1 redesign Codex X3).
  A trusted report whose identity is not yet absorbed is read by the gate only to REFUSE (Task 8.1). **Bound, stated:** `ci.yml`
  and `shadow-compare.yml` are workflow files, so a PR could stop calling `shard_targets`, the gate or the guard,
  exactly as it can delete the sweep today; that is review's to catch, not this plan's. A dishonest
  `reset_by_owner` text is put in front of the owner by the HOLD, and cannot prove it was the owner. GitHub
  returning false run metadata is out of scope.
- **The sweep never stops running because selection did (r1 Codex F1).** `mutation-sweep` runs on every event
  whatever `sweep-select`'s result (skipped on master and the schedule, failed, cancelled), and a shard with no
  usable list runs today's rule (FULL on master and the schedule). Task 8.1 cases it at workflow level.
- **Coverage is identical:** no mutant, case or pin is removed by any slice. Master pushes and the schedule keep
  running the WHOLE manifest.
- Python pinned `3.12` in every new CI job, with the `scripts/check-python-pin.py` step (it fails any job that does
  not pin). Node `'22'` where a job stages `node_modules/typescript`.
- `record-reads`, `sweep-select` and `shadow-compare` are NOT required checks; `mutation-sweep-complete` ignores them.
- Read-only tokens: `contents: read`, plus `actions: read` where a job lists caches or downloads artifacts. A job
  that has NO `permissions:` block today (`verify`) gets the block in full, never one line: a job-level block sets
  every unlisted scope to `none`, `contents` included (r1 redesign Claude F7; Task 7.3). **ONE
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
| 7 | `shadow-compare` / `build-586-s7-compare` | report-writing comparator + `shadow-compare.yml`, `--mutant` replay, committed `docs/shadow-ledger.json`, `--absorb`, `check-shadow-ledger.py`, the epoch HOLD | no | a dispatched master run uploads one `shadow-report-*` (Task 7.3) |
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
  evidence. `scripts/check-ratchet-contract.py` neither passes nor fails four of the new names: its population is
  `GUARD_PATH_RE = scripts/check-[\w.-]+\.py`, which `strace_reads.py`, `reach_select.py`, `shadow-compare.py` and
  `reach_gate.py` do not match (r1 Claude F15; `ci.yml` says the same of `page_markup`/`page_chrome`). Run it anyway;
  do not cite it for them. **`check-shadow-ledger.py` (Task 7.3) DOES match, so the ratchet judges it; cite it there.**
- **W8** if the script uses `fixture_git`, it enters `fixture_git.isolated()` in the exact shape
  `scripts/check-fixture-git-isolation.py` reads (PR #546 tripped it).

**WM — a task that MODIFIES an existing self-tested script (r1 Codex F8, Claude F14).** W1-W8 above are for a
script a task CREATES. A task that adds functions or cases to an existing one (`check-plan-code.py` in Tasks 4.1,
4.2, 5.2, 6.1, 6.2, 7.1, 8.1; `strace_reads.py` in 2.2-3.2 and 4.2; `reach_select.py` in 5.2-5.3, 6.1 and 8.1;
`shadow-compare.py` in 7.3 and 8.2; `reach_gate.py` in 8.1; `check-merge-ready.py` in 7.3; `sweep-red-alert.py` in
8.2) does, in the same commit: **W1** the declared count
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
- `pick_cache(entries: list[dict] | None, prefix: str, is_ancestor, distance, default_ref: str) -> tuple[str | None,
  str]` (r1 Claude F12; `ci.yml`'s own rule that a `run:` block decides nothing) — from the Actions API's cache list
  (injected), keeps the keys with `prefix` whose sha `is_ancestor` of BASE, returns the one with the smallest
  `distance` (commits from it to BASE, injected), and why; None with the reason on an API failure (`entries is
  None`), no candidate, or a key whose sha does not parse. **Scope (r3 Claude F1).** It keeps ONLY entries whose
  `ref == default_ref` (`refs/heads/<default branch>`, from `gh api repos/{owner}/{repo}`, never typed; the
  cache-list API carries `ref`, MEASURED 2026-11-09). An entry with no `ref` is skipped. It returns None with
  `key shadowed in <ref>` when ANY listed entry with the chosen key has another ref, because a pull request's own
  scope can hold the same key, and an exact-key restore takes the run's own scope first (from GitHub's
  documentation, not exercised). **Bound, stated:** an entry created in the PR's own scope between the list and
  the restore needs a workflow the PR adds, the bound *Trust and provenance* already gives to review.
- [ ] **Failing cases (§8.3):** missing, red, short-count, wrong-key (one case per key element: strace version,
  Node minor, runner image, a `package-lock.json` blob changed over R..BASE), wrong-recorder and unvalidated sets
  each give today's rule; an unparseable cache → today's rule for all; each with an equal-key negative.
  `pick_cache`: the nearest of two ancestors is chosen, a NEARER non-ancestor (a sibling branch's sha) is skipped,
  a key with another prefix is skipped, `None` entries → None with `cache list failed`, an empty list → None;
  **(r3 F1)** a `refs/pull/7/merge` entry with a NEARER ancestor sha is skipped and the master one is chosen
  (adjacent: the same entry on `default_ref` is chosen); the chosen master key also listed under
  `refs/pull/7/merge` → None, `key shadowed in refs/pull/7/merge` (adjacent: listed only under master → chosen);
  an entry with no `ref` → skipped.
- [ ] **Steps (each of 5.1-5.3):** red, implement, green, W1-W7 (and, in 5.2, the WM pins for
  `check-plan-code.py`), mutate `--only scripts/reach_select.py`, commit.

**Pre-push (slice 5):** `python3 scripts/reach_select.py --self-test`; `python3 scripts/check-plan-code.py
--self-test`; `python3 scripts/check-plan-code.py --mutate . --only scripts/reach_select.py`; the harness note: this
PR's own sweep runs ALL (Task 5.2 edits `check-plan-code.py`).

---

## Slice 6 — shadow: `sweep-select` reports, nothing skips (spec §2 Resolve, shadow data; §7 Q1, Q4)

**Design D1, owner 2026-11-09 14:55 (selection card, answer A).** This slice changes only by two `selection-*`
fields: `selector_blob` is added (r3 F8: evidence is keyed to the selector that produced it) and `q1_probe_delta`
moves to the comparator (r3 F4: a PR run's own code must not compute an input of the gate). Architecture review §6.

### Task 6.1: `--select-only` in `reach_select.py`, `--verdicts` in `check-plan-code.py`

**Files:** Modify `scripts/reach_select.py`, `scripts/check-plan-code.py`, both manifests; WM pins for both.

**Interfaces:**
- `python3 scripts/reach_select.py --select-only OUT --readsets FILE --r-base FILE --base-head FILE --image
  "$ImageVersion" --selector-blob "$(git rev-parse HEAD:scripts/reach_select.py)"` (in `reach_select`, per the
  import direction of Task 5.1) → writes the selection artifact `{pr, head, base, r, image, selector_blob,
  key_check, today: [...], observed: [...], would_skip: {t: why}, picks: {t: rule}}` and prints the log lines.
  `selector_blob` is the blob of the `reach_select.py` the PR run EXECUTED (the merge commit's), so the comparator
  can tell which selector produced a `WOULD-SKIP` set by CONTENT, not by run metadata (r3 F8). There is no
  `q1_probe_delta` field: the comparator computes it with default-branch code (Task 7.2; r3 F4). It also writes
  `targets=<one line>` to `$GITHUB_OUTPUT` (the list, or `full: <why>`), unused until slice 8.
- `q1_probe_delta(readsets, diff) -> int` is a PURE function in `reach_select.py` (no caller in this slice but its
  self-test; Task 7.2 calls it): picks on PR #543's diff (its two commits pinned as constants) with the read sets
  as recorded, minus picks with each target's `probed` replaced by `probed - probed_stat_only` (Task 3.2's
  provenance; r1 Codex F3, Claude F3) (spec §2 Q1 fallback; > 5 → `Q1 FALLBACK: revert 3(c) to option A`).
- `--verdicts FILE` → a FIRST header line `{image: <ImageVersion env>, shard, run_id}` (r1 Codex F9, Claude F16:
  the drift evidence), one JSON line per mutant run `{target, mutant, seed, verdict}` (`killed`, `survived`,
  `cannot-run`, `timeout`), one per control `{target, control: green|red}`, final `{complete: bool}` (false when
  budget-stopped or a control did not run). Written by `run_mutations`; no verdict changes.
- [ ] **Failing cases:** `today` in the artifact equals `select_manifests`' result on the same inputs (the shadow
  invariant: nothing the shard runs changes); a budget-stopped run writes `complete: false`; every mutant has
  exactly one line; adjacent: a complete run writes `complete: true`; the header carries the `ImageVersion` it was
  given, and an unset one is written `null`, never omitted; the artifact carries the `--selector-blob` it was
  given, and an absent option is CANNOT RUN rc 2, never an artifact without the field; the artifact has no
  `q1_probe_delta` key; `q1_probe_delta` over a two-target fixture where one target's only probe of a changed path
  is a `newfstatat` (stat-only) gives 1, and where that path was ALSO a failed open gives 0.

### Task 6.2: the jobs

**Files:** Modify `.github/workflows/ci.yml`.
- `sweep-select`: `pull_request` only; NOT in `mutation-sweep`'s `needs:` in this slice; `permissions: contents:
  read, actions: read`. Steps (r1 Claude F12; spec §2 Resolve: it "runs the shards' `setup-node` step", since
  `node -v` is a key element): checkout `fetch-depth: 0` (the ancestor test and the R..BASE diff need history),
  setup-node `'22'`, setup-python `'3.12'`, the Python-pin step; then ONE step that fetches the cache list
  (`gh api repos/{owner}/{repo}/actions/caches?key=readsets-<python>-<hash>-`, with `env: GH_TOKEN: ${{
  github.token }}`, r2 redesign Codex C3's class: no `ci.yml` job exports a token to `gh` today) to a file and passes it to
  `reach_select.py`, whose `pick_cache` decides (no ancestry or "nearest" logic in YAML); `actions/cache/restore`
  by the exact key it printed; `reach_select.py --select-only … --image "$ImageVersion" --selector-blob "$(git
  rev-parse HEAD:scripts/reach_select.py)"`; upload `selection-<run_id>-<run_attempt>` (`retention-days: 90`,
  `if: always()`). A miss or API failure is logged and the artifact says `full: <why>`.
- `mutation-sweep`: adds `--verdicts "$RUNNER_TEMP/verdicts.jsonl"` and an upload of
  `verdicts-<run_id>-<run_attempt>-<shard>` (`if: always()`, 90 days) on every event; its `ImageVersion` is in the
  verdicts header (Task 6.1).
- [ ] **Failing case:** a `ci.yml` read in `check-plan-code.py`'s self-test asserts `mutation-sweep` does not consume
  `sweep-select`'s output in this slice (the shadow invariant, made mechanical); slice 8 flips this case. A second
  read asserts the `--select-only` step passes `--selector-blob` from `git rev-parse HEAD:scripts/reach_select.py`.
  A third (r2 C3) asserts the cache-list step's `env.GH_TOKEN` is exactly `${{ github.token }}` (Task 7.2 turns
  this into the general `GH_CALLERS` read).

**Pre-push (slice 6):** `python3 scripts/check-python-pin.py`; `python3 scripts/check-plan-code.py --self-test`;
`python3 scripts/reach_select.py --self-test`; WM pins for both (Tasks 6.1, 6.2).
**Merge gate:** the PR's own run uploads one `selection-*` (with `selector_blob`) and every shard's `verdicts-*`.

---

## Slice 7 — the comparator, the committed ledger and its guard (spec §2 *The comparator*, *The ledger*, "A MISS, precisely"; §8.6)

**Design D1, owner 2026-11-09 14:55 (selection card, answer A; spec §2 and §7, last row).** The comparator is a
STATELESS report writer; the ledger is the committed file `docs/shadow-ledger.json`, changed only by an absorb
pull request under a monotonic guard. Every input that can OPEN the switch is read at BASE; Actions storage can only
CLOSE it (architecture review §3 D1, §6, §9). Removed from the r2 design, and why: `newest_trusted` (predecessor
search), the "no trusted ledger → empty ledger" genesis rule (r3 F2: genesis is now the file's creating commit), the
writer's schema hard-failure, the `shadow-ledger` concurrency group (r3 F6: reports cannot race), the
epoch-by-string-equality rule (r3 F5), the per-candidate lookup on the writer path (r3 F7) and `q1_probe_delta` in
`selection-*` (r3 F4).

**One run predicate, `trusted_report_run(run, default_branch) -> str | None`** (None = trusted, else the reason),
in `scripts/reach_gate.py` (created in Task 7.3, so the comparator, the guard and the gate share ONE definition):
`run.event in {"schedule", "workflow_dispatch"}`, `run.path == ".github/workflows/shadow-compare.yml"`,
`run.head_branch == default_branch` (from `gh api repos/{owner}/{repo}`, never typed), and
`run.head_repository.id == run.repository.id` (a fork's branch may be NAMED `master`). It is the r2 `trusted_ledger`
renamed, and every remaining use of it is fail-closed and inherits nothing. **Listing reports** (shared helper
`list_reports(gh, skip: set[str], today) -> list[dict]`, also in `reach_gate.py`; r1 redesign Claude F4). It
lists the RUNS of one workflow, never the repository's artifacts, which after slice 6 grow by about 9 per CI run
(INFERRED: 8 `verdicts-*` + 1 `selection-*`; MEASURED 710 runs in 7 days) to tens of thousands of artifacts and
hundreds of pages per listing against `GITHUB_TOKEN`'s 1,000 requests per hour:
1. `gh api "repos/{owner}/{repo}"` → `default_branch` (never typed) and the repository `id`;
2. `gh api --paginate --slurp "repos/{owner}/{repo}/actions/workflows/shadow-compare.yml/runs?branch=<default>&created=>=<today − 120 days>&per_page=100"`
   (about 120 daily runs plus dispatches: two pages), parsed by `runs_from_listing` below. **`--slurp`, r3 F6:**
   gh's own manual (`gh api --help`, read 2026-11-10): in `--paginate` mode "Each page is a separate JSON array
   or object. Pass `--slurp` to wrap all pages of JSON arrays or objects into an outer JSON array." Without it the
   output is two concatenated objects, which `json.loads` refuses (fail closed) and a first-object parser
   (`raw_decode`) silently reads as page 1 alone, dropping the OLDEST runs, a late rerun's report among them. **No `status` parameter** (r2 redesign Codex C2): GitHub's
   `status` "Returns workflow runs with the check run status or conclusion that you specify", which is the run's
   CURRENT state, and a rerun of a run that already published a miss is `queued` or `in_progress` until it ends,
   so `status=success` dropped the run and the miss with it. **120 days, not 90** (found by the class search
   after C2, by simulation): GitHub's re-run page says a run can be re-run "up to 30 days after its initial run",
   and `created` filters on the RUN's creation, so a rerun attempt's report can be uploaded 30 days after its
   run was created and still live 90 days after that. Each run object carries `event`, `path`, `head_branch`,
   `head_repository.id`, `repository.id`, `run_attempt`, `status` and `conclusion`, so `trusted_report_run` needs
   NO per-run lookup;
3. **every ATTEMPT of every trusted run is its own report** (r2 redesign Codex C2: a rerun must never remove an
   earlier attempt's tightening evidence; GitHub's docs do NOT state whether an earlier attempt's artifacts
   survive a rerun, so the rule below fails closed either way). A report's identity is `report_id = "<run_id>.<run_attempt>"`,
   and `skip` holds the identities the ledger at BASE already absorbed (Task 7.3). For each trusted run and each
   attempt `n` in `1..run.run_attempt` whose identity is NOT in `skip`: its state is the run object's for the
   latest attempt, else `gh api "repos/{owner}/{repo}/actions/runs/<id>/attempts/<n>"` (documented: "Gets a
   specific workflow run attempt"); then `gh api "repos/{owner}/{repo}/actions/runs/<id>/artifacts?name=shadow-report-<id>-<n>"`
   (the `name` parameter is an EXACT match, r2 Codex F5, so the run id and attempt are in the name). An attempt
   that concluded `success` must have exactly one artifact with `expired == false`, whose download must pass
   `report_schema_ok` AND `report_identity_ok(rep, <run id>, <n>)` (r3 F5: the body's `run_id`/`run_attempt`
   must be the attempt it was downloaded from, so `skip`, keyed by the listing, and `report_id`, keyed by the
   body, cannot disagree and hide another run's report); an attempt still `queued`, `in_progress` or `waiting`
   contributes nothing YET (it is not absorbed, so the next listing reads it); an attempt that COMPLETED otherwise
   contributes its report if one exists (the upload is `if: success()`, but a cancel in a post step can leave one;
   a report only tightens what it adds beyond `may_loosen`), and if none exists it contributes a NO-REPORT STUB
   `{run_id, run_attempt, no_report: <conclusion>}` (r3 F4). A completed attempt can never upload an artifact
   later, so the absorb records the stub's identity (`absorbed_reports[<id>] = null`, Task 7.3) and no later
   listing re-queries it; without the stub, every failed or cancelled attempt was re-queried on every listing for
   the whole 120-day window.
A failed call, a successful attempt with no unexpired report (absent, or deleted by a rerun), or a report failing
its schema or its identity RAISES; every caller turns that into a refusal. **The cost, restated from the steps
above (r3 F4):** 1 (repository) + P (run pages, ⌈runs in the window / 100⌉, 2 at one run a day) + for each
UNABSORBED attempt: 1 artifacts call, + 1 download when a report exists, + 1 attempt-state call when it is not
its run's latest attempt. Every listed attempt, stubs included, enters `skip` at the next absorb, so the
unabsorbed set is what ran since the last absorb: at one scheduled run a day and the gate's 14-day staleness
clause (Task 8.1 clause 7; the gate fetches only when clauses 1-7 pass), about 3 + 2 × 14 = 31 calls, plus 2 per
extra dispatch or rerun attempt in those 14 days.

**Why a separate workflow file (resolves r3's Q2 note).** The job lives in a NEW workflow,
`.github/workflows/shadow-compare.yml` (`on: schedule` daily + `workflow_dispatch`), not in `ci.yml`. Adding
`workflow_dispatch` to `ci.yml`'s `on:` would make every `ci.yml` job dispatchable, the sweep and its `sweep-red`
alert included, on any branch. A separate file leaves `ci.yml`'s triggers and the alert condition unchanged.

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

### Task 7.2: `scripts/shadow-compare.py --report` and its workflow

**Files:** Create `scripts/shadow-compare.py`, `scripts/mutations/shadow-compare.json`, and its **W1-W8**:
**W1** docstring count; **W2** the manifest, one entry per guard clause below; **W3** `EXPECTED_MUTATIONS`
`"scripts/shadow-compare.py"`; **W4** the declared-counts case in `check-plan-code.py`; **W5** `POPULATION` in
`check-selftest-counts.py`; **W6** `EXAMINED_KEYS["shadow-compare.py"]` by `analyse()`; **W7** a `ci.yml` `verify`
step `python3 scripts/shadow-compare.py --self-test` (the caller); **W8** `fixture_git.isolated()` if it uses
`fixture_git` (the ancestry cases do). Create `.github/workflows/shadow-compare.yml`.

**The workflow.** Two jobs, and **no concurrency group** (two overlapping runs write two independent reports;
neither reads the other, so neither can erase the other). **No `if:` in this file reads `github.event`** (r1
redesign Claude F3). GitHub's events reference gives the `schedule` event's webhook payload as "Not applicable",
with `GITHUB_REF` "Default branch", and its `workflow_dispatch` payload table lists `inputs`, `ref` and
`workflow` but no `repository`; so the r1 expression `github.ref == format('refs/heads/{0}',
github.event.repository.default_branch)` compared against `refs/heads/` and skipped every scheduled run. The
default branch is read from the API instead, the same source `trusted_report_run` uses:
```yaml
  on-default-branch:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    outputs:
      on_default: ${{ steps.branch.outputs.on_default }}
    steps:
      # setup-python '3.12' and the Python-pin step go here too: `check-python-pin.py` requires every job
      # to pin, and its `EXEMPT_JOBS` is empty on purpose (two lines of YAML, not an exemption)
      - id: branch
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          d="$(gh api "repos/$GITHUB_REPOSITORY" --jq .default_branch)"
          test -n "$d"
          echo "default branch: $d; ref: $GITHUB_REF"
          if [ "$GITHUB_REF" = "refs/heads/$d" ]; then echo on_default=true; else echo on_default=false; fi >> "$GITHUB_OUTPUT"
```
An API failure or an empty answer FAILS the job (the default shell is `bash -e`), so it is red, never a silent
skip. The second job, `shadow-compare`: `needs: on-default-branch`, `if: needs.on-default-branch.outputs.on_default
== 'true'` (r3 F6: a dispatch on a feature branch is skipped, on cost grounds; trust does not depend on it, the
predicate does), `permissions: contents: read, actions: read`. Steps: checkout `fetch-depth: 0`; setup-node `'22'`; setup-python `'3.12'`; the Python-pin step; `npm ci`
(a replay stages `node_modules/typescript`); the read-set cache list and `actions/cache/restore` by `pick_cache`
(Task 5.3, default-branch entries only) for the Q1 delta; then ONE step, `python3 scripts/shadow-compare.py
--report --out "$RUNNER_TEMP/report.json"`; then `actions/upload-artifact` named
**`shadow-report-${{ github.run_id }}-${{ github.run_attempt }}`** (one report per attempt, r2 redesign Codex
C2), `retention-days: 90`, `if: success()`. **Every step that runs `gh`, directly or through a script, carries
`env: GH_TOKEN: ${{ github.token }}`** (r2 redesign Codex C3: GitHub's CLI page requires the variable in a
workflow step, and a job's `permissions:` exports no token to `gh`): here the cache-list step and the `--report`
step; `on-default-branch` already does.

**What `--report` does** (all `gh` calls injected in the self-test): (1) reads `docs/shadow-ledger.json` AT ITS OWN
CHECKOUT, for the ACTIVE `epoch.start`, the GENESIS start (the first epoch's: `previous_epochs[0].start`, else
`epoch.start`), the decided rows of EVERY epoch (for `settled`, below) and the archived epochs' events (for
`held_by_archive`, Task 7.3). **It reads archived epochs only to OMIT what they already hold exactly; it never
reads an earlier report or an artifact ledger** (r4 M1: the r3 text said it never read an archived epoch, while
`report()` needed one to omit held events); (2) lists PRs merged since the GENESIS start (r4 class search: under r3
it listed since the ACTIVE start, so a PR still `pending` when an owner's reset merged, merged before the new
start and decided in no epoch, was never compared again and its miss could not latch), takes `observed_at` from
GITHUB's clock, the `Date` header of its repository call (`github_time`, r7 F1; never the runner's clock), fails
CANNOT RUN (nonzero, nothing written or uploaded) when `clock_errors` finds the runner's clock more than an hour from
it, and THEN lists the CI workflow's runs ONCE into `runs_now` (r5 F1; `runs_now_from_listing` below), omits
every PR `settled` (code below) finds, lists the remaining PRs' pushes' runs WHATEVER their current status (the class of r2
redesign Codex C2), and downloads each
`selection-*`/`verdicts-*` pair it needs, for EVERY attempt of a run (both names carry `<run_attempt>`): an
attempt still running makes that push `pending`, and each completed attempt's VIEW is compared on its own, so a
rerun that compares clean cannot replace an earlier attempt's difference (`decide_pr` latches a miss from any of
them). **An attempt's VIEW (r3 F3)** is, per artifact (the `selection-*` and each shard's `verdicts-*`), that
attempt's own artifact, else the latest EARLIER attempt's: "Re-run failed jobs" re-runs only the failed shard,
so attempt 2 has `verdicts-<id>-2-3` and no `selection-<id>-2` (`sweep-select` did not re-run, so attempt 1's
selection is the one that attempt executed). Under r2 that attempt had no `selector_blob` and was `not a
sample`, so a difference in the re-run shard was never compared; the view compares it;
(3) compares, replays, decides each PR not `settled`;
(4) computes `q1_probe_delta` ITSELF with `reach_select.q1_probe_delta` (Task 6.1) over the restored read sets
(r3 F4: default-branch code, never a PR run's), or null when no usable read set was restored; (5) runs
`post_switch` (Task 8.2; an empty list until slice 8); (6) writes the report, `final_runs` included. A failed listing or download exits
nonzero and uploads nothing; a missing report is not a clean one, because the gate's staleness clause (Task 8.1)
closes the switch when reports stop being absorbed.

**The report's schema** (`report.json`): `{schema: 1, run_id, run_attempt, code_sha: $GITHUB_SHA, selector_blob:
<git rev-parse $GITHUB_SHA:scripts/reach_select.py>, comparator_blob: <… :scripts/shadow-compare.py>,
epoch_start, generated_at, q1_probe_delta: int | null, prs: {"<N>": {decision: "clean"|"miss"|"inconclusive"|
"pending"|"not a sample", merged_at, decided_at, pushes: [{head, base, run_id, run_created_at, attempts, result,
differing: [...], drift: bool}]}},
final_runs: {"<run_id>": {attempts, observed_at}},
post_switch_events: [{sweep_run_id, pr, targets}], counts: {miss, inconclusive, unreproduced, drift_events}}`.
`final_runs` (r5 F1) is `final_runs()` below: each PR CI run whose attempt count this report OBSERVED final and
which a DECIDED row compared at that count; the absorb records it, and only it freezes a push (`settled`).
A push's `run_id`, `run_created_at` and `attempts` name its PR CI run, when that run was created, and how many of
its attempts the decision compared (r4 class search: `settled` needs them); its `result` is `miss` when a
difference at that push replayed as a miss (`replay`), and its `differing` lists each differing `{target, mutant,
seed}` or `{target, control}` of that push, the items `miss_evidence` (Task 7.3) identifies.
`generated_at` is the UTC time the report is WRITTEN (step 6), stated so it is not taken for the run's start; it
orders reports for Q1's value and measures freshness, and nothing else (a report's absorption is by its identity
`report_id` = `<run_id>.<run_attempt>`, Task 7.3; r1 redesign Claude F1c, r2 redesign Codex C2). **DECIDED** means one of `clean`, `miss`, `inconclusive` or `not a sample`;
`pending` is NEVER decided, is never written to the ledger, and is re-scanned by every later report (r1 redesign
Claude F9). `DECIDED = frozenset({"clean", "miss", "inconclusive", "not a sample"})` lives in `reach_gate.py`,
and the comparator, the absorb and the guard all import it.
**A sample counts only when its push's `selection-*` records a `selector_blob` equal to the report's own** (r3 F8);
otherwise that push is `not a sample` (the PR run executed a different selector). The PR run executes the merge
commit's `reach_select.py`, so equal blobs mean the evidence was produced by the code being keyed.

**Interfaces:**
- `pushes(pr: dict, runs: list[dict]) -> list[dict]` — every push's PR run with its own BASE.
- `compare_push(pr_verdicts: list | None, base_verdicts: list | None, would_skip: set[str], select_image: str |
  None, select_blob: str | None, report_blob: str) -> tuple[str, list, bool]` — `"not a sample"` when
  `select_blob != report_blob` (None included); `"clean"`, `"difference"` (with the differing (target, mutant,
  seed)), `"inconclusive"` (missing, expired, `complete: false`, a CANNOT RUN control, a cancelled run), `"pending"`
  (either sweep not finished); the third element is DRIFT (r1 Codex F9, Claude F16; spec §2 Resolve, §4.4): any PR
  shard's verdicts-header `image` differs from the `selection-*` artifact's `image`, or either is null. Drift is
  COUNTED in the report, never a verdict change.
- `replay(diff, run_one) -> str` — 3 runs per side under EACH `RECORD_SEEDS` value through Task 7.1's option, in
  fresh trees: stable-and-different under any seed → `"miss"`; anything else → `"unreproduced difference"`.
  A push compared with an EMPTY would-skip set returns `"no would-skip"` (compared, nothing to miss; r3 F3
  names it so `decide_pr` can tell it from a push never compared).
- `decide_pr(pushes: list[list[str]]) -> str` — one inner list per push, one result per completed attempt VIEW
  (r3 F3: r2's flat list had no rule for `clean` beside `not a sample`). Code below, run against the F3 cases.
- `report(ledger_doc: dict, decided: dict, meta: dict) -> dict` — builds the schema above, omitting every PR
  `settled` finds (a `pending` PR is never settled, so never omitted), and every post-switch event that
  `held_by_archive([ledger_doc["epoch"], *ledger_doc["previous_epochs"]], event=ev)` (Task 7.3) holds EXACTLY,
  every one of its (PR, target) items, in the active or an archived epoch at the checkout (r3 F1 class: a red
  master that stays red after the owner's reset re-blames the same PR for the same target on every sweep; the
  absorb drops it either way, and omitting it here keeps gate clause 9 from refusing on it every day until the
  absorb). An event with any item no epoch holds, a new target for an archived PR among them, is reported whole.
  A PR merged before the ACTIVE `epoch.start` (a PR pending at a reset) is reported like any other; it can only
  latch, because gate clause 5 counts no row merged before the active start (Task 8.1).
- `settled(pr, ledger_doc, runs_now) -> bool` — **the omission rule, by IDENTITY, never by PR number alone**
  (r4 class search: under r3 any DECIDED row for the PR omitted it, so a re-run attempt of one of its push runs,
  made after the decision, was never compared, and a miss in it could not latch, though `decide_pr` latches a
  miss from ANY attempt). Settled means: some epoch (active or archived) holds a DECIDED row for the PR whose
  `pushes` is NON-EMPTY (r5 F2: `all` over `[]` is True, the vacuous class the r4 fold fixed in
  `held_by_archive`), and every push of it is FROZEN or still has exactly the `attempts` the row compared.
  **Frozen is an OBSERVATION, never an age (r5 F1).** A push is frozen only when some epoch's `final_runs`
  records its run: a report OBSERVED that run `completed`, with no attempt in progress, at the attempt count a
  decided row compared, at an `observed_at` later than `run_created_at` + `RERUN_DAYS` + `SKEW_DAYS` (GitHub's
  re-run page: a run can be re-run "up to 30 days after its initial run", already cited for the 120-day window),
  and the absorb recorded it (Task 7.3). **`observed_at` is GitHub's clock (r7 F1):** the `Date` header of the
  report's repository call, made before the runs listing (`github_time`), so it and `run_created_at` come from one
  clock. Under r5 and r6 it was the report runner's clock: under r5 a runner two seconds fast recorded run 55 final
  at GitHub's 09:59:59 on day 30 (Codex's executed reproduction), and under r6 a runner two days fast still froze it
  on GitHub's day 29, after which a legal re-run's miss was never compared (the r7 reviewer's construction A). The
  report fails CANNOT RUN when the runner's clock and that header differ by more than an hour (`clock_errors`); that
  is an ALARM for a broken runner, not the defence, because no time the report records is the runner's.
  **`SKEW_DAYS` = 1 stays (r6 B1):** a record therefore proves GitHub's own clock was more than a day past the
  re-run deadline. **A recorded run is out of the listing's reach:** the listing returns about 10 days (backlog
  #595) and a record needs more than 31, so `runs_now` never lists a frozen run, and its safety is the server-clock
  comparison against GitHub's documented 30-day re-run limit, not a later listing. The clause that UNFREEZES a push
  whose run `runs_now` lists at an attempt count other than the recorded one is kept (fail-closed), but it reaches
  only a run that a re-decision of the same PR adds to `runs_now`; it is not the defence, and the r6 claim that it
  overrules a premature observation "from any cause" was wrong (r7 F1). `settled` reads, per run, the NEWEST
  recorded observation across every epoch by GitHub's time (r7 F3), and the absorb keeps the first observation only
  while a later one AGREES with it: a later observation at another count replaces it (Task 7.3). The row's own `attempts` may be LOWER than the recorded count: a run that gained an
  attempt is re-decided, and a non-miss re-decision leaves the old row in place, but that later decision compared
  every attempt (a miss latched or was held exactly by an archive), so nothing it saw is lost. `settled` re-checks the time against the push's own `run_created_at`, with the margin, so a record
  that does not prove the deadline had passed freezes nothing. Under r4 a run older than 30 days was frozen by
  its AGE, though no report had seen its final count: a re-run made on day 30 after that day's report, or an
  attempt still running at the last report before day 31, was never compared, and its miss was dropped (the
  r5 reviewer ran both). Until a push is frozen it is compared against its run's CURRENT attempt count in
  `runs_now`; a run absent from `runs_now`, a push with any run field missing OR null (r5 F4: the r4 code
  checked the keys and raised on a null), and a run that gained an attempt are not settled: the PR is
  re-decided over every attempt view, and the absorb keeps the old row unless the new decision is a `miss` (a
  decided row is replaced only by a miss, Task 7.3), so a re-decision can only tighten. **`final_runs` lives in
  the EPOCH, keyed by run id, and not on the push row** (the coordinator's text said the row; this is a
  deviation, and why): an absorb may not touch an archived epoch (it must stay verbatim, Task 7.3), and a reset
  usually follows a FRESH miss, so a miss row archived before its run's day 31 could never be marked; its
  re-decision is HELD BY ARCHIVE and writes nothing, so it would be re-decided, at about 100 calls, every day for
  ever. An observation in the active epoch's map freezes the archived row's push as well.
- `runs_now_from_listing(stdout) -> dict` — ONE paginated listing, `gh api --paginate --slurp
  "repos/{owner}/{repo}/actions/workflows/ci.yml/runs?created=>=<observed_at − LISTING_DAYS>&per_page=100"`, with
  no `status` or `event` parameter (a filter can only drop a run, which then cannot settle: liveness, never a
  loosening), parsed by `runs_from_listing` into run id → `{attempts: run_attempt, status, created_at}`. NEVER a
  call per run (r5 F1). `LISTING_DAYS` is `RERUN_DAYS` + `SKEW_DAYS` + 15: a decided run whose final count is not
  yet recorded stays in the listing for 15 days after it can first be observed final, so up to 14 consecutive
  failed reports (the gate's staleness clause, Task 8.1 clause 7, has closed the switch by then) still leave a
  report that observes it, **for a run the listing returns: GitHub caps it (r6 M1, below).**
  For a PR the report re-decides, the runs it lists for that PR's pushes are added to `runs_now` with the same
  three fields, so a run older than the listing is observed by its own re-decision. A failed listing RAISES.
- `github_time(include_stdout) -> tuple[str, dict]` — (r7 F1) `observed_at` from the `Date` header of `gh api
  --include "repos/{owner}/{repo}"` (the repository call the report already makes, so no call is added), and the
  body; no single parseable, zoned `Date` header → `CannotRun`. **Why the repository call and not the listing's
  response** (the coordinator's text named the listing): it is made BEFORE the listing, which keeps
  `observe_final`'s ordering (the listing's state is at least as recent as `observed_at`), and `--include` would
  put header text in front of `--slurp`'s one JSON array. Both are GitHub's clock, the property F1 asks for.
- `clock_errors(runner_now, observed_at) -> list[str]` — (r7 F1) one `CANNOT RUN` line when the runner's clock and
  GitHub's `Date` differ by more than `CLOCK_ALARM` (1 hour); the report then exits nonzero and writes nothing.
- `observe_final(run, observed_at) -> bool` — the run is `completed` and `observed_at` is LATER than its
  `created_at` + `RERUN_DAYS` + `SKEW_DAYS` (r6 B1: exactly +31 days is not final). `observed_at` is GitHub's
  `Date` from the repository call made BEFORE the first listing call (r7 F1), so the state each listing
  returns is at least as recent as `observed_at`: a re-run started before the deadline shows as a higher
  `run_attempt` or a status other than `completed`. A missing or null field → False, never a raise.
- `final_runs(ledger_doc, decided, runs_now, observed_at) -> dict` — the report's `final_runs`: for each DECIDED
  row (the ledger's, in any epoch, and this report's own `decided`), each push whose run is in `runs_now` at
  exactly the push's `attempts` and `observe_final` → `{"<run_id>": {attempts, observed_at}}`. A `pending` row
  contributes nothing, so a run still running is never recorded final.
- **The report's call bound, from the code above (r5 F1; `GITHUB_TOKEN` allows 1,000 requests an hour).** Every
  report pays 1 (the repository) + ⌈N / 100⌉ (the PR listing, N = PRs merged since GENESIS) + ⌈R / 100⌉ (the CI
  runs listing, R = CI runs created in the last `LISTING_DAYS`). A frozen or equal-count PR costs nothing beyond
  its line on a PR listing page, so the frozen rows bound the scan without a window on N. MEASURED inputs: R
  from the 710 CI runs in 7 days above, about 101 a day, so 46 days give about 4,660 runs; N from
  `git log origin/master --first-parent` (493 squash-merged PRs from 2026-07-13 to 2026-11-10, about 4.1 a day),
  so 6 pages at 120 days and about 16 after a year. **The runs listing is CAPPED (r6 M1; Codex's review cites
  GitHub's REST page, not re-checked by this fold): a filtered workflow-run listing returns at most 1,000 runs**,
  10 pages, newest first, so it reaches back about 10 days, not 46, and the r5 sentence "about 1 + 16 + 46 = 63
  calls a day after a year, about 937 left for deciding PRs" is WRONG as stated. Past the cap a decided run is
  ABSENT from `runs_now`, and an absent run is never settled, so its PR is re-decided (about 100 calls) on every
  report until its own re-decision observes it final after day 31. That FAILS CLOSED (a missing run is compared
  again, never dropped), but the steady state is NOT reached: INFERRED from the figures above, not measured, about
  4.1 PRs a day each re-decided on about 21 reports (days 10 to 31) is about 86 re-decisions a report, far past
  the hour, so the report fails, uploads nothing, and the gate's staleness clause keeps the switch closed. Filed
  as backlog #595, beside #594; this plan does not redesign the listing. Under r4 the same work was one `runs/<id>` call per push
  of every PR decided in the last 30 days. Re-decisions this rule causes, beyond deciding new PRs: (a) a decided
  PR whose run gained an attempt is re-decided, at about 100 calls (the coordinator's measure: every attempt's
  artifacts), on each report until its new count is observed final, at most 31 days; how often a MERGED PR's run
  is re-run is NOT measured, and each one costs about 100 calls a day while it lasts; (b) a decided run whose
  final count no report observed inside `LISTING_DAYS` (15 or more consecutive failed reports) is re-decided
  once, by the first report after it, and that re-decision records it (with the cap, (b) is every decided run
  older than the listing reaches: backlog #595). **The rest of the report is not bounded
  by this fold:** deciding each NEWLY merged PR costs about 100 calls, so the 937 left cover about 9 PRs a
  report. `git log` shows 21 PRs merged on 2026-09-07, and an outage leaves its whole backlog undecided; a
  report that exceeds the hour fails, uploads nothing, and the next one faces the same set. That predates this
  fold and is filed as backlog #594.
```python
import json
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

DECIDED = frozenset({"clean", "miss", "inconclusive", "not a sample"})  # built: `from reach_gate import DECIDED`

def runs_from_listing(stdout):
    """`gh api --paginate --slurp` prints ONE JSON array holding every page (gh's manual: without `--slurp`
    "each page is a separate JSON array or object", concatenated, which `json.loads` refuses; r3 F6)."""
    pages = json.loads(stdout)
    if not isinstance(pages, list):
        raise ValueError("runs listing is not a --slurp array of pages")
    return [run for page in pages for run in page["workflow_runs"]]

def report_identity_ok(rep, run_id, attempt):
    """r3 F5: the body's identity must be the run attempt it was downloaded from, or `skip` (keyed by the
    listing) and `report_id` (keyed by the body) could disagree and hide another run's report."""
    return rep.get("run_id") == run_id and rep.get("run_attempt") == attempt

def decide_pr(pushes):
    """`pushes`: one list per push, one result per completed ATTEMPT VIEW of that push's PR run (r3 F3).
    `no would-skip` = compared, nothing skipped (neutral); `not a sample` = not compared under this selector."""
    flat = [r for push in pushes for r in push]
    if "miss" in flat:
        return "miss"                                  # latches, from any attempt of any push
    if "pending" in flat:
        return "pending"
    per_push = [[r for r in push if r != "not a sample"] for push in pushes]
    if all(not p for p in per_push):
        return "not a sample"                          # no push compared under this selector
    if any(not p for p in per_push):
        return "inconclusive"                          # one push was never compared under this selector
    rest = [r for p in per_push for r in p]
    if any(r != "clean" and r != "no would-skip" for r in rest):
        return "inconclusive"                          # inconclusive, unreproduced difference
    return "clean" if "clean" in rest else "not a sample"

RERUN_DAYS = 30    # GitHub's re-run page: a run can be re-run "up to 30 days after its initial run"
SKEW_DAYS = 1      # r6 B1, kept by r7: both times are GitHub's now (r7 F1); the margin outlasts any re-run request
FINAL_AFTER = timedelta(days=RERUN_DAYS + SKEW_DAYS)
LISTING_DAYS = RERUN_DAYS + SKEW_DAYS + 15  # 14 failed reports (gate clause 7 closes the switch) still leave one
RUN_FIELDS = ("run_id", "run_created_at", "attempts")
CLOCK_ALARM = timedelta(hours=1)  # r7 F1: the runner's clock this far from GitHub's -> CANNOT RUN (an alarm only)

class CannotRun(Exception):
    """The report cannot run: it exits nonzero, writes nothing and uploads nothing."""

def as_utc(s):  # built: `from reach_gate import as_utc` (Task 7.3's block)
    if len(s) == 10:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def github_time(include_stdout):
    """r7 F1: `observed_at` is GITHUB's clock, never the runner's: the `Date` header of the report's repository call,
    `gh api --include "repos/{owner}/{repo}"`, a call the report already makes (the call bound's 1), made BEFORE the
    runs listing. `--include` prints the status line, the headers, a blank line, then the body. Returns
    (observed_at, body). No single parseable, zoned `Date` header -> CannotRun."""
    head, sep, body = include_stdout.replace("\r\n", "\n").partition("\n\n")
    dates = [line.split(":", 1)[1].strip() for line in head.split("\n")[1:]
             if ":" in line and line.split(":", 1)[0].strip().lower() == "date"]
    if not sep or len(dates) != 1:
        raise CannotRun(f"repository call: {len(dates)} Date headers, want 1")
    try:
        t = parsedate_to_datetime(dates[0])
    except (TypeError, ValueError) as e:
        raise CannotRun(f"repository call: unparseable Date header {dates[0]!r}") from e
    if t is None or t.tzinfo is None:
        raise CannotRun(f"repository call: Date header {dates[0]!r} has no zone")
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), json.loads(body)

def clock_errors(runner_now, observed_at):
    """r7 F1: the runner's clock more than CLOCK_ALARM from GitHub's `Date` -> the report is CANNOT RUN. An ALARM for
    a broken runner, NOT the defence: no time the report records is the runner's."""
    gap = abs(runner_now - as_utc(observed_at))
    if gap > CLOCK_ALARM:
        return [f"CANNOT RUN: runner clock {runner_now:%Y-%m-%dT%H:%M:%SZ} is {gap} from GitHub's {observed_at}"]
    return []

def runs_now_from_listing(stdout):
    """r5 F1: ONE paginated listing of the CI workflow's runs, never a call per run."""
    return {r["id"]: {"attempts": r.get("run_attempt"), "status": r.get("status"), "created_at": r.get("created_at")}
            for r in runs_from_listing(stdout)}

def observe_final(run, observed_at):
    """r5 F1: the run's attempt count is FINAL only when OBSERVED completed after its re-run deadline plus the
    margin (r6 B1). `observed_at` is GitHub's `Date` from the call BEFORE the listing (r7 F1), so both times are
    GitHub's and the listing's state is at least that recent."""
    if run is None or any(run.get(k) is None for k in ("attempts", "status", "created_at")):
        return False
    return run["status"] == "completed" and as_utc(observed_at) > as_utc(run["created_at"]) + FINAL_AFTER

def _epochs(ledger_doc):
    return [ledger_doc["epoch"], *ledger_doc["previous_epochs"]]

def final_runs(ledger_doc, decided, runs_now, observed_at):
    """The report's `final_runs`: each run a DECIDED row compared at the count OBSERVED final."""
    rows = [r for ep in _epochs(ledger_doc) for r in ep["rows"].values()] + list(decided.values())
    out = {}
    for row in rows:
        if row.get("decision") not in DECIDED:
            continue                                   # a pending row: its run may still be running
        for p in row.get("pushes") or []:
            if any(p.get(k) is None for k in RUN_FIELDS):
                continue
            run = runs_now.get(p["run_id"])
            if run is not None and run["attempts"] == p["attempts"] and observe_final(run, observed_at):
                out[str(p["run_id"])] = {"attempts": p["attempts"], "observed_at": observed_at}
    return out

def newest_finals(ledger_doc):
    """r6 B1: per run, the NEWEST recorded observation in any epoch (r5's `update` let an archive's older one win).
    r7 F3: newest by GitHub's time, since every `observed_at` is a `Date` header (r7 F1)."""
    finals = {}
    for ep in _epochs(ledger_doc):
        for run_id, fin in ep.get("final_runs", {}).items():
            if fin.get("attempts") is None or fin.get("observed_at") is None:
                continue
            old = finals.get(run_id)
            if old is None or as_utc(fin["observed_at"]) > as_utc(old["observed_at"]):
                finals[run_id] = fin
    return finals

def settled(pr, ledger_doc, runs_now):
    """r4 class search: a PR the report may OMIT, by the identity of what was decided, never by PR number alone.
    r5 F1: a push is frozen by a recorded OBSERVATION (`final_runs`), never by its age.
    r6 B1: an observation counts only past the margin. r7 F1: a recorded run is ABSENT from the capped listing, so
    the record alone freezes it, safe because its `observed_at` is GitHub's time; the unfreeze clause is kept,
    fail-closed, and reaches only a run a re-decision of this PR adds to `runs_now`."""
    finals = newest_finals(ledger_doc)
    for ep in _epochs(ledger_doc):
        row = ep["rows"].get(pr)
        if row is None or row["decision"] not in DECIDED:
            continue
        def frozen_or_equal(p):
            if any(p.get(k) is None for k in RUN_FIELDS):
                return False                           # r5 F4: a missing OR null run field: re-decide, never raise
            fin = finals.get(str(p["run_id"]))
            now = runs_now.get(p["run_id"])
            if (fin is not None and as_utc(fin["observed_at"]) > as_utc(p["run_created_at"]) + FINAL_AFTER
                    and (now is None or now["attempts"] == fin["attempts"])):
                return True                            # r5 F1: frozen, OBSERVED final (GitHub's clock, r7 F1)
            return now is not None and now["attempts"] == p["attempts"]
        if row["pushes"] and all(frozen_or_equal(p) for p in row["pushes"]):   # r5 F2: [] is never settled
            return True
    return False
```
`not a sample` ATTEMPTS of a push that has another compared attempt are ignored (the ledger's clause 5 ignores
`not a sample` ROWS the same way); a PUSH with no compared attempt among compared pushes makes the PR
`inconclusive`, never `clean`, because spec §8.6 item 6 counts a PR only when every push compared. Neither rule
loosens: a `miss` latches before either is read.
- [ ] **Failing cases (§8.6, each adjacent):** a cancelled PR run, a missing base artifact, a red control →
  inconclusive; a pending PR not counted and decided by a later run; a miss at a non-final push then a clean final
  push → miss; a flip on re-run → inconclusive; stable on both trees under one seed → miss; reproduces under only
  one of the two seeds → miss; reproduces under neither → unreproduced, listed, never clean; a PR with no would-skip
  target → not a sample; an expired input with no decided row → inconclusive; **a PR decided in the committed
  ledger is absent from the report, even when its inputs have expired** (adjacent: an undecided PR whose inputs
  expired → inconclusive); **(F9)** a PR decided `inconclusive` in the active epoch is absent from the report
  (inconclusive is decided), adjacent: a PR the ledger cannot hold as `pending` (no row) is re-decided;
  **(r4 class search, `settled`; each FAILS on the r3 rule "omit any PR the active epoch decided")** #620 decided
  `clean` with its push run 55 compared at `attempts: 1`, created 10 days ago, and run 55 now at `run_attempt: 2`
  whose attempt-2 view differs and replays stable → #620 is re-decided and reported `miss` (r3 omitted it), and
  the absorb replaces the `clean` row with the `miss`; adjacent: run 55 still at attempt 1 → omitted, and NO
  artifact call is made for #620; a row whose pushes lack `attempts` → re-decided; a failed CI runs listing →
  nonzero, no report; NO `runs/<id>` call is made for any push (one listing, `--paginate --slurp`, whose URL
  holds `created=>=` `observed_at` − 46 days and no `status=` or `event=`); **(r6 M1, the cap; liveness, not a
  loosening)** a listing of 10 full pages (1,000 runs, `total_count` 4,560) that omits run 55 → #620 NOT settled
  and `final_runs` holds no 55 (re-compared, never dropped);
  **(r5 F1, frozen on an OBSERVATION, never an age; each FAILS on the r4 age rule)** #620 `clean`, push run 55
  `run_created_at 2027-01-01T10:00:00Z`, `attempts: 1`, no `final_runs` entry: (the re-run at day 30) the
  report at 2027-02-01T07:00Z sees run 55 at attempt 2 `completed` → NOT settled, re-decided, attempt 2's stable
  difference → `miss`, absorbed over the `clean` (r4 froze it by age); (an attempt still running) at
  2027-01-31T07:00Z run 55 at attempt 2 `in_progress` → not settled, `pending`, `final_runs` holds no 55; at
  2027-02-01 attempt 2 `completed` → not settled, compared, `miss` (r4 froze it on 02-01); (never observed) on
  2027-02-01 run 55 absent from `runs_now` → not settled (r4: settled by age); (the observation itself)
  `observe_final` is False at `observed_at` exactly 2027-02-01T10:00:00Z (+31 days, `RERUN_DAYS` + `SKEW_DAYS`:
  not LATER than the margin) and True one second later, False for `in_progress`; `final_runs` holds no 55 when,
  one second after the margin, run 55 is `completed` at attempt 2 and the only decided row compared 1 (a count no
  decision compared is never recorded); a `final_runs` record whose `observed_at` is not later than
  `run_created_at` + 31 days → freezes nothing;
  **(r7 F1, GitHub's clock; each FAILS on the r6 code, which took `observed_at` from the runner)** (the reviewer's
  construction A, a runner 2 days fast) run 55 created 2027-01-01T10:00:00Z, #620 `clean` at attempt 1, no record;
  the repository call's `Date` is `Sat, 30 Jan 2027 10:00:00 GMT` (GitHub's day 29) and the runner reads
  2027-02-01T10:00:01Z → `clock_errors` gives one `CANNOT RUN` line (nonzero, nothing written), and, with that alarm
  set aside, `github_time` gives `observed_at` 2027-01-30T10:00:00Z, so `final_runs` over run 55 `completed` at
  attempt 1 is EMPTY (r6 recorded `{"55": {attempts 1, observed_at 2027-02-01T10:00:01Z}}`); the owner re-runs 55 on
  GitHub's day 29.5, attempt 2 replays a stable difference, and on every later report the CAPPED listing omits 55 →
  #620 is NOT settled (r6: settled for ever), its re-decision lists run 55 at attempt 2, `decide_pr([["clean",
  "miss"]])` → `miss`, and the absorb latches it over the `clean`; (the divergence) a runner 1 h 0 min 1 s from the
  header → `CANNOT RUN`; exactly 1 h → no error (the boundary); (adjacent pass) a runner 59 min fast and a `Date` of
  `Tue, 02 Feb 2027 07:00:00 GMT` (past +31 days), run 55 `completed` at attempt 1 → no clock error, `final_runs`
  holds `{"55": {attempts 1, observed_at "2027-02-02T07:00:00Z"}}` (the HEADER's time, not the runner's), the absorb
  records it, and the capped listing omitting 55 → settled (frozen); (the header) no `Date` header, two of them, an
  unparseable one, a body with no blank line before it → `CannotRun`; `date:` in lower case and CRLF line ends →
  parsed;
  **(r6 B1, the clock margin; rewritten by r7 F2 against a listing that honours the cap: a final run is ABSENT)**
  (Codex's reproduction, a runner 2 s fast) the `Date` is 2027-01-31T09:59:59Z and the runner reads 10:00:01 →
  `observed_at` is the header's 09:59:59 and `final_runs` over run 55 `completed` at attempt 1 is EMPTY (r5
  recorded `{"55": {attempts 1, …}}`); attempt 2 is then requested before GitHub's deadline and completes with a
  stable difference → with the capped listing (run 55, 30 days old, ABSENT) #620 has no record and is NOT settled,
  its re-decision compares attempt 2, `decide_pr([["clean", "miss"]])` → `miss`, and the absorb replaces the
  `clean` row with the `miss`; **(the absent-run path, the production shape)** the active epoch records `{"55":
  {attempts 1, observed_at 2027-02-02T07:00:00Z}}` (a header time past +31 days) and the capped listing omits 55 →
  SETTLED, frozen by the record alone, NO artifact call; the same record and #620's `clean` row ARCHIVED under an
  empty new epoch → settled; a record at exactly +31 days with 55 absent → NOT settled; (the kept unfreeze clause,
  a direct unit case: production reaches it only when a re-decision of #620 adds run 55 to `runs_now`) that record
  and `runs_now {55: attempt 2}` → NOT settled, and a later report's `{"55": {attempts 2, observed_at
  2027-02-03T07:00:00Z}}` REPLACES the record in the absorb (r5 kept the first; the guard refuses a HEAD keeping it);
  **(r7 F3, newest by GitHub's time)** the active epoch's `{"55": {attempts 1, observed_at 2027-02-02T07:00:00Z}}`
  and an archived `{"55": {attempts 2, observed_at 2027-02-05T07:00:00Z}}`, both header times → `newest_finals`
  reads the archived one; in the absorb, over the record at 1 observed 2027-02-02T07:00:00Z, a report at attempts 2
  whose header time is EARLIER (2027-02-01T07:00:00Z) leaves the record, and one whose header time is LATER
  (2027-02-03T07:00:00Z) replaces it;
  **adjacent passes:** on 2027-02-02T07:00Z run 55 at attempt 1 `completed` → settled by its equal count, NO
  artifact call, and the report's `final_runs` holds `{"55": {attempts: 1, observed_at: "2027-02-02T07:00:00Z"}}`;
  after the absorb records it, with `runs_now` EMPTY (the capped listing, r7 F2) → settled (frozen), and the next
  day's report repeating the entry leaves the ledger
  byte-identical (no churn: the row is not touched and the first `observed_at` stays);
  the same record frozen for a row in an ARCHIVED epoch (the record is in the active one); a run re-run to
  attempt 2 and re-decided `clean` (the old `clean` row stays at `attempts: 1`) → `final_runs` records 55 at 2
  from the report's own row, and the row is then frozen (without it, it was re-decided every day for ever);
  **(r5 F2)** a decided row with `pushes: []` → NOT settled for each of `not a sample`, `inconclusive`, `clean`
  (r4: settled); adjacent: one frozen push → settled; **(r5 F4)** a push with `run_created_at: null`, with
  `attempts: null`, with `run_id: null` → not settled and NO exception (r4 raised `AttributeError`), and
  `observe_final` over a run with a null field → False; **(a PR pending at a reset)** #630 merged d10, `pending` in the last report the old epoch absorbed,
  decided in NO epoch; the owner's reset starts the new epoch at d12 → the next report lists #630 (merged since
  GENESIS) and, its comparison now complete with a stable difference, reports it `miss`, which the absorb latches
  in the new epoch (no archive holds it); under r3 the listing started at d12 and #630 was never compared again;
  adjacent: #630 decided `clean` in the archived epoch → omitted (`settled` reads every epoch), and the same #630
  re-decided `clean` in the new epoch is NOT counted by gate clause 5 (merged before the active start, Task 8.1);
  **(r4 M1)** `report()` reads `previous_epochs` at the checkout to omit an event the archive holds exactly
  (#600, `[scripts/x.py]`, sweep 91) and REPORTS #600 `[scripts/x.py, scripts/y.py]` whole; **(r3 F8)** a push whose `selection-*` `selector_blob` differs from the report's →
  `not a sample`, a missing `selector_blob` → `not a sample`, equal → compared; **(r3 F4)** `q1_probe_delta` is
  computed in-job: a merged PR's `selection-*` carrying a stale `q1_probe_delta: 2` (a pre-slice-6 shape) is
  ignored and the report holds the in-job value 6; no restored read set → `null`; the report reads NO earlier
  report (the fake `gh` serves a `shadow-report-*` with a decided row and the run never downloads it); a failed
  artifact listing → nonzero, no report; `epoch_start` is copied from the ledger at the checkout, never a script
  constant; `code_sha`, `selector_blob` and `comparator_blob` are the values at `GITHUB_SHA` (two fixture commits
  with different `reach_select.py` give different blobs); **(drift)** a shard image ≠ the selection image →
  `drift: true`, `drift_events` 1, the result unchanged; equal images → `drift: false`; a null image → drift; a
  `shadow-compare.yml` read asserts `shadow-compare`'s `needs:` is `on-default-branch` and its `if:` is exactly
  `needs.on-default-branch.outputs.on_default == 'true'`, its permissions are exactly `contents: read`, `actions:
  read`, it has NO `concurrency` key, and the artifact name is exactly
  `shadow-report-${{ github.run_id }}-${{ github.run_attempt }}`; **(r2 C3, every `gh` caller is authenticated)**
  a read of `shadow-compare.yml` AND `ci.yml` asserts that every step whose `run:` contains `gh ` or invokes a
  script in `GH_CALLERS` (`scripts/shadow-compare.py`, `scripts/check-shadow-ledger.py`, and from slice 8 the
  `--select-only` step that runs `switch_gate`) has `env.GH_TOKEN` exactly `${{ github.token }}` (it fails on
  the r1 guard step, which had none; adjacent: a step with it passes, and a step that runs neither passes
  without it); **(F3, the scheduled run)**
  the same read REFUSES any `if:` in the file that contains `github.event.` (it fails on the r1 expression
  `github.ref == format('refs/heads/{0}', github.event.repository.default_branch)`, the one that skipped every
  `schedule` run), and the `on-default-branch` step, run under `bash -e` against a fake `gh` (stdout `master`),
  writes `on_default=true` for `GITHUB_REF=refs/heads/master` (the scheduled run's ref) and `on_default=false` for
  `refs/heads/feature`, and exits nonzero, writing nothing, when the fake `gh` fails or prints an empty line;
  **(F4)** `list_reports` over a fake `gh` serving 150 trusted runs of which 140 are in `skip` makes exactly
  1 + 2 + 2 × 10 calls (repository, two run pages, artifact list and download per unabsorbed attempt) and NEVER
  calls `repos/{owner}/{repo}/actions/artifacts` (the repository-wide listing), adjacent: a successful attempt
  with no `shadow-report-<id>-<n>` → RAISES; a run with `event: pull_request` in the listing is not trusted and
  costs no call; an `expired: true` report RAISES (never silently dropped); **(r2 C2, a rerun in progress)** run
  9 with `run_attempt: 2`, `status: in_progress`, whose attempt 1 concluded `success` with a report holding #650
  `miss` → `list_reports` returns attempt 1's report (identity `9.1`) and the gate's clause 9 refuses
  `unabsorbed miss` (under r1 the `status=success` query never returned run 9, and the gate opened); the listing
  URL holds no `status=` parameter and `created=>=` today − 120 days; adjacent: attempt 2 completes `success`
  with a report saying #650 `clean` → BOTH `9.1` and `9.2` are listed and the absorb keeps `miss`; attempt 1
  concluded `success` but its artifact is gone (a rerun deleted it) → RAISES, never skipped; attempt 1 concluded
  `failure` with no artifact → contributes nothing, no raise; an attempt `9.1` in `skip` costs no call while
  `9.2` is read; **(the 120-day window)** a run created 100 days ago whose attempt 2 (uploaded 70 days ago, a
  rerun 30 days after its run) holds a miss → listed (a 90-day `created` window drops it); **(comparator, the
  same class)** a PR push whose CI run has attempt 1 with a difference that replays as a miss and attempt 2
  comparing clean → the PR is `miss`; an attempt still running → `pending`;
  **(r3 F3, "Re-run failed jobs")** run 70's attempt 1 has `selection-70-1` and shards 1-8, shard 3
  `complete: false`; attempt 2 has ONLY `verdicts-70-2-3` → attempt 2's view is `selection-70-1` + shards
  1, 2, 4-8 of attempt 1 + shard 3 of attempt 2; with that shard differing and the replay stable → the PR is
  `miss` (under r2 attempt 2 had no `selector_blob`, was `not a sample`, and the difference was never compared);
  adjacent: the re-run shard agrees → attempt 2 `clean`, attempt 1 `inconclusive`, PR `inconclusive` (spec §8.6
  item 6: a flaky re-run is inconclusive); `decide_pr([["clean", "not a sample"]])` → `clean`;
  `decide_pr([["clean"], ["not a sample"]])` → `inconclusive` (r2: undefined); every push `not a sample` →
  `not a sample`; `[["clean"], ["no would-skip"]]` → `clean`, `[["no would-skip"]]` → `not a sample`;
  `[["not a sample", "miss"]]` → `miss`;
  **(r3 F4, no-report attempts)** run 41's attempt 1 concluded `failure` with no artifact → `list_reports` returns
  the stub `41.1` (`no_report: failure`) after ONE artifacts call and no download; with `41.1` in `skip` it
  costs ZERO calls (under r2 it cost a call on every listing for 120 days); a `cancelled` attempt WITH a
  `shadow-report-41-1` holding a miss → the report is returned, not a stub (adjacent); an attempt `in_progress`
  → nothing, no stub; a `success` attempt with no artifact → still RAISES, never a stub. The call count of the
  F4 case above becomes 1 + 2 + 10 × (1 + 1), plus 1 for each of two failed attempts added to its window, and
  the case asserts that exact number;
  **(r3 F5, a body naming another run)** the artifact `shadow-report-5-1` downloaded from run 5 attempt 1 whose
  body says `run_id: 6` → RAISES (`report identity 6.1 is not 5.1`); with `run_attempt: 2` → RAISES; under r2 it
  was absorbed as `6.1`, and run 6's real report, holding #650 `miss`, was filtered out by `skip` from then on;
  adjacent: a body saying `5`, `1` → returned;
  **(r3 F6, the real page shape)** the fake `gh` serves 150 trusted runs as TWO pages: invoked without
  `--slurp` it prints gh's documented default, `{page 1}{page 2}` concatenated, and with `--slurp` the array
  `[{page 1}, {page 2}]` → `list_reports` sees all 150 (the case asserts run 149, on page 2, is read), and its
  call log shows `--paginate --slurp`; a parser reading the first object only (`raw_decode`) sees 100 and goes
  red on run 149; dropping `--slurp` from the command makes the fake's output unparseable and the listing
  RAISES (`json.loads` refuses `}{`).
- [ ] **Steps:** red, implement with `gh` injected, green, W1-W8, mutate `--only scripts/shadow-compare.py`, commit.

### Task 7.3: the committed ledger, the absorb, the guard and the epoch HOLD

**Files:** Create `docs/shadow-ledger.json`; create `scripts/reach_gate.py` (`trusted_report_run`, `list_reports`,
`ledger_schema_ok`, `report_schema_ok`; Task 8.1 adds the gate) with `scripts/mutations/reach_gate.json`; create
`scripts/check-shadow-ledger.py` with `scripts/mutations/check-shadow-ledger.json`; modify
`scripts/shadow-compare.py` (`--absorb`; its manifest and WM pins), `scripts/check-merge-ready.py` (WM pins),
`.github/workflows/ci.yml` (`verify`: two `--self-test` steps and the guard step; the job gains the whole block `permissions: {contents: read, actions: read}`, F7).
**W1-W8 for `scripts/reach_gate.py` AND for `scripts/check-shadow-ledger.py`, each in full:** **W1** the docstring
count from the suite's own pass line; **W2** the manifest, one entry per guard clause; **W3** its
`EXPECTED_MUTATIONS` entry; **W4** the declared-counts case in `check-plan-code.py`; **W5** `POPULATION`;
**W6** `EXAMINED_KEYS` by `analyse()`; **W7** a `ci.yml` `verify` step `python3 scripts/<name>.py --self-test`;
**W8** `fixture_git.isolated()` (the guard's ancestry cases build a fixture repository). ⚠ Unlike the other new
scripts, `check-shadow-ledger.py` DOES match `GUARD_PATH_RE` (`scripts/check-[\w.-]+\.py`), so
`scripts/check-ratchet-contract.py` judges it: a `--self-test`, no fail-open handler, and a caller. Run it and cite
it for this file.

- **The file, created by this slice's PR** (r1 redesign Codex X3: everything the gate reads lives INSIDE the epoch,
  so archiving an epoch archives its decisions and events with it): `{schema: 1, epoch: {start: <the date slice 6
  merged>, selector_blob: <git rev-parse HEAD:scripts/reach_select.py at this commit>, reset_by_owner: null,
  absorbed_reports: {}, absorbed_through: null, rows: {}, post_switch_events: [], q1_probe_delta: null,
  final_runs: {}}, previous_epochs: []}`. `final_runs` maps a PR CI run id to `{attempts, observed_at}`, the
  OBSERVATION that froze its pushes (r5 F1, Task 7.2 `settled`), timed by GitHub's `Date` header (r7 F1); it
  LOOSENS (a frozen push is not compared again), so it is taken only from a report that `may_loosen`, and a new epoch starts it empty.
  A later observation of the same run at the same count leaves the first; one at ANOTHER count, observed later by
  GitHub's time, replaces it (r6 B1, r7 F3). A row is `{decision, merged_at, decided_at, pushes, selector_blob}`, the last copied from
  the report that wrote it (r1 redesign Claude F5); `absorbed_reports` maps each absorbed report's `report_id`
  (`<run_id>.<run_attempt>`, Task 7.2) to its `generated_at` (its IDENTITY, r1 redesign Codex X1, X2, r2 C2), or
  to `null` for a NO-REPORT stub (an attempt that completed without a report, r3 F4); `q1_probe_delta` is `{value, generated_at}` or null
  (r1 redesign Claude F6); `absorbed_through` is the newest absorbed `generated_at` and serves FRESHNESS only
  (Task 8.1 clause 7), never which reports are absorbed. `epoch.start` replaces the r2 `SHADOW_START` constant.
  GENESIS is this commit: expiry cannot empty a file (r3 F2).
- **`shadow-compare.py --absorb docs/shadow-ledger.json`**, run LOCALLY by the coordinator with a read-only `gh`
  (no workflow writes the repository; every job keeps a read-only token). It absorbs EVERY trusted report whose
  `report_id` is not yet in the ledger (`list_reports(gh, skip=<every absorbed id, active and archived>)`), by the
  ONE rule `absorb_epoch` below, which the guard also runs. **EVERY, never a subset, and the guard enforces it**
  (r2 redesign Codex C1): under r1 an absorb could take reports of its choosing, so fourteen weekly absorbs of
  unrelated reports kept the watermark fresh while a report contradicting an EXISTING `clean` row aged out of the
  listing; a subset also lets the absorber choose which of two non-miss rows lands first. A miss or a post-switch event only TIGHTENS, so it is taken
  from any trusted report; a non-miss row and Q1's value only LOOSEN, so they are taken only from a report that
  `may_loosen` (ancestor `code_sha`, BASE's two blobs, the active epoch), and any other report is logged
  `ABSORB MISSES ONLY: <report_id> <why>` (r1 redesign Claude F1a: under r1, a comparator change SKIPPED an older
  report's miss whole). A decided row is never overwritten, except that a `miss` replaces a non-miss: **the r1
  `ABSORB CONFLICT` refusal is removed** (r1 redesign Claude F1b) because its resolution was a hand edit choosing a
  side, and the guard (rebuild, below) now refuses every hand edit; "a miss always wins" is the only resolution
  that never loosens, and it is the latch spec §7 Q5 already states. The absorb commit rides the coordinator's
  ordinary docs batch, so it costs no extra PR.
```python
import copy
import json
from datetime import date, datetime, timezone

DECIDED = frozenset({"clean", "miss", "inconclusive", "not a sample"})  # "pending" is never written (F9)

def report_id(rep):
    """A report's IDENTITY: one per run ATTEMPT, so a rerun never replaces an earlier attempt's report (r2 C2).
    A NO-REPORT stub (an attempt that concluded without `success` and uploaded nothing, r3 F4) has one too."""
    return f"{rep['run_id']}.{rep['run_attempt']}"

def as_utc(s):
    """An `epoch.start` (a date, or an ISO-8601 UTC timestamp) or a `generated_at`, as an aware datetime."""
    if len(s) == 10:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def miss_evidence(pr, row):
    """A miss row's evidence, by its FULL identity (r4 B1: r3 matched the PR number alone): one item per differing
    `{target, mutant, seed}` or `{target, control}` of each push that replayed as a miss, keyed by the PR and that
    push's HEAD and BASE. The attempt is not part of it: attempts re-run the same two commits."""
    return {(pr, p["head"], p["base"], json.dumps(d, sort_keys=True))
            for p in row.get("pushes", []) if p.get("result") == "miss" for d in p.get("differing", [])}

def event_evidence(ev):
    """A post-switch event's evidence: the PR's skip of each now-red target, one item per (PR, target). The sweep
    that observed it is not part of it: a master that stays red re-observes the SAME skip in every sweep (r3 F1)."""
    return {(ev["pr"], t) for t in ev["targets"]}

def held_by_archive(epochs, pr=None, row=None, event=None):
    """True only when `epochs` (the ARCHIVED ones, for the absorb) together hold EVERY item of this tightening
    evidence, exactly (r4 B1). EMPTY evidence is never held. Anything else latches the active epoch: a new target,
    mutant, seed or push for an archived PR is evidence the owner has not seen."""
    if event is not None:
        new = event_evidence(event)
        old = set().union(*(event_evidence(e) for ep in epochs for e in ep["post_switch_events"]))
    else:
        new = miss_evidence(pr, row)
        old = set().union(*(miss_evidence(p, r) for ep in epochs for p, r in ep["rows"].items()
                            if r["decision"] == "miss"))
    return bool(new) and new <= old

def may_loosen(rep, epoch, blobs, is_ancestor):
    """None when this report may add non-miss rows and Q1's value; else why not (it still adds misses)."""
    if rep["selector_blob"] != blobs["selector"] or rep["comparator_blob"] != blobs["comparator"]:
        return "blob differs from BASE"
    if not is_ancestor(rep["code_sha"]):
        return "code_sha not an ancestor of BASE"
    if rep["epoch_start"] != epoch["start"]:
        return "report from another epoch"
    return None

def absorb_epoch(epoch, reports, blobs, is_ancestor, archived=()):
    """The ONE absorb rule: --absorb writes it, the guard recomputes it. Never removes anything.
    `archived` is the ledger's `previous_epochs` at BASE."""
    out, log = copy.deepcopy(epoch), []
    for rep in sorted(reports, key=lambda r: (r.get("generated_at") or "", report_id(r))):
        if rep.get("no_report"):  # concluded without a report: absorbed so no listing re-queries it (r3 F4)
            out["absorbed_reports"][report_id(rep)] = None
            continue
        why = may_loosen(rep, epoch, blobs, is_ancestor)
        if why:
            log.append(f"ABSORB MISSES ONLY: {report_id(rep)} {why}")
        for pr, row in sorted(rep["prs"].items()):
            if row["decision"] not in DECIDED or (why and row["decision"] != "miss"):
                continue
            if row["decision"] == "miss" and held_by_archive(archived, pr=pr, row=row):
                log.append(f"HELD BY ARCHIVE: {report_id(rep)} #{pr} miss")
                continue
            old = out["rows"].get(pr)
            if old is None or (row["decision"] == "miss" and old["decision"] != "miss"):
                out["rows"][pr] = dict(row, selector_blob=rep["selector_blob"])
        for ev in rep["post_switch_events"]:
            if held_by_archive(archived, event=ev):
                log.append(f"HELD BY ARCHIVE: {report_id(rep)} event #{ev['pr']}")
            elif ev not in out["post_switch_events"]:
                out["post_switch_events"].append(ev)
        if not why:  # r5 F1: an OBSERVED final attempt count; it loosens, so only from a report that may_loosen
            for run_id, fin in sorted(rep.get("final_runs", {}).items()):
                old = out["final_runs"].get(run_id)
                # an AGREEING repeat keeps the first (no churn); r6 B1: a NEWER one at another count wins,
                # newer by GitHub's time, since every observed_at is a Date header (r7 F3)
                if old is None or (fin["attempts"] != old["attempts"]
                                   and as_utc(fin["observed_at"]) > as_utc(old["observed_at"])):
                    out["final_runs"][run_id] = fin
        q1 = out["q1_probe_delta"]
        if not why and rep["q1_probe_delta"] is not None and (q1 is None or rep["generated_at"] > q1["generated_at"]):
            out["q1_probe_delta"] = {"value": rep["q1_probe_delta"], "generated_at": rep["generated_at"]}
        out["absorbed_reports"][report_id(rep)] = rep["generated_at"]
    out["absorbed_through"] = max((t for t in out["absorbed_reports"].values() if t), default=None)
    return out, log

def absorb_errors(base_epoch, head_epoch, listed, blobs, is_ancestor, archived=()):
    """The guard's absorb clause. `listed` is EVERY trusted report not absorbed at BASE (list_reports with
    skip = every id BASE absorbed, active and archived). The absorb takes ALL of them, never a subset (r2 C1)."""
    base_ids, head_ids = set(base_epoch["absorbed_reports"]), set(head_epoch["absorbed_reports"])
    listed_ids = {report_id(r) for r in listed}
    errs = [f"absorbed id removed: {i}" for i in sorted(base_ids - head_ids)]
    errs += [f"absorbed id is no listed trusted report: {i}" for i in sorted(head_ids - base_ids - listed_ids)]
    errs += [f"listed report not absorbed: {i} (re-run --absorb)" for i in sorted(listed_ids - head_ids)]
    if errs:
        return errs
    expected, _ = absorb_epoch(base_epoch, listed, blobs, is_ancestor, archived)
    return [f"{k} differs from the rebuilt absorb" for k in sorted(set(expected) | set(head_epoch))
            if expected.get(k) != head_epoch.get(k)]

def new_start_errors(base_doc, head_start, today):
    """The epoch-change clause's bound on the new `start` (r3 F2: no backdating). A reports' re-scan reaches back
    to `start`, so a start before the newest absorbed report would re-decide what the archive already decided."""
    ts = [t for ep in [base_doc["epoch"], *base_doc["previous_epochs"]]
          for t in ep["absorbed_reports"].values() if t]
    errs = []
    if as_utc(head_start) <= as_utc(base_doc["epoch"]["start"]):
        errs.append("new epoch start not later than the old")
    if ts and as_utc(head_start) < max(as_utc(t) for t in ts):
        errs.append(f"new epoch start {head_start} before the newest absorbed report {max(ts)}")
    if as_utc(head_start).date() > today:
        errs.append(f"new epoch start {head_start} after today {today}")
    return errs
```
- **`scripts/check-shadow-ledger.py --base REF`.** Its rule, `ledger_change_errors(base_doc, head_doc, reports,
  blobs_at_base, is_ancestor, today) -> list[str]`, is PURE; the fetch (`list_reports`, the download, `git show`,
  `git merge-base --is-ancestor`) is injected (ADR-0014). It reads `git show REF:docs/shadow-ledger.json` and the
  working tree's file. Unchanged → rc 0, `shadow-ledger: unchanged`, with NO API call (an ordinary PR depends on
  nothing remote). Changed → it fetches `reports = list_reports(gh, skip=<BASE's absorbed ids>)` and refuses
  (rc 1, one line per error). **The r1 guard enumerated forbidden EDITS and so passed a watermark-only advance past
  an omitted miss (r1 redesign Codex X1); this one REBUILDS the expected result and refuses everything else:**
  - **an absorb** (the epoch's identity `start`, `selector_blob`, `reset_by_owner` and `previous_epochs`
    unchanged): `absorb_errors` above. HEAD's absorbed ids must be BASE's plus EXACTLY the identities of
    `reports` (every listed trusted report BASE has not absorbed, in any epoch): a removed id, an id that is not
    among `reports` (untrusted, expired, or invented) and a listed report LEFT OUT are each refused; then HEAD's
    epoch must EQUAL `absorb_epoch(BASE's epoch, reports)` field by field, rows, events, Q1, `absorbed_reports`
    and `absorbed_through` included, so a removed or altered row, a `miss` → `clean` change, an EXISTING `clean`
    row a listed report contradicts left `clean` (the rebuild replaces it: a miss always wins), a dropped event, a
    row no report holds, an older Q1 and a moved watermark are all one clause (r2 redesign Codex C1: the r1 fold
    rebuilt from the ids HEAD CHOSE, and its extra check covered only rows HEAD ADDED, so an absorb that left out
    the report contradicting an existing row passed). The rebuild passes BASE's `previous_epochs` as
    `archived`, so `held_by_archive` is part of what HEAD must equal (r3 F1). **Its cost, stated (r3 F7):** a
    report published between the local `--absorb` and a `verify` run is listed by the guard and not absorbed, so
    that `verify` is red with `listed report not absorbed: <id> (re-run --absorb)` until the absorb is re-run.
    Every push to the PR re-runs `verify` and re-lists, so the cost is one re-absorb per PUSH whose `verify`
    follows a schedule the local absorb did not see, not one per PR (the absorb rides the ordinary docs batch,
    which may take several pushes). The absorber therefore runs `--absorb` immediately before EACH push of a PR
    that carries an absorb. It fails closed;
  - **an absorb gap**: BASE's `absorbed_through` (or `epoch.start`) more than 76 days before today → refused; only
    an epoch reset clears it. This and gate clause 7 are the only reads of the timestamp watermark, and both can
    only REFUSE. **The bound, restated from what the C1 fix makes true and attacked before it was written:** every
    admitted absorb takes every listed report, and `absorbed_through` is never later than the previous absorb, so
    at the next admitted absorb (at most 76 days after `absorbed_through`) every report uploaded after the
    previous one is at least 14 days from its 90-day expiry, and the 120-day `created` window (Task 7.2) still
    lists its run even when it is a rerun attempt uploaded 30 days after its run began. A trusted report is
    therefore lost unabsorbed only if NO absorb is admitted during its whole life, and then the ledger cannot
    advance at all and gate clause 7 has closed the switch since day 14. **ASSUMED, not stated by GitHub:** an
    artifact expires 90 days after its UPLOAD (the docs give `expires_at`, not its start); a shorter life is
    still caught for a successful attempt in the window, because its missing or `expired` report RAISES (Task
    7.2). Simulated over the extracted `absorb_epoch`/`absorb_errors` rule's listing model (3,000 random absorb
    schedules × 3 seeds, uploads up to 30 days after run creation): no report expired unabsorbed before the last
    admitted absorb; the same simulation with a 90-day `created` window, or a 92-day gap, LOSES reports (the
    controls);
  - **an epoch change** (any identity field or `previous_epochs` differs): `previous_epochs` must be BASE's with
    BASE's active epoch appended VERBATIM (its rows, misses, events and absorbed ids with it); the new epoch must
    be EMPTY (`fresh_epoch`: no rows, events, ids, Q1 or `final_runs` carried; the archived epoch keeps its own `final_runs`, which `settled` still reads); `new_start_errors` (code above) empty;
    `reset_by_owner` a non-empty string; `selector_blob` equal to BASE's `reach_select.py` blob (r3 F5; r1
    redesign Codex X3). **The new `start` (r3 F2: no backdating)** is strictly later than the old, NO EARLIER than
    the newest `generated_at` absorbed in ANY epoch, and no later than `today`; it may be a date or an ISO-8601
    UTC timestamp (`as_utc`). Every report re-runs `post_switch` over red sweeps since `start`, and every sweep an
    absorbed report decided happened before that report's `generated_at`, so a start at or after it cannot
    re-decide what the archive holds. PRs are no longer scanned from `start` (r4 class search): the report lists
    them from GENESIS and omits what `settled` finds decided in ANY epoch (Task 7.2), so a PR pending at the reset
    is still compared and can latch, and a PR merged before `start` can never count toward the 20 (gate clause 5,
    Task 8.1); under r2 a start of
    2027-01-02 on a 2027-03-01 reset re-recorded the archived #600 miss in the new epoch every day.
    **What a reset clears, precisely (r3 F1).** A report written for the OLD epoch and absorbed only after the reset
    (it is near-certain: the daily report between the absorb and the reset's merge repeats every miss and event
    the old epoch latched) is absorbed into the NEW epoch for its misses and events only (`may_loosen`: `report
    from another epoch`), and of those, `absorb_epoch` drops each one `held_by_archive` finds in the archived
    epochs EXACTLY, logging `HELD BY ARCHIVE`: every item of its evidence must be there, a miss's
    `miss_evidence` (PR, push HEAD and BASE, and each differing target with its mutant and seed, or control) and an
    event's `event_evidence` (PR, target), and empty evidence is never held (r4 B1: the r3 predicate matched a
    `miss` by the PR number alone, so an archived #600 miss on `scripts/x.py` dropped a trusted report's NEW #600
    miss on `scripts/y.py`, and the guard, rebuilding with the same predicate, accepted it; Codex ran it). A
    coarse match fails toward LOOSENING; an exact one fails only toward latching too much (liveness). **A reset clears exactly what it archived:** evidence the owner saw is not re-latched, and
    evidence NO archive holds, whenever it was generated, latches the new epoch, because the owner has not seen it.
    The same predicate applies to every report, so a red master that stays red after the reset and re-blames the
    archived PR's target in a NEW sweep does not re-latch either (the sweep is not part of an event's identity:
    it re-observes the same skip), while a NEW target for it does, as does a new target, mutant, seed or push
    in a miss row for an archived PR. **Not taken,
    and why:** the coordinator's first form, "evidence counts only if its event happened at or after `start`",
    would drop a pre-reset miss the owner never saw (one in a report published after the reset PR's `verify`)
    while recording the report as absorbed, which spec §8.6 lists as a failure ("records a report as absorbed
    without absorbing its misses") and which loosens the latch; and the reviewer's option (a), refusing a reset
    while any report is unabsorbed, leaves that same window between the reset PR's `verify` and its merge, so it
    needs this rule anyway. The archive rule alone closes both;
  - **genesis**: no file at BASE → HEAD must be an empty epoch keyed to BASE's selector, `previous_epochs: []`;
  - a HEAD document that fails `ledger_schema_ok`, or a BASE that has the file and HEAD deletes it.
  A failed listing or download while the ledger changed is rc 2, CANNOT RUN, never a pass. Caller: a `verify` step
  `python3 scripts/check-shadow-ledger.py --base "${{ github.event.pull_request.base.sha }}"` on `pull_request` (the
  ledger reaches master only through a PR); `verify` already checks out with `fetch-depth: 0`, which the ancestry
  clause needs. **`verify` has no `permissions:` block today, so it gains the WHOLE block `permissions: {contents:
  read, actions: read}`** (r1 redesign Claude F7: a job-level block sets every unlisted scope to `none`, so adding
  `actions: read` alone would revoke `contents` and break every checkout); `verify` makes no write call today
  (no `gh`, no `GH_TOKEN`), so the explicit block loses nothing. **The guard step carries `env: GH_TOKEN: ${{
  github.token }}`** (r2 redesign Codex C3: `verify` exports no token today, and Codex measured `gh api` with no
  token and an empty config exit 4 before any request; a `permissions:` block grants scopes, it exports nothing);
  the Task 7.2 `GH_CALLERS` case reads it.
- **`scripts/check-merge-ready.py`: a HOLD reason `shadow-ledger epoch changed`** when BASE's and HEAD's
  `epoch.start`, `epoch.selector_blob`, `epoch.reset_by_owner` or `previous_epochs` differ (an absorb changes
  only the active epoch's contents and does not HOLD). Spec §7 Q5 makes a revisit the owner's, and a HOLD makes that
  a machine rather than the r2 `EPOCH RESET` PR-body convention (r3 F5's residue). WM pins.
- [ ] **Failing cases of `ledger_change_errors`, each a scenario that PASSED the r1 guard, with its ADJACENT pass:**
  **(X1, watermark-only)** BASE absorbed through T0, a listed trusted report at T1 holds a new miss, HEAD advances
  only `absorbed_through` to T2 ≥ T1 → refused (adjacent: HEAD = the absorb of that report → passes); **(X1,
  dropped evidence)** HEAD absorbs the miss report's id but omits its miss row → refused, and the same with the
  row turned `clean` → refused; **(F1b, hand-picked subset)** reports R1 (#600 `miss`) and R2 (#600
  `inconclusive`, #601 `clean`) both listed, HEAD absorbs only R2 → refused, `listed report not absorbed: <R1>`
  (adjacent: HEAD absorbs both → #600 `miss`, passes); **(r2 C1, a selective absorb against an EXISTING row —
  the Codex scenario, which PASSED the r1 fold's guard)** BASE holds #600 `clean`; listed R1 decides #600 `miss`
  and R2 decides only #601; HEAD = `absorb_epoch(BASE, [R2])` → refused, `listed report not absorbed: <R1>` (the
  r1 rebuild over the CHOSEN ids equals HEAD, and its ADDED-rows check never looked at #600); fourteen such weekly
  absorbs, each of one unrelated report while R1 stays listed → each refused at the first; adjacent: HEAD =
  `absorb_epoch(BASE, [R1, R2])` → #600 `miss`, passes; **(r2 C1, the contradiction kept by hand)** HEAD carries
  both ids but keeps #600 `clean` → refused, `rows differs from the rebuilt absorb`; **(r2 C1, a subset choosing
  which non-miss row lands)** R_a (earlier) #601 `inconclusive`, R_b #601 `clean`, HEAD absorbs only R_b →
  refused (adjacent: both → `inconclusive`, the earlier report's row, in either input order); **(r2 C1, the race,
  its stated cost)** a report published after the local absorb is listed at `verify` → refused, `re-run
  --absorb`, and the re-run absorb passes; **(r2 C2)** run 9's attempts `9.1` (#650 `miss`) and `9.2` (#650
  `clean`) both listed, HEAD absorbs only `9.2` → refused; both → `miss`, two identities; **(F6)** HEAD's
  `q1_probe_delta` `{value: 4}` from the older of two absorbed reports when the newer says 7 → refused (adjacent:
  7 → passes); an absorbed id no listed report has → refused; a removed absorbed id → refused; a removed row, a
  dropped post-switch event → refused; a report from a `pull_request` run → not listed, so its id is refused;
  each `trusted_report_run` clause alone (event, `path` of another workflow, a feature `head_branch`, a fork whose
  branch is named `master`) → untrusted, adjacent: `schedule` on the default branch → trusted; **(X3, a reset from
  an actual latch)** BASE's active epoch holds a `miss` row; HEAD archives it verbatim and starts an empty epoch
  with `reset_by_owner` set and `start` later → passes, and the gate's clause 4 then sees no miss (under r1 the
  rows sat outside `epoch`: keeping them refused forever, dropping them was refused by the guard); adjacent: the
  archive drops the miss row → refused; an empty `reset_by_owner` → refused; the new epoch carries the old rows →
  refused; `start` moved backward → refused; an earlier `previous_epochs` entry altered → refused; **(a report
  from the old epoch, absorbed after a reset)** its #610 `miss` and #611 `clean` → the new epoch holds #610 `miss`
  and no #611 (adjacent: the same report with the new epoch's `epoch_start` → both rows); **(r3 F1, the
  reviewer's `reset.py`: a reset re-closed by an old-epoch report)** R10 (old epoch d0) holds post-switch event
  E `{sweep 77, #600, [scripts/x.py]}` and is absorbed; R11, written the next day before the reset merges,
  repeats E with `epoch_start` d0; the owner's reset (archive verbatim, empty epoch, `start` d12) passes; the
  next absorb MUST take R11 (leaving it out → `listed report not absorbed: 11.1`) → the new epoch holds NO event,
  `HELD BY ARCHIVE: 11.1 event #600` logged, and gate clause 4 does not refuse (under r2 the new epoch held E and
  clause 4 refused `latched miss`, undoing the reset); a HEAD carrying E in the new epoch (the r2 absorb) →
  refused, `post_switch_events differs from the rebuilt absorb`; the same with a repeated `miss` row for #600
  the archive holds → no row; adjacent (the latch still works): an old-epoch report's UNSEEN #610 `miss` (no
  archive holds it) → latches the new epoch; a new-epoch report's event for #600 on a NEW target
  `scripts/y.py` → latches; a later red sweep (sweep 91) re-blaming #600 on `scripts/x.py` → held, not latched;
  **(r4 B1, Codex's reproduction; each FAILED under the r3 `held_by_archive`, which matched the PR alone)** the
  archived epoch holds #600 `miss` with one push `{head h1, base b1, result miss, differing [{target
  scripts/x.py, mutant m1, seed null}]}`; the active epoch holds 20 clean rows; trusted report `11.2` (old
  epoch, absorbed misses-only) holds #600 `miss` at the same push on `scripts/y.py` → the absorb writes #600
  `miss` into the active epoch, no `HELD BY ARCHIVE` line, and gate clause 4 refuses `latched miss` (r3: no row,
  `HELD BY ARCHIVE: 11.2 #600 miss`, guard errors `[]`, clauses 4 and 9 open); a HEAD equal to the r3 absorb's
  output (11.2 absorbed, no #600 row) → refused, `rows differs from the rebuilt absorb`; **(the same PR at another
  push)** 11.2's #600 `miss` on `scripts/x.py`, mutant m1, at push `{head h2, base b2}` → latches; a different
  mutant or seed at push h1/b1 → latches; a #600 `miss` row whose pushes list NO differing item → latches
  (empty evidence is never held); an event `{sweep 91, #600, []}` → latches; **adjacent (held):** 11.2's #600
  row byte-identical to the archived one, repeated by a daily report → no row, `HELD BY ARCHIVE: 11.2 #600
  miss`, guard passes; the same row with an EXTRA non-miss push (`result: clean`) → still held (only `miss`
  pushes are evidence); an event `{sweep 91, #600, [scripts/x.py]}` when the archive holds x.py and y.py in two
  separate events of #600 → held (identity is per (PR, target));
  **(r5 F1, the observation the absorb records)** a report that `may_loosen` with `final_runs {"55": {attempts 1,
  observed_at 2027-02-02T07:00:00Z}}` → the active epoch's `final_runs` holds it, and a HEAD without it → refused,
  `final_runs differs from the rebuilt absorb`; a second report repeating 55 with a later `observed_at` → the
  first stays (no churn); **(r6 B1)** a later report with 55 at `attempts 2` → REPLACES it, and a HEAD keeping
  the first → refused; an EARLIER-observed report at another count, absorbed later → the record stays; the same entry in a report that may NOT loosen (`report from another epoch`) → not
  recorded, `ABSORB MISSES ONLY` logged; a HEAD that adds a `final_runs` entry no listed report holds → refused;
  an epoch reset whose new epoch carries `final_runs` → refused (the archive keeps its own);
  **(r3 F2, a backdated epoch start)** BASE's newest absorbed `generated_at` 2027-01-10T06:00:00Z, a reset on
  2027-03-01 with `start` 2027-01-02 → refused, `new epoch start 2027-01-02 before the newest absorbed report
  2027-01-10T06:00:00Z` (r2's "strictly later" passed it, and every later report re-recorded #600's archived
  miss); a newest `generated_at` in an ARCHIVED epoch counts too; `start` after `today` → refused; adjacent:
  `start` equal to the newest `generated_at`, or `today`, → passes; **(r3 F4)** an absorb taking a no-report stub
  `40.1` → `absorbed_reports["40.1"]` is `null`, `absorbed_through` ignores it, the guard passes; leaving the
  stub out → `listed report not absorbed: 40.1`; **(gap)** BASE
  absorbed 77 days ago → refused (adjacent: 75 → passes); genesis with a row → refused (adjacent: empty →
  passes); a deleted ledger → refused; a PR that does not touch the ledger → rc 0, `shadow-ledger: unchanged`,
  and the injected `gh` was never called; a failed listing with a changed ledger → rc 2.
- [ ] **Failing cases of `--absorb` (`absorb_epoch`):** **(F1a)** a report whose `comparator_blob` differs from
  BASE's holding #600 `miss` and #602 `clean` → #600 absorbed `miss`, #602 absent, `ABSORB MISSES ONLY` logged
  (r1: the whole report skipped, the miss lost); a report with a `code_sha` not an ancestor of BASE, and one from
  an earlier epoch, likewise misses only; a `clean` row and a later report saying `miss` → `miss` (adjacent: a
  `miss` row and a later report saying `clean` → still `miss`); **(F9)** a report row `pending` → no row written,
  `inconclusive` → written; **(F5)** every written row carries the writing report's `selector_blob`; **(F6)** two
  reports absorbed out of `generated_at` order → Q1 is the newer's; an untrusted run → never listed, never
  absorbed; the absorbed file passes `ledger_change_errors` against the pre-absorb file (the absorb and the guard
  share `absorb_epoch`, so this is a case by construction, and a mutation of `absorb_epoch` must redden BOTH).
- [ ] **Failing cases of the HOLD:** an epoch change → HOLD `shadow-ledger epoch changed`; adjacent: rows added by
  an absorb, epoch identity unchanged → no HOLD; no ledger at BASE or HEAD → no HOLD.
- [ ] **(F7) A `ci.yml` read case:** the `verify` job's `permissions` is exactly `{contents: read, actions: read}`
  (it fails on a block holding `actions: read` alone, the one-line edit that would revoke `contents`); and its
  guard step's `env.GH_TOKEN` is exactly `${{ github.token }}` (r2 C3; the step is in Task 7.2's `GH_CALLERS`
  read, which fails on the r1 fold's step without it).
- [ ] **Steps:** red, implement, green, W1-W8 for both new scripts, WM pins for `shadow-compare.py` and
  `check-merge-ready.py`, mutate `--only` each of the four, commit.

**Pre-push (slice 7):** `python3 scripts/shadow-compare.py --self-test`; `python3 scripts/reach_gate.py --self-test`;
`python3 scripts/check-shadow-ledger.py --self-test`; `python3 scripts/check-merge-ready.py --self-test`;
`python3 scripts/check-plan-code.py --mutate . --only` each of `scripts/shadow-compare.py`, `scripts/reach_gate.py`,
`scripts/check-shadow-ledger.py`, `scripts/check-merge-ready.py`; `python3 scripts/check-ratchet-contract.py`;
`python3 scripts/check-python-pin.py` (the new workflow's job pins Python).
**Merge gate:** after merge, a `workflow_dispatch` of `shadow-compare.yml` on master uploads one
`shadow-report-<run_id>-<run_attempt>`, the FIRST SCHEDULED run uploads one too (r1 redesign Claude F3: the r1
`if:` skipped every scheduled run, which no dispatch could reveal), and a first absorb PR passes
`check-shadow-ledger.py` in its own `verify` (with `GH_TOKEN`, r2 C3). **Two live reads GitHub's docs do not
settle (r2 C2):** while a dispatch is `in_progress`, the runs listing WITHOUT `status` returns it (the docs do
not say what an omitted `status` includes); and after re-running a completed dispatch, the run's artifacts
listing still returns attempt 1's `shadow-report-<id>-1` (the docs do not say whether a rerun keeps an earlier
attempt's artifacts). Either answer is fail-closed by Task 7.2's rule (a successful attempt without its report
RAISES); the reads record WHICH, in the measurement doc, so a gate refusing `reports unreadable` after every
rerun is not a surprise.

---

## Slice 8 — the switch (LAST; spec §7 Q4, §8.1)

**Design D1 (owner 2026-11-09 14:55).** `switch_gate` reads the committed ledger's ACTIVE epoch AT BASE; trusted
reports whose identity that ledger has not absorbed can only close the switch (architecture review §6; r1 redesign
Codex X2: by identity, never by a timestamp).

**The preconditions are a MACHINE, not a paragraph (r1 Claude F2).** The spec's are: backlog #590 ✅ ("must close
before any skip takes effect; shadow mode alone is not enough"), ≥ 20 COMPLETE clean PRs from the ledger's epoch
start with 0 latched misses (§7 Q4), and Q1 decided (§2: probe delta ≤ 5 on PR #543's diff, or 3(c) reverted to
option A). The owner's merge-when-READY rule would merge a slice-8 PR whose prose says "do not merge yet", and
`check-merge-ready.py` cannot HOLD it: `hold_reasons` reads syntactic proxies only (its own comment: "A SEMANTIC
loosening … is outside what a diff rule can see"), and no PR-body marker forces a HOLD (the only body-driven HOLD is
`NO-REVIEW:`, a waiver, not a precondition). So `switch_gate` (Task 8.1) checks all three on EVERY pull request, at
run time, and a refused gate leaves the selection at today's rule. Slice 8 can then be built and merged whenever it
is ready; it skips nothing until the evidence exists, and it STOPS skipping by itself if a miss appears later
(spec §8.1: one case "stops the switch, or reverts it"): a shadow miss or a post-switch event (Task 8.2) in any
trusted report closes the gate on the next PR, before it is absorbed, and the absorb makes it permanent for the
epoch. The PR
body quotes the gate's line from its own `sweep-select` log (`SWITCH GATE: refused — <why>` is the expected line
while shadow mode runs). A latched miss goes to the owner (spec §7 Q5: revisit).

### Task 8.0 (only if the ledger's `epoch.q1_probe_delta.value` > 5): rule 3(c) reverts to option A in `reach_select.py`, with the fixture
case updated, and `Q1_DECISION = "A"`. A separate commit, reviewed on its own. Its own PR cannot open the gate
with the new value: `switch_gate` reads `Q1_DECISION` at BASE, and `shard_targets` refuses any list on a PR that
changes `reach_select.py` (Task 8.1; r2 Codex F2). **Its stated cost:** the revert changes `reach_select.py`'s
blob, so the gate refuses `selector changed since epoch` until an epoch change records the new `selector_blob`
(Task 7.3: owner's `reset_by_owner`, a HOLD), and the 20-PR count restarts under the new rule. That is correct,
because the rule changed; it is stated, not avoided.

### Task 8.1: `switch_gate` in `reach_gate.py`, and shards run `sweep-select`'s list

**Files:** Modify `scripts/reach_gate.py` (`switch_gate`, `q1_at_base`; its manifest and WM pins),
`scripts/reach_select.py` (`Q1_DECISION`, `SELECTOR_FILES`; WM pins), `.github/workflows/ci.yml`,
`scripts/check-plan-code.py` (`--targets FILE`, `shard_targets`; WM pins); the slice-6 invariant case flipped.
`switch_gate` and `q1_at_base` live in `reach_gate.py`, NOT in `reach_select.py`, so editing the GATE does not move
the evidence key (`reach_select.py`'s blob, r3 F8). `reach_gate.py` is in `SELECTOR_FILES`.

**Interfaces:**
- `Q1_DECISION: str` (in `reach_select.py`) — `"B"` (the owner's choice) until Task 8.0 sets `"A"`.
- `q1_at_base(src: str | None) -> str | None` — `Q1_DECISION`'s literal from `git show BASE:scripts/reach_select.py`
  (`ast`, the module-level assignment only), or None when the file is absent, unparseable, the name is missing, or
  its value is not exactly `"A"` or `"B"` (r2 Codex F2). Before slice 8 merges, BASE has no `Q1_DECISION`, so
  slice 8's own PR is refused here too.
- `switch_gate(backlog_at_base: str | None, ledger_at_base: dict | None, q1_decision: str | None,
  selector_blob_at_base: str, fetch_reports: Callable[[set[str]], list[dict] | None], today: date) -> str | None`
  — None = the switch may take effect; else the refusal, checked in this order. **Reports are fetched LAST, and
  only when clauses 1-7 pass** (r1 redesign Claude F4): `fetch_reports(skip)` is `list_reports(gh, skip, today)`
  with a failure turned into None, and `skip` is every id the BASE ledger absorbed (active and archived), so while
  shadow mode refuses at clause 5 an ordinary PR makes NO Actions API call. Every clause reads the ACTIVE epoch
  (`ledger_at_base.epoch`) only; `previous_epochs` is history for the guard and is never counted (r1 redesign Codex
  X3):
  1. `backlog_at_base` is None (`git show BASE:docs/backlog.md` failed) → refused; row `| 590 |`'s status cell does
     not begin with `✅` → `backlog #590 open`;
  2. `ledger_at_base` is None, or fails `ledger_schema_ok` (`git show BASE:docs/shadow-ledger.json` absent or
     unparseable) → `no ledger at BASE`;
  3. `ledger_at_base.epoch.selector_blob != selector_blob_at_base` (`git rev-parse BASE:scripts/reach_select.py`)
     → `selector changed since epoch` (r3 F8);
  4. any `miss` row or any `post_switch_events` entry in the active epoch → `latched miss`;
  5. fewer than 20 consecutive complete clean rows of the active epoch, in `merged_at` order, counting only rows
     whose `merged_at` is at or after `epoch.start` (r4 class search: the report lists PRs from GENESIS so that a
     PR pending at a reset can still latch, and such a PR merged before the reset is evidence the owner's reset
     already weighed, so it may close the switch and never open it) and whose `selector_blob` equals `epoch.selector_blob` (r1 redesign Claude F5: a row decided by an earlier
     selector is not evidence about this one), ignoring `not a sample` rows (an `inconclusive` row does not reset
     the run but is not counted; a `miss` resets it, though clause 4 already refused) → `N of 20 clean PRs`;
  6. `q1_decision` is None → `Q1 decision unreadable at BASE`; `q1_decision == "B"` and the active epoch's
     `q1_probe_delta` (at BASE) is null or its `value` > 5 → `Q1 undecided`. The value is the NEWEST absorbed
     report's (`absorb_epoch` keeps it by `generated_at`, and the guard refuses any other; r1 redesign Claude F6);
  7. the active epoch's `absorbed_through` is null or more than 14 days before `today` → `ledger stale` (a
     comparator or absorb that stops running fails CLOSED; the inverse of r3 F2). This is the ONLY use of the
     timestamp watermark;
  8. `fetch_reports(skip)` returns None (a listing, artifact lookup or download failed) → `reports unreadable`;
  9. any listed trusted report whose `report_id` (`<run_id>.<run_attempt>`, every attempt of every run whatever
     its current status, Task 7.2; r2 C2) is NOT absorbed in the BASE ledger (in no epoch) holds a `miss` row
     or a post-switch event → `unabsorbed miss`, whatever its `generated_at` (r1 redesign Codex X2, Claude F1c: a
     report uploaded after a later one was absorbed is still read). The read is a UNION over those reports, so the
     newest report omitting a miss cannot hide it (r3 F3, F5 in the window). A report absorbed in an ARCHIVED epoch
     is not re-read. An OLD-epoch report still unabsorbed when the reset merged IS read here, and refuses until
     the next absorb; that absorb latches only what no archived epoch holds (Task 7.3, `held_by_archive`), so an
     owner's reset is not undone by it either (r3 F1: the r2 text claimed this while the absorb re-latched). This
     clause stays a plain union, NOT filtered by `held_by_archive`: it can only close, and its cost is one refusal
     window per such report, bounded by the next absorb.
  **Every input that can OPEN the switch (1-7) is read at BASE, never at HEAD and never from Actions storage**
  (`q1_decision` is `q1_at_base(...)`, never the running module's constant), so a PR cannot enable its own skips
  by ticking #590, flipping the decision or editing the ledger in its diff. **Reports (8-9) can only CLOSE it**: a
  forged or untrusted report could at most refuse.
- `sweep-select` (now also in slice 8's `needs:` graph; `actions: read`, already held; its `--select-only` step,
  which now runs `switch_gate` and so `list_reports`, carries `env: GH_TOKEN: ${{ github.token }}` as its
  cache-list step does, r2 C3) runs `git show
  "$BASE":docs/backlog.md`, `git show "$BASE":docs/shadow-ledger.json`, `git show "$BASE":scripts/reach_select.py`
  (→ `--q1-base FILE`; absent → `q1_at_base(None)`) and `git rev-parse "$BASE":scripts/reach_select.py`, lists the
  trusted reports by `list_reports` (Task 7.2) only when `switch_gate` asks, runs `switch_gate`, and when refused writes TODAY's selection
  (`select_manifests`) as `targets`, logging `SWITCH GATE: refused — <why>`; when passed, writes the observed list
  and logs `SWITCH GATE: open`.
- `shard_targets(event: str, select_result: str, output: str | None, full: str | None, reasons: dict, known:
  frozenset, changed_paths: set[str]) -> tuple[list[str] | None, str]` in `check-plan-code.py` — the list a shard
  runs, None = its own rule (today's `select_manifests`, which is FULL on a push or the schedule). **The shard does
  not trust the list (r2 Codex F1, F2): it re-derives `full, reasons` by calling `select_reasons` on its OWN diff**
  (the call `select_manifests` already makes there), and `known` is the manifest target set. Checked in order, the
  first failure → None with that reason: `event != "pull_request"`; `select_result != "success"`; `full` is not
  None (`full: <why>`: rule 1 runs ALL whatever the list says); any `changed_paths` member in `SELECTOR_FILES`
  (`selector changed`; `SELECTOR_FILES = frozenset({"scripts/reach_select.py", "scripts/reach_gate.py"})`, so the PR
  that edits the selector, `switch_gate` or `Q1_DECISION` runs today's rule); `output` is not a non-empty JSON list
  of distinct strings; an element not in `known` (`unknown target <t>`); a target whose `reasons` hold `own-source`
  or `own-manifest` missing from the list (`missing mandatory <t>`). Else the list. These checks live in the
  HARNESS, so a PR that edits them gets FULL from `full`. `--targets FILE` reads the file the step wrote from
  `needs.sweep-select.outputs.targets` and calls it.
- **`ci.yml` (r1 Codex F1, BLOCKER).** `mutation-sweep` gets `needs: sweep-select` AND `if: ${{ !cancelled() }}`.
  GitHub skips a job whose `needs:` job was skipped or failed unless its `if:` says otherwise, and `sweep-select`
  is `pull_request`-only, so without that `if:` the master push and the schedule (the FULL sweeps, the backstop of
  spec §4) and every PR whose selector failed would run NO sweep, and `mutation-sweep-complete` (`if: always()`,
  which fails any result but `success`) would report FAILED on every master push. The shard step passes
  `SELECT_RESULT: ${{ needs.sweep-select.result }}` and the output to `shard_targets`, so the decision is in
  Python, not YAML.
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
  valid list holding every mandatory pick → None, `selector changed`, and the same for `scripts/reach_gate.py`; a
  case asserts every module `reach_select.py` or `reach_gate.py` imports from `scripts/` (by `ast`, as
  `harness_files` reads imports) is in `SELECTOR_FILES` or in `harness_files`, so a new selector module cannot
  escape the refusal. `SKIPPED:` replaces `WOULD-SKIP:` in the log.
- [ ] **Failing cases, `switch_gate`, each refusal with its ADJACENT pass:** #590's row with `🟠` → refused, with
  `✅ (was 🟠)` → passes that clause; no ledger at BASE → refused, while the PR's HEAD carries a valid 20-clean
  ledger (the gate reads BASE); a ledger whose `epoch.selector_blob` ≠ BASE's blob → `selector changed since
  epoch`, equal → passes; 19 clean → refused, 20 → passes; 20 clean and one `miss` row → refused; one post-switch
  event → refused; 20 clean rows recorded under an earlier epoch (in `previous_epochs`) and none in the current →
  `0 of 20`; **(r4 class search)** 20 clean rows of the active epoch, one of them merged before `epoch.start`
  (a PR pending at the reset, decided after it) → `19 of 20` (r3 counted it: 20, open), adjacent: that row
  merged AT `epoch.start` → passes; `Q1_DECISION="B"` with the ledger's delta 6 → refused, 5 → passes, `"A"` with delta 6 → passes;
  **(r2 Codex F2)** BASE source with `"B"`, delta 6, while the RUNNING module says `"A"` → refused (the gate takes
  BASE's); `q1_at_base` of a source with `Q1_DECISION = "C"`, of one with no assignment, of `None` and of
  unparseable text → None → refused, adjacent: `"A"` → `"A"`; `absorbed_through` 15 days before `today` →
  `ledger stale`, 14 → passes; a fetch returning None → `reports unreadable`, `[]` → passes; a listed report
  whose id is unabsorbed with a miss → `unabsorbed miss`, while the NEWEST report omits it (the union);
  **(X2, a late upload across an absorb)** the BASE ledger absorbed R2 (`generated_at` 10:01, no miss) so its
  `absorbed_through` is 10:01, and R1 (`generated_at` 10:00, a miss, uploaded after that absorb) is listed →
  `unabsorbed miss` (r1 compared 10:00 with 10:01 and passed), adjacent: R1's id in `absorbed_reports` → passes;
  a report absorbed in an ARCHIVED epoch with a miss → passes clause 9 (the owner's reset holds); **(r3 F1)**
  right after a reset, an OLD-epoch report `11.1` absorbed in no epoch repeats the archived event → `unabsorbed
  miss` (closes, never opens), and after the absorb of `11.1` (Task 7.3: held by the archive, nothing latched)
  the same ledger passes clauses 4 and 9, refusing only at clause 5 (`0 of 20`); **(F5, a row
  decided by the previous selector)** 20 clean rows whose `selector_blob` is X in an epoch keyed to Y → `0 of 20`
  (r1 rows carried no blob and counted 20), adjacent: the same rows with blob Y → passes; **(X3)** a `miss` in
  `previous_epochs` with 20 clean active rows → passes clause 4 (r1 had no archive of rows to read); **(F6)** the active epoch's `q1_probe_delta.value` 7 while an older absorbed
  report said 4 → `Q1 undecided` (the ledger can hold only the newest; Task 7.3 refuses 4); **(F4)** a ledger
  refused at clause 5 → the injected `fetch_reports` was called ZERO times; a ledger passing 1-7 → called once,
  with `skip` equal to the BASE ledger's absorbed ids; a report that claims 25 clean rows the ledger lacks does
  NOT open a gate refused at `N of 20` (a report can only close); a HEAD backlog with ✅ and a BASE backlog
  without → refused (the gate reads BASE).
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
  --post-switch --out "$RUNNER_TEMP/post-switch.md"`, with `env: GH_TOKEN: ${{ github.token }}` (r2 C3; a
  missing token would make every result `NOT CHECKED`). The job gains `actions: read` (to list and download
  artifacts); it already holds `issues: write` for `sweep-red-alert.py` (backlog #330). No new job, and no new
  write permission.
- **Its output contract.** The file is Markdown: `POST-SWITCH: <N> merged PR(s) skipped a now-red target` and one
  line per PR (`#N skipped <targets>`), or `POST-SWITCH: none`, or `POST-SWITCH: NOT CHECKED — <why>` (a missing
  selection artifact, an API failure). The step never fails the job. `sweep-red-alert.py` gains env
  `POST_SWITCH_REPORT` (a path): `red_body` APPENDS the file's text when it exists, and appends
  `POST-SWITCH: NOT CHECKED — no report file` when the variable is set but the file is absent. It remains the ONE
  writer of the `sweep-red` issue.
- **It also LATCHES, in three steps.** (1) `shadow-compare.py --report` (Task 7.2's daily job) calls `post_switch`
  over every red master full sweep since `epoch.start` and records each hit in the REPORT's `post_switch_events`;
  (2) the gate's tightening read (Task 8.1, clause 9) closes the switch on the next PR, before any absorb, because
  the report's id is unabsorbed; (3) the absorb copies the event into the active epoch, where the guard's rebuild
  forbids dropping it (Task 7.3), and clause 4 keeps the switch closed, UNLESS the archived epochs already hold
  every (PR, target) of it exactly (`held_by_archive`, Task 7.3, r4 B1: the owner's reset archived it, so it is logged `HELD BY ARCHIVE` and not re-latched;
  r3 F1). Turning it back on is the owner's (spec §7
  Q5: "revisit on the first §8.1 event"): a reviewed commit that starts a NEW EPOCH in `docs/shadow-ledger.json`
  (a `start` bounded by `new_start_errors`, Task 7.3: later than the old, not before the newest absorbed
  report, not after today; the old epoch, its rows, misses, events and absorbed ids WITH it, appended verbatim to
  `previous_epochs`, an EMPTY new epoch, a non-empty `reset_by_owner`), which `check-shadow-ledger.py` checks and
  `check-merge-ready.py` HOLDs (Task 7.3). The gate reads only the active epoch, so the latch no longer refuses and
  the 20-PR count restarts at zero; the archived miss stays in the file, unalterable (r1 redesign Codex X3: under
  r1 the rows and events sat outside `epoch`, so no reset could both satisfy the guard and clear the latch).
- [ ] **Failing cases:** a red target in a merged PR's SKIPPED set → reported; a red target skipped by no PR → not;
  a missing selection artifact → reported as NOT CHECKED, never silent; the daily report records a hit as one
  `post_switch_events` entry; a later report, after the hit's inputs expired and the hit was absorbed, omits it
  while the ledger keeps it (the guard refuses its removal, Task 7.3); **(X3)** from a ledger whose active epoch
  holds that event, an owner's epoch reset passes `check-shadow-ledger.py` and `switch_gate` no longer refuses at
  clause 4 (adjacent: the same reset with the event deleted from the archive → refused by the guard); **(r3 F1,
  live loop)** master stays red after that reset: the next daily report (new epoch) re-blames #600 for the same
  target in a NEW sweep → `report()` omits it (held by the archive at the checkout), the absorb holds it, and
  clauses 4 and 9 do not refuse (under r2 it re-latched every day and the reset never held); the same sweep
  blaming a DIFFERENT merged PR, or #600 for a NEW target → recorded and latched (adjacent); `sweep-red-alert.py`: with a report file
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
  Q1 fallback: Task 3.2 (`probed_stat_only`), 6.1 (the pure delta), 7.2 (computed in the report), 7.3 (absorbed), 8.0, 8.1 (`Q1_DECISION`). Shadow data + comparator + MISS +
  ledger persistence: Tasks 6.1-7.3 (the committed ledger, absorb by identity, the guard's rebuild and the epoch
  archive: Task 7.3; spec §2 *The ledger*). Image drift (§2 Resolve, §4.4): Tasks 6.1 (headers), 7.2 (counted).
- §2 "backlog #590 must close before any skip takes effect" and §7 Q4: `switch_gate` (Task 8.1), at run time, so
  no merge rule can bypass it.
- Trust in the gate's inputs (design D1, owner 2026-11-09 14:55): the list is re-validated by the harness
  (`shard_targets`); every input that can open the switch is read at BASE, the ledger included; the ledger changes
  only through a guarded absorb of trusted reports that the guard rebuilds (`check-shadow-ledger.py`,
  `trusted_report_run`); reports can only close the switch, and are absorbed by identity; an epoch archives its
  rows verbatim and HOLDs (Global Constraints, *Trust and provenance*; Tasks 7.2, 7.3, 8.1).
- §3 fail-closed rows: Task 5.3 (key, restore, usable), Task 4.1 (`GIT_DIR`), Tasks 2.2-3.2 (complete).
- §4 bound 6 / backlog #590: Tasks 2.2 (R4-F1), 3.1 (R4-F2, default-deny), 4.2 (live cases), 4.3 (closure).
- §8.1-8.6: Tasks 8.2/7.2, 5.2, 5.1-5.3, 2.2-3.2, 4.1-4.2, 7.2/7.3/8.1 respectively (§8.6's ledger clause: 7.3, 8.1).
- §6 (backlog #560 reuse) needs nothing here: the record carries blob ids (Task 4.1).
