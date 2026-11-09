# Observed-reach selection — implementation plan (backlog #586, prerequisite backlog #590)

> **Anchor:** `dev-speed-first` — **ADR:** none
> **Goal:** A change gets its verdict as fast as the evidence allows, with mutation coverage identical.

**Status:** 📝 DRAFT, written 2026-11-09 from the approved spec at `1a6004c1`. Phase 2: dual adversarial review
to convergence or the round cap (`docs/review-method.md` §0 Q4c) before any task is dispatched. Nothing is built.

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
- **No skip takes effect before slice 8**, and slice 8 does not merge until backlog #590 is ✅ and the shadow ledger
  holds 20 COMPLETE clean PRs (spec §7 Q4) with no latched miss.
- **Coverage is identical:** no mutant, case or pin is removed by any slice. Master pushes and the schedule keep
  running the WHOLE manifest.
- Python pinned `3.12` in every new CI job, with the `scripts/check-python-pin.py` step (it fails any job that does
  not pin). Node `'22'` where a job stages `node_modules/typescript`.
- `record-reads`, `sweep-select` and `shadow-compare` are NOT required checks; `mutation-sweep-complete` ignores them.
- Read-only tokens: `contents: read`, plus `actions: read` where a job lists caches or downloads artifacts.
- No tool call over 270 s while executing this plan: long CI waits are backgrounded and polled.
- Every number written into code comments, docs or the dashboard is marked MEASURED (with what was run) or INFERRED.

## Review Focus

1. **A trace that reads `complete` while a read was lost** — the parser meets a line shape the fixtures never had
   (a signal line `--- SIGCHLD`, `+++ exited`, a `<... resumed>` split across pids, a path with `\x` escapes). Expected:
   any line the tokenizer cannot place is `log did not parse`, never skipped. Test owner: Task 2.1.
2. **The cache restored from a different world** — a payload whose sha is not an ancestor of BASE, or whose key
   differs in one element. Expected: today's rule for every target, one log line naming the element. Owner: Task 5.3.
3. **A shard that runs a list other than `sweep-select`'s** after the switch (the job output truncated, empty, or
   absent because `sweep-select` was skipped). Expected: empty or absent output is FULL, never "nothing selected".
   Owner: Task 8.1.
4. **A shadow comparison counted clean on missing evidence** — an expired artifact, a `complete: false` verdict file,
   a base whose shard was budget-stopped. Expected: INCONCLUSIVE, never clean. Owner: Task 7.2.
5. **A recording job killed mid-way that still saves** (the `timeout-minutes` kill, a cancelled run, a target listed
   twice). Expected: no save. Owner: Task 4.3.

---

## Slice map

Each slice is ONE pull request off fresh `origin/master`, independently mergeable, with its own dual review.

| # | Slug / branch | What merges | Changes selection? | Merge gate beyond READY |
|---|---|---|---|---|
| 1 | `measure-strace-runner` / `build-586-s1-measure` | measurement workflow + driver + measured data + doc | no | the measurement ran on GitHub-hosted ubuntu |
| 2 | `strace-parse` / `build-586-s2-parse` | `scripts/strace_reads.py`: tokenizer, process tree, cwd model, path refusals | no (no caller) | — |
| 3 | `strace-classify` / `build-586-s3-classify` | default-deny classifier, record assembly, seed + cross-run checks | no (no caller) | allowlist ⊆ slice 1's measured set |
| 4 | `record-reads-job` / `build-586-s4-record` | `--record-reads` mode, `record-reads` job, cache save, live cases | no | first master `record-reads` run saved; backlog #590 ticked |
| 5 | `reach-select` / `build-586-s5-select` | `scripts/reach_select.py`: `Δ`, rule 3, validity | no (no caller) | — |
| 6 | `shadow-select` / `build-586-s6-shadow` | `sweep-select` job (report-only), `verdicts.jsonl`, artifacts | **no** — shards still self-select | the first PR run uploads `selection-*` |
| 7 | `shadow-compare` / `build-586-s7-compare` | comparator, `--mutant` replay, scheduled job, ledger | no | — |
| 8 | `observed-reach-switch` / `build-586-s8-switch` | shards take `sweep-select`'s list; post-switch detector | **YES** | backlog #590 ✅, ledger 20 complete clean PRs, no latched miss, Q1 fallback decided |

Slices 2 and 5 can be built in parallel after slice 1; slice 3 needs slice 1's data; slice 4 needs 3; slice 6
needs 4 and 5; slice 7 needs 6; slice 8 needs 7 plus the shadow period.

## Wiring a new self-tested script (W1-W8) — the PR #551 lesson, named per task

Every task that creates a script with `--self-test` does ALL of these in the same commit as the script, and names
them in its file list. CI went red on PR #551 for missing the declared-count and examined-keys pair.

- **W1** the script's docstring declares `python3 scripts/<name>.py --self-test  # N cases`, N copied from the
  suite's own `N/N self-test cases passed` line (never typed from memory).
- **W2** `scripts/mutations/<stem>.json`: one entry per guard clause the task adds (`name`, `file`, `edits`,
  `expect`), each run red with `python3 scripts/check-plan-code.py --mutate . --only scripts/<name>.py`.
- **W3** `scripts/mutations/expected_mutations.py`: `"scripts/<name>.py": <entry count>`; the TOTAL comment set from
  the real sum (`python3 scripts/check-plan-code.py --mutate . --only scripts/<name>.py` prints it), never by hand.
- **W4** `scripts/check-plan-code.py`: the path in the sorted list of the case
  `"the declared counts name every manifest that ships"` (in `_self_test_body`). This edits the harness, so the
  PR's own sweep runs ALL; expected.
- **W5** `scripts/check-selftest-counts.py`: the file name in `POPULATION`, with a dated comment.
- **W6** `scripts/check-fixture-variation.py`: `EXAMINED_KEYS["<name>.py"]` set to the keys
  `python3 scripts/check-fixture-variation.py scripts/<name>.py` prints, plus one written exemption per key a
  helper drives through a single call site. Every new pure function's parameters are varied in ≥ 2 cases.
- **W7** a caller: a `ci.yml` `verify` step `python3 scripts/<name>.py --self-test` (or, for a library imported by
  `check-plan-code.py`, `check-selftest-counts`' run, as `coverage_verdict.py` has), so
  `scripts/check-ratchet-contract.py` passes.
- **W8** if the script uses `fixture_git`, it enters `fixture_git.isolated()` in the exact shape
  `scripts/check-fixture-git-isolation.py` reads (PR #546 tripped it).

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

- [ ] **Step 2: verify.** Expected (MEASURED 2026-11-09 by this plan's author on the same file): 47 untraced
  targets; traced readers of a changed path exactly `check-canonical-source`, `check-dashboard-entry`,
  `check-features`.
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
  first line, `uname -r`, `ImageOS`, `ImageVersion`, `node -v`, `python3 -V`.
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
- Modify: `docs/backlog.md` (rows #586 and #590: the measured facts, one line each)
- Modify: `docs/dashboard-entries.md`

- [ ] **Step 1:** push the branch, open a DRAFT PR, wait for the run (background + poll in < 270 s chunks).
- [ ] **Step 2:** `gh run download <id> -D <tmp>`; `python3 scripts/strace-measure.py --merge <tmp>/* --out <json>`.
- [ ] **Step 3: the decision gate.** If the ptrace probe failed or strace is unavailable: write that in the doc,
  and slices 2-3 are REPLACED by slice 2F below; the rest of the plan is unchanged. Otherwise record, all MEASURED:
  the strace version line; the syscall-name union and per-name target counts; the ioctl tokens; AT_FDCWD decoration
  yes/no; each refusal-trigger hit by target; `TRACE_FACTOR` = the largest traced/plain wall-clock ratio over
  spawner targets, rounded UP to an integer; the targets whose traced and plain case counts differ; job durations.
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
- [ ] **Step 3: implement** the four functions above. Use real log lines from slice 1's artifacts as the source of
  every fixture line's exact shape (copy them, shorten paths).
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
  `cwd model disagrees` (only if slice 1 measured decoration); **backlog #590 R4-F1:** an `unlink*`/`rename*`/`rmdir`
  of a path outside the copy that no earlier call in the log created → `external path removed`.
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
  refused. The `realpath` cases build real links in a temp dir (`tempfile`), so they run on macOS and Linux.
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
    restricted to `MEASURED_SYSCALLS - DENIED_SYSCALLS`.
  - `ALLOWED_SYSCALLS = READ_ONLY | WRITES | PROCESS`; `ALLOWED_IOCTLS = MEASURED_IOCTLS - DENIED_IOCTLS`.
  - `classify(call: Call) -> tuple[str, str | None]` → (`"read"`/`"write"`/`"process"`/`"list"`, refusal or None).
    An `open*` with `O_CREAT|O_WRONLY|O_RDWR|O_TRUNC|O_TMPFILE` is a write; `mmap` with `MAP_SHARED` and
    `PROT_WRITE` on a file label is a write.

- [ ] **Step 1: failing cases:**
  - `"the allowlist is a subset of the measured set"`: `ALLOWED_SYSCALLS <= MEASURED_SYSCALLS` and
    `ALLOWED_IOCTLS <= MEASURED_IOCTLS` (backlog #590's FAILS IF, second clause).
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
  - `@dataclass(frozen=True) class Record: reads: frozenset[str]; probed: frozenset[str]; listed: frozenset[str];
     wrote: frozenset[str]; trace: str` (`trace` = `"complete"` or a `REASONS` member; `reads`/`probed`/`listed` are
     copy-relative and at or under a staged root, a root itself included; `wrote` is absolute or copy-relative and
     keeps every path).
  - `record_from_log(text: str, ctx: Ctx, strace_version: str) -> Record` — version ≠ `STRACE_VERSION` →
    `strace version`.
  - `EXEMPT_WRITES` — `/dev/null`, `/dev/zero`, `/dev/full`, `/dev/random`, `/dev/urandom`, `/dev/tty`,
    `/dev/pts/*`, everything under `/proc` and `/sys` (spec §2; `/dev/shm` NOT exempt).
  - `merge_seeds(a: Record, b: Record) -> Record` — equal `reads`/`probed`/`listed` → `a`; else `trace="seed-dependent reads"`.
  - `cross_run(records: dict[str, Record]) -> dict[str, Record]` — target T refused (`cross-run flow`) when its
    whole-trace reads/probes meet another target's `wrote` (exemptions dropped first), or its whole-trace `listed`
    holds an ancestor of such a path. The whole-trace sets are carried in `Record` as `all_named` and `all_listed`
    (absolute), added here.

- [ ] **Step 1: failing cases** (§8.4, §8.5): a read of a path another target wrote → refused; a listing of
  `docs/generated` when another wrote `docs/generated/flag` → refused, negative: a listing of a sibling directory;
  two targets each opening `/dev/null` `O_RDWR` → neither refused, while a `/dev/shm/x` write read later → refused;
  two seeds whose sets differ → `seed-dependent reads`, equal → kept; a version mismatch → `strace version`;
  `probed` holds a failed open, a failed `execve`, a `chdir`, a `statfs`, an `inotify_add_watch` (spec's
  definition); `readlink` → `reads` of the link; `execve` of a staged script → `reads`; `openat2` recorded; a
  failed `unlink` → `wrote`.
- [ ] **Steps 2-5:** red, implement, green, pins, mutate `--only`, commit.

**Pre-push (slice 3):** as slice 2. **Merge gate:** the subset case passes against the constants copied from the
merged slice 1 JSON (reviewer diffs them).

---

## Slice 4 — the `record-reads` job (spec §2 Record, Store; §8.5)

### Task 4.1: `--record-reads` mode in `check-plan-code.py`

**Files:**
- Modify: `scripts/check-plan-code.py` (top-level `import strace_reads`, which makes it a harness file by
  `harness_files`; the new mode; self-test cases; its own declared count and `EXPECTED_MUTATIONS` entry)
- Modify: `scripts/mutations/check-plan-code.json`, `scripts/mutations/expected_mutations.py`,
  `scripts/check-fixture-variation.py` (`EXAMINED_KEYS["check-plan-code.py"]` gains the new functions' keys)

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
    in ANOTHER fresh copy (`control_parts`). Not green by `control_is_green`, or case counts unequal →
    `trace="control red"` / `"case count differs"`. `runner` is injected so the self-test fakes strace.
  - `record_reads(root: pathlib.Path, out: pathlib.Path, runner=…) -> int` — every manifest target, sorted, both
    seeds, `merge_seeds`, then `cross_run`; writes `readsets.json`
    `{sha, key: {...}, targets: {t: {reads, probed, listed, wrote, trace, recorder, rc, cases, seeds, blobs}}, tally: {reason: n}}`
    where `blobs` maps each tracked path in `reads` to its git blob id. rc 0 when every target appears exactly once.
  - `validity_key(root: pathlib.Path) -> dict` — Python `major.minor.micro`, `harness_hash` (sha256 over the sorted
    `harness_files` blob ids), `recorder`, `STRACE_VERSION`, `node -v` minor, `ImageOS`, `ImageVersion`, blob ids
    of `DEPENDENCY_MANIFESTS`.
- [ ] **Step 1: failing cases:** the traced run is first and in a different copy from the plain run (the fake
  runner logs the cwd of each call); a red plain control refuses only its own target; unequal case counts refuse;
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
  `runs-on: ubuntu-latest`; `timeout-minutes:` from slice 1's measured duration × 1.5, rounded up (INFERRED until the
  first run, then re-set from it); steps: checkout `fetch-depth: 0`, setup-node 22, setup-python 3.12, Python pin,
  `npm ci`, strace install, `python3 scripts/strace_reads.py --live-cases`, `python3 scripts/check-plan-code.py
  --record-reads "$RUNNER_TEMP/readsets.json"` with `env: *shard-env`, then `actions/cache/save@v4` with key
  `readsets-<python>-<harness hash>-${{ github.sha }}`, `if: success()`. The step that records exits nonzero when a
  target is missing or doubled, so `success()` is the save condition; a cancelled or timed-out job never reaches it.
- `--live-cases`: runs, under `strace -f -yy`, a real child that calls `os.unshare(os.CLONE_FS)` and one that calls
  `setns` on `/proc/self/ns/mnt` (it may fail with EPERM; the call is still logged), and asserts each record's
  `trace` is the refusal (spec §8.4, r2 Codex F2: EXECUTED, not synthetic).

- [ ] **Step 1:** failing self-test case in `check-plan-code.py`: `sweep_limit_pin`-style read of `ci.yml` asserts
  `record-reads` has no `needs:` on `mutation-sweep`, never runs on `pull_request` or `batch/**`, and saves only
  under `if: success()` (spec §8.5). Adjacent negative: the `mutation-sweep` job keeps its triggers.
- [ ] **Steps 2-4:** implement, green, commit.

### Task 4.3: the first master run, measured; backlog #590 closed

**Files:** Modify `docs/reviews/measurements/2026-11-NN-strace-on-runner.md` (a "first record-reads run" section),
`docs/backlog.md` (#590 ✅ with the evidence; #586 progress), `.github/workflows/ci.yml` (`timeout-minutes` re-set
in a follow-up commit on the next docs batch if the measured duration differs).

- [ ] After merge, wait for the first master `record-reads` run (background poll). Record MEASURED: duration, the
  refusal tally by reason, how many targets got a complete read set, the save's key. This is the spec's "build step
  1 counts refusals by reason" (cross-run, seed-dependent, external path removed, …).
- [ ] Backlog #590 closes when: Task 3.1's subset and FS_IOC_SETFLAGS cases, Task 2.2's R4-F1 case and Task 4.2's
  live cases are green on master. Its FAILS IF are those cases' adjacent pairs.

**Pre-push (slice 4):** `python3 scripts/check-python-pin.py`; `python3 scripts/check-plan-code.py --self-test`;
`python3 scripts/strace_reads.py --self-test`; and the harness note: this PR's own sweep runs ALL.

---

## Slice 5 — the pure selector (spec §2 diff, comparison set, Use; §3; §8.2, §8.3)

### Task 5.1: `Δ` and the diff parser

**Files:**
- Create: `scripts/reach_select.py`, `scripts/mutations/reach_select.json`; W3-W7 files.

**Interfaces:**
- `parse_status(raw: str) -> list[tuple[str, str]] | None` — `git diff --name-status -z --no-renames` output;
  None for a non-NUL list, a C-quoted path, or any status outside `A`/`M`/`D`.
- `delta(r_base: list | None, base_head: list | None) -> frozenset[tuple[str, str]] | None` — the UNION of
  (status, path) pairs, never netted; None if either is None.
- [ ] **Failing cases:** a `T` in either list → None (FULL); a `D`+`A` rename arrives as two pairs; a PR that deletes
  a file master added over R..BASE keeps both pairs (Codex F1's `docs/activated`), negative: a path changed in only
  one list; an empty list → empty set.

### Task 5.2: rule 3 and the observed selection

**Interfaces:**
- `pick_reason(rec: dict, delta: frozenset, named_added_deleted: set[str]) -> str | None` — `"reads"`, `"probed"`,
  `"probed ancestor"`, `"listed ancestor"`, `"named"` or None (spec Use 3(a)-(c)).
- `observed_selection(event: str, changed: list[tuple[str, str]] | None, delta, sources: dict, harness: frozenset,
  readsets: dict | None, modules: dict | None, key_ok: list[str]) -> tuple[frozenset | None, list[str], dict[str, str]]`
  — (picks, log lines, would-skip `{target: why}`). Rules 1, 2, 4 come from calling today's `select_manifests` per
  path (imported from `check-plan-code.py` through `importlib`, never re-typed); rule 3 replaces rule 4 only for a
  target with a usable set. Log lines `  <t> <- <path> (observed)` / `(named: untraced)`; one `WOULD-SKIP:` line.
- [ ] **Failing cases (spec §8.2 and §8.3, each with its adjacent negative):** the committed spike fixture
  (`scripts/fixtures/observed-reach-spike-pr545.json`, spawners marked untraced) plus PR #545's diff selects
  EXACTLY today's spawner picks plus `check-canonical-source`, `check-dashboard-entry`, `check-features`, each with
  its reason; a traced spawner whose child read a changed path is picked and one whose children read none is not;
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
- [ ] **Failing cases (§8.3):** missing, red, short-count, wrong-key (one case per key element: strace version,
  Node minor, runner image, a `package-lock.json` blob changed over R..BASE), wrong-recorder and unvalidated sets
  each give today's rule; an unparseable cache → today's rule for all; each with an equal-key negative.
- [ ] **Steps (each of 5.1-5.3):** red, implement, green, W1-W7, mutate `--only scripts/reach_select.py`, commit.

**Pre-push (slice 5):** `python3 scripts/reach_select.py --self-test`;
`python3 scripts/check-plan-code.py --mutate . --only scripts/reach_select.py`.

---

## Slice 6 — shadow: `sweep-select` reports, nothing skips (spec §2 Resolve, shadow data; §7 Q1, Q4)

### Task 6.1: `--select-only` and `--verdicts` in `check-plan-code.py`

**Interfaces:**
- `--select-only OUT --readsets FILE --r-base FILE --base-head FILE` → writes the selection artifact
  `{pr, head, base, r, key_check, today: [...], observed: [...], would_skip: {t: why}, picks: {t: rule},
  q1_probe_delta}` and prints the log lines. `q1_probe_delta` = picks on PR #543's diff (its two commits pinned as
  constants) with `probed` minus picks with `probed`'s stat/access entries removed (spec §2 Q1 fallback; > 5 →
  report `Q1 FALLBACK: revert 3(c) to option A`).
- `--verdicts FILE` → one JSON line per mutant run `{target, mutant, seed, verdict}` (`killed`, `survived`,
  `cannot-run`, `timeout`), one per control `{target, control: green|red}`, final `{complete: bool}` (false when
  budget-stopped or a control did not run). Written by `run_mutations`; no verdict changes.
- [ ] **Failing cases:** `today` in the artifact equals `select_manifests`' result on the same inputs (the shadow
  invariant: nothing the shard runs changes); a budget-stopped run writes `complete: false`; every mutant has
  exactly one line; adjacent: a complete run writes `complete: true`.

### Task 6.2: the jobs

**Files:** Modify `.github/workflows/ci.yml`.
- `sweep-select`: `pull_request` only; NOT in `mutation-sweep`'s `needs:` in this slice; lists caches with
  `gh api repos/{owner}/{repo}/actions/caches?key=readsets-<python>-<hash>-` (`actions: read`), keeps ancestors of
  BASE (`git merge-base --is-ancestor`), restores the nearest by exact key, runs `--select-only`, uploads
  `selection-<run_id>-<run_attempt>` (`retention-days: 90`, `if: always()`). A miss or API failure is logged and the
  artifact says `full: <why>`.
- `mutation-sweep`: adds `--verdicts "$RUNNER_TEMP/verdicts.jsonl"` and an upload of
  `verdicts-<run_id>-<run_attempt>-<shard>` (`if: always()`, 90 days) on every event; logs its `ImageVersion`.
- [ ] **Failing case:** a `ci.yml` read in `check-plan-code.py`'s self-test asserts `mutation-sweep` does not consume
  `sweep-select`'s output in this slice (the shadow invariant, made mechanical); slice 8 flips this case.

**Pre-push (slice 6):** `python3 scripts/check-python-pin.py`; `python3 scripts/check-plan-code.py --self-test`.
**Merge gate:** the PR's own run uploads one `selection-*` and every shard's `verdicts-*`.

---

## Slice 7 — the comparator (spec §2 "A MISS, precisely"; §8.6)

### Task 7.1: `--mutant` replay

**Interfaces:** `check-plan-code.py --mutate . --only <target> --mutant <name> --seeds <s>` runs ONE manifest entry
(matched by its `name`) in a fresh staged tree. Failing cases: an unknown name → CANNOT RUN rc 2; a known name runs
one mutant only.

### Task 7.2: `scripts/shadow-compare.py` and its job

**Files:** Create `scripts/shadow-compare.py`, `scripts/mutations/shadow-compare.json`; W1-W8 files;
`.github/workflows/ci.yml` (job `shadow-compare`, `schedule` daily + `workflow_dispatch`, `contents: read`,
`actions: read`).

**Interfaces:**
- `SHADOW_START: str` — the date slice 6 merged.
- `pushes(pr: dict, runs: list[dict]) -> list[dict]` — every push's PR run with its own BASE.
- `compare_push(pr_verdicts: list | None, base_verdicts: list | None, would_skip: set[str]) -> tuple[str, list]` —
  `"clean"`, `"difference"` (with the differing (target, mutant, seed)), `"inconclusive"` (missing, expired,
  `complete: false`, a CANNOT RUN control, a cancelled run), `"pending"` (either sweep not finished).
- `replay(diff, run_one) -> str` — 3 runs per side under EACH `RECORD_SEEDS` value through Task 7.1's option, in
  fresh trees: stable-and-different under any seed → `"miss"`; anything else → `"unreproduced difference"`.
- `decide_pr(push_results: list[str]) -> str` — any `miss` LATCHES `"miss"`; any pending → `"pending"`; any
  inconclusive or unreproduced → `"inconclusive"`; all clean and at least one would-skip target → `"clean"`.
- `ledger(previous: dict, decided: dict) -> dict` — a PR decided in `previous` keeps its decision.
- [ ] **Failing cases (§8.6, each adjacent):** a cancelled PR run, a missing base artifact, a red control →
  inconclusive; a pending PR not counted and decided by a later run; a miss at a non-final push then a clean final
  push → miss; a flip on re-run → inconclusive; stable on both trees under one seed → miss; reproduces under only
  one of the two seeds → miss; reproduces under neither → unreproduced, listed, never clean; a PR with no would-skip
  target → not a sample; an expired input with no decided row → inconclusive; a decided row survives its input's
  expiry.
- [ ] **Steps:** red, implement with `gh` injected, green, W1-W8, mutate `--only scripts/shadow-compare.py`, commit.

**Pre-push (slice 7):** `python3 scripts/shadow-compare.py --self-test`;
`python3 scripts/check-plan-code.py --mutate . --only scripts/shadow-compare.py`; `python3 scripts/check-python-pin.py`.

---

## Slice 8 — the switch (LAST; spec §7 Q4, §8.1)

**Do not start the build until ALL hold, each quoted with its evidence in the PR body:** backlog #590 ✅ (its row's
evidence); the newest `shadow-ledger-*` lists ≥ 20 COMPLETE clean PRs, consecutive from `SHADOW_START`, and 0 latched
misses; the `unreproduced difference` count is stated; the Q1 probe delta on PR #543's diff is ≤ 5, or Task 8.0 has
reverted 3(c) to option A. A latched miss stops this slice and goes to the owner (spec §7 Q5: revisit).

### Task 8.0 (only if `q1_probe_delta` > 5): rule 3(c) reverts to option A in `reach_select.py`, with the fixture
case updated. A separate commit, reviewed on its own.

### Task 8.1: shards run `sweep-select`'s list

**Files:** Modify `.github/workflows/ci.yml` (`mutation-sweep` `needs: sweep-select`; passes
`needs.sweep-select.outputs.targets`), `scripts/check-plan-code.py` (`--targets FILE`: the list to shard; an empty,
absent or unparseable file is FULL with the reason), the slice-6 invariant case flipped.
- [ ] **Failing cases:** a shard given a list slices it with `shard_slice` and runs nothing else; an absent output
  (`sweep-select` skipped or failed) → FULL; a `full: <why>` output → FULL; adjacent: a valid list is honoured.
  `SKIPPED:` replaces `WOULD-SKIP:` in the log.

### Task 8.2: the post-switch detector (§8.1)

**Files:** Modify `scripts/shadow-compare.py` (`--post-switch`), its manifest and pins.
- `post_switch(red_targets: set[str], merged: list[dict]) -> list[str]` — the PRs merged since the last green full
  sweep whose `selection-*` `SKIPPED` set meets the red targets (red targets read from each shard's `verdicts-*`;
  the PR from the squash subject's `(#N)`). A non-empty result comments on the open `sweep-red` issue, naming them.
- [ ] **Failing cases:** a red target in a merged PR's SKIPPED set → reported; a red target skipped by no PR → not;
  a missing selection artifact → reported as NOT CHECKED, never silent.

**Pre-push (slice 8):** all slice-6 and slice-7 lines.

---

## Self-review notes (coverage of the spec)

- §2 Record, cold traced run first, two fixed seeds, env reproduction, timeout: Tasks 4.1-4.2. Recorder, classes,
  INCOMPLETE triggers, normalisation: Tasks 2.1-3.2. Record fields: Task 3.2/4.1. Store/save condition: Task 4.2.
  Validity key: Task 4.1/5.3. Resolve: Task 6.2 (report-only), 8.1 (effective). Diff + `Δ` + Use: Tasks 5.1-5.2.
  Q1 fallback: Task 6.1/8.0. Shadow data + comparator + MISS: Tasks 6.1-7.2.
- §3 fail-closed rows: Task 5.3 (key, restore, usable), Task 4.1 (`GIT_DIR`), Tasks 2.2-3.2 (complete).
- §4 bound 6 / backlog #590: Tasks 2.2 (R4-F1), 3.1 (R4-F2, default-deny), 4.2 (live cases), 4.3 (closure).
- §8.1-8.6: Tasks 8.2/7.2, 5.2, 5.1-5.3, 2.2-3.2, 4.1-4.2, 7.2 respectively.
- §6 (backlog #560 reuse) needs nothing here: the record carries blob ids (Task 4.1).
