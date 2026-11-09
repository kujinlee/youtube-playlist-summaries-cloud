Reviewed head: dcf8bb205b04dc215c76843f21c458ce2c186689

# Design review, round 1 of the REDESIGN — observed-reach spec (backlog #586) — Claude half

Subject: `docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md` at `dcf8bb20`.
Mandate: REFUTE the mechanism (the dedicated `record-reads` job and the `strace -f` recorder). The owner's
six decisions (§7) are not re-litigated; each finding below is a place where the mechanism AS WRITTEN cannot
deliver them, or a hole the mechanism ADDS beyond the bound the owner accepted (a mutant reads a file its
unmutated control never opened, §4.1).

Independence: I did not read the concurrent Codex half (`docs/reviews/codex/spec-586-redesign-r1-codex.md`).

## Evidence base, and what I could NOT check

- **strace is not installed here** (`which strace` exits 1; macOS). No suite was traced. Every claim about
  strace's own behaviour below is INFERRED from its documented options and marked so; build step 1 is where
  each one becomes MEASURED.
- Harness behaviour is read from `scripts/check-plan-code.py` at this head (quoted by symbol).
- Repository facts were MEASURED by grep / `git ls-files` / `gh run` (read-only), each cited.
- Not checked: the spike document's figures, Node 22's libuv io_uring default, whether strace `-y` decorates
  `AT_FDCWD` with the cwd on the runner's strace version, and glibc's choice of `clone3` on the runner image.

## Findings

### F1 — HIGH — §3 staleness row + §2 Use 3(a): a master ADD or DELETE over R..BASE of a path in `probed` or `reads` neither stales the set nor picks the target

**Where.** "The diff" (§2) defines the changed list as `origin/$BASE_REF...HEAD`, i.e. BASE..HEAD, and Use 3(a)
tests only that list against `reads`/`probed`. §3's staleness row voids a set only when a path in `reads` or
`probed` was **MODIFIED** over R..BASE. Additions and deletions over R..HEAD reach only 3(b) (under a listed
directory) and 3(c) (literally named in the source).

**Constructed miss (not the accepted bound — the CONTROL's reads change).** At R, target T's suite does
`(root / "docs/flags" / f"{mode}.on").exists()` with `mode` computed, `docs/flags/` absent, and on true it also
reads `docs/strict-rules.md`. strace records `docs/flags/strict.on` in `probed` (failed `newfstatat`); no
listing of `docs/flags` happens (it does not exist), the name is not literal in the source. Master adds
`docs/flags/strict.on` over R..BASE. A PR then modifies `docs/strict-rules.md`.
- staleness row: no path in `reads`/`probed` was MODIFIED → set usable;
- 3(a): `docs/strict-rules.md` ∉ reads ∪ probed (R's control never read it);
- 3(b): `docs/flags` not in `listed`; 3(c): not literal →
- **T is skipped, while its plain control at BASE/HEAD reads the changed file.**

The deletion twin: T reads `docs/a.md` if present else `docs/b.md`; master deletes `a.md` over R..BASE; a PR
modifies `b.md` → skipped. This is round 1 Codex F1's class; the r1 fix closed it only for literal names and
listed directories. strace now records the probe natively, so the fix is cheap.

**Fix.** Either (a) 3(a) tests `reads ∪ probed` against A and D over **R..HEAD** (M stays BASE..HEAD plus the
staleness row), or (b) the staleness row reads "added, modified or deleted". Add to §8.3: a computed-name probe
(not literal, not under a listed dir) whose path master adds over R..BASE PICKS the target; adjacent negative,
an unprobed addition in the same directory does not.

### F2 — HIGH — §2 normalisation: a symlink OUTSIDE the staged tree that points INTO it silently drops reads (not INCOMPLETE)

**Evidence (MEASURED, this repo).** `scripts/check-review-recorded.py` self-test, at the symbol `_cli` fixture:

```python
os.symlink(_real_root / "scripts", pathlib.Path(_cli, "scripts"))
...
os.symlink(_real_root / "docs" / "superpowers", pathlib.Path(_cli, "docs", "superpowers"))
...
globals()["ROOT"] = pathlib.Path(_cli)
```

and the `finally:` then `shutil.rmtree(_cli, ...)`. `_cli` is a temp directory; `_real_root` is the staged tree.
Every read the suite then makes as `<tmp>/_cli/scripts/...` or `<tmp>/_cli/docs/superpowers/...` is logged by
strace under the TEMP path. §2 resolves "`..` segments and symlinks inside the staged tree" only; the link here
lives outside it, `symlinkat` is not in the traced list, and the log is parsed after `rmtree`, so a post-hoc
`realpath` returns the lexical temp path, which is OUTSIDE every staged root → **dropped as not-a-repo-read,
with the trace still `complete`.** A PR editing a `docs/superpowers/` file this suite reads through the link is
not a pick. `scripts/check-doc-citations.py` and `scripts/begin-plan.py` also create symlinks in their fixtures
(grep `symlink_to|os.symlink`).

**Fix.** (1) For every SUCCESSFUL open, take the path from strace `-y`'s decoration of the RETURNED fd
(`= 3</real/path>`), which the kernel resolved at the time, symlinks included; reconstruction is then needed
only for failed opens and path-only calls. (2) Trace `symlink`/`symlinkat`/`link`/`linkat`/`rename*` and keep a
table of links created during the trace; a failed probe or `stat` whose path traverses a created link resolves
through it, and one that traverses a link the recorder cannot resolve makes the trace INCOMPLETE. (3) §8.4
gains a case: a read through a temp-dir symlink into the staged tree, logged after the link is deleted,
resolves to its staged-tree name.

### F3 — HIGH — §8.1 / §8.6 / Q4: shadow mode's comparison has no data source; every sample is INCONCLUSIVE by the spec's own rule

**Evidence (MEASURED).** `grep -nE "upload-artifact|download-artifact" .github/workflows/*.yml` → **no hits**.
`--evidence` is RETIRED in `check-plan-code.py` `main` (`retired = [... ("--evidence", a.evidence) ...]`). §8.1
reads "red targets (read from each shard's structured results artifact)" and "its selection from that run's
artifact"; §8.6 makes "a missing artifact" INCONCLUSIVE. §2 never specifies that artifact as something the
build adds, nor its retention, nor the script that compares. As written, every shadow PR is INCONCLUSIVE, Q4's
20 complete PRs never accrue, and the post-switch detector (§8.1, second half) is blind. This fails CLOSED (the
switch never happens) — so it is not a soundness hole, but the owner's Q4 decision cannot be delivered.

**Fix.** Add to §2 a named component: every `mutation-sweep` shard (PR and master) uploads a per-mutant verdict
file (`{target, mutant name, verdict, seed}`) plus, on a PR, `sweep-select`'s output (picks, WOULD-SKIP with
reasons, R, BASE); retention ≥ the evaluation delay; the comparison is a named mode of a named script run by the
scheduled job. §8.6 cases then have a real input to go INCONCLUSIVE on.

### F4 — MEDIUM — §2 recorder: the syscall list is enumerated, and it is incomplete

INFERRED from strace's and glibc's documented behaviour (not run: no strace here).
- **`clone3` is missing** from the parentage list (`execve, clone, fork, vfork`). glibc ≥ 2.34 creates threads
  with `clone3`, and recent glibc's `posix_spawn` uses it too; Ubuntu 24.04 ships glibc 2.39. A parser that
  learns a child's parent and inherited cwd only from the listed calls meets PIDs of unknown parentage — either
  every spawner goes INCOMPLETE (the saving collapses, silently) or the cwd defaults (wrong resolution).
  Threads created with `CLONE_FS` SHARE one cwd: a `chdir` in one thread moves all of them, which a per-TID
  copy-on-clone model gets wrong.
- **`openat2`** (a newer open), **`readlink`/`readlinkat`**, and **`execve`'s own path** (a staged script or a
  PATH-search probe — `execve` is traced but only for parentage) are not counted as reads/probes.
- `unlink`/`rename`/`mkdir`/`link` failing with ENOENT/EEXIST are existence probes too.
- `io_uring` (§4.2): an open submitted through `io_uring` is invisible, but `io_uring_setup` itself is a syscall.

**Fix.** Trace by strace CLASS, not by list: `-e trace=%file,%process,getdents64,fchdir,io_uring_setup` — `%file`
is every syscall taking a filename (covers `openat2`, `statx`, `readlinkat`, `execve`, `symlinkat`, `unlink*`, …)
and `%process` covers `clone3`. Count every path a `%file` call names as `probed` at least. An
`io_uring_setup` in the trace makes it INCOMPLETE — this turns §4.2's "INFERRED rare" into a detected refusal.
Model `CLONE_FS`. Build step 1 then MEASURES the list instead of confirming a guessed one. If strace `-y`
decorates `AT_FDCWD` with the cwd (INFERRED; verify in step 1), use it as the authority for `*at` calls and
keep cwd tracking only as a cross-check whose disagreement is INCOMPLETE.

### F5 — MEDIUM — §2 Record / §4.3: one tree, plain-before-traced order — warm state and cross-suite flows can shrink a read set below what a shard's control reads

**Evidence.** In a shard (`mutate_delivered`), the harness runs EVERY target's control first, then every
mutant of every target in one tree `d`, then the re-controls. The recording job instead runs, per target in
sorted order, the plain control and THEN the traced run, all 91 in one tree. Two consequences the bound does
not cover:
1. **Warm path.** Whatever T's own plain control leaves (in the tree or `CHILD_HOME`, which is `d/.home`, shared
   by all suites) the traced run may consume instead of re-reading inputs. A shard's CONTROL runs cold relative
   to T's own state. If a warm run reads fewer repo files, the traced set under-reports the control's. (Repo
   example of on-disk state: `recall-llm.py`'s `CACHE_DIR = ROOT / ".claude" / "recall-cache"`; I did not
   establish whether its self-test uses that path or a temp root — INFERRED risk, not a shown instance.)
2. **Laundered dependency.** Suite U reads repo file F and writes derived file D outside the staged roots (e.g.
   under `.home`); suite T reads D. T's recorded set never contains F, whatever the order; a PR changing F
   changes T's result whenever U ran first in the shard. §4.3 frames ordering as "changes a later suite's
   reads", not as a content flow.

**Fix.** Run the TRACED run first on T (cold), the plain control second, and compare counts as now. Record
writes (open flags `O_CREAT|O_WRONLY|O_RDWR|O_TRUNC`, `rename*`, `unlink*`) per run; a target whose traced run
reads a path that ANOTHER target's traced run wrote is INCOMPLETE (or inherits the writer's reads, transitively).
Both are cheap under strace and turn an unmeasured bound into a refusal.

### F6 — MEDIUM — §2 Record: one recording per target on a push is one draw of a nondeterministic read set

A master push is unseeded, so `mutation_env(tree, None)` leaves `PYTHONHASHSEED` as inherited (random per
process when unset). The harness's own backlog #506 comment (above `SEED_MAX`) MEASURED that hash order changes
outcomes (dropping `sorted()` survived under ~1 in 120 seeds). Any `for p in <set>: ... break` or `any(...)` over
paths opens a seed-dependent subset. The PR's control runs under a different random seed and can open a file
the one recording did not. This is NOT the accepted bound (it is the control, unmutated). "Read sets from several
seeds are united" helps only on the schedule's two seeds.

**Fix.** Record every push under two fixed, distinct seeds (the job is off the critical path); a target whose
two read sets differ is either united (cheap) or refused as `nondeterministic reads` (strict). §8.5 gains the
case.

### F7 — MEDIUM — §2 Record / §4.4: the recording job's environment is not the shard's

`child_env` starts from `dict(os.environ)`. The `mutation-sweep` step sets `SWEEP_JOB_START`, `SHARD_INDEX`,
`SHARD_TOTAL`, `EVENT`, `BASE_REF`, `RUN_ID` and `SWEEP_TIMEOUT_MINUTES` (ci.yml, `mutation-sweep` job); a new
`record-reads` job will have whatever its own steps set. §4.4 names only the `GITHUB_*` event difference.
Targets that read CI env today (grep): `batch-ci`, `check-merge-ready`, `check-python-pin`
(`GITHUB_ACTIONS`), `check-review-recorded`, `ci-durations`, `gates-for-pr`, `page_markup`. Also unkeyed: the
runner image (glibc, git, strace versions) and Node's floating `'22'` minor — only Python is in the key.

**Fix.** One YAML anchor supplies the step env to both jobs (the recorder sets `EVENT=pull_request` and an empty
`BASE_REF`-like value the way a PR shard would, or the spec states why push values are the right stand-in); the
payload records the env KEY set and `ImageOS`/`ImageVersion` + `strace -V`, and `sweep-select` validates them like
the harness hash.

### F8 — MEDIUM — §2 Use 3(b): "lies under a directory in its `listed`" is undefined, and the saving depends on the reading

Python's `FileFinder` lists every `sys.path` directory (`getdents64` of the staged `scripts/`) for every Python
suite. Read RECURSIVELY, any added path anywhere below `scripts/` — including `scripts/mutations/<x>.json` — picks
every traced target; read as DIRECT CHILD, a new file inside an existing unlisted subdirectory is missed only if
that subdirectory was never listed (sound), but a new subdirectory is caught via its parent. §5's "adding any
file under `scripts/` picks all 43" suggests the scorer used one reading; the spec does not say which.

**Fix.** Define it: an A/D path P picks T when the DEEPEST ancestor of P that existed at R is in T's `listed`.
That is sound (listing a directory reveals exactly its own entries) and no wider than needed. Case both shapes
in §8.3.

### F9 — LOW — §2 `.git` rule: the adjacent negatives are missing, and the "must count" side is empty under this harness

`.github/workflows` and `.githooks` are staged roots whose first component begins with `.git`; §8.4 cases only a
temp repository's `.git`. A prefix/substring implementation would drop both and pass every listed case. Answer
to the brief's question: `stage_tree` copies `HARNESS_TREE` only, so the staged tree has no `.git`; no suite in a
mutation run can read the real repository's metadata (barring an inherited `GIT_DIR`), so no `.git` read must
count. **Fix:** add `.github/workflows/ci.yml` and `.githooks/pre-push` reads as negatives that DO count; state
the empty "must count" set, and refuse (INCOMPLETE) if `GIT_DIR`/`GIT_WORK_TREE` is set in the env.

### F10 — LOW — §2 Cost: the traced run's timeout is unspecified

The plain control runs under the flat `SUITE_TIMEOUT = 120`. At the spec's own 2-5x, the slowest (55 s, a
spawner) becomes 110-275 s; under the same limit it times out, is refused, and falls back silently — and the
spawners are where strace's saving lives (§5). **Fix:** a scaled traced-run limit, and the payload's refusal
reasons tallied in the job log so shadow mode reports the fallback rate by cause.

### F11 — LOW — §2 normalisation: `/proc/self/fd/N` needs an fd table the traced calls do not give

Resolving `fd/N` requires `dup`/`dup2`/`dup3`/`fcntl(F_DUPFD)`/`close` and `O_CLOEXEC` across `execve`, none
traced. **Fix:** resolve only through the returned fd's `-y` decoration on the same line; any other `/proc/*/fd`
or `/proc/*/cwd` path is INCOMPLETE.

### F12 — LOW — §8.1 / §8.6 shadow-mode definitions

- §8.1 compares "at any push"; §8.6 counts "its final push". Each push has its own BASE and base sweep; pick one
  (final push).
- A differing verdict from a seed-flaky mutant (#506's class) counts as a miss and "stops the switch" with no
  reproduction step; add: re-run that mutant on both trees before counting.
- Reaching 20: MEASURED, 2 of the last 3 master `push` runs of `ci.yml` concluded `failure` (`42662571317` on
  `c3ef94d7`, `42634452353` on `4a6f1577`, the latter in `mutation-sweep (16)`). A base whose shard was
  budget-stopped lacks per-mutant verdicts and is INCONCLUSIVE, so Q4's "about 6 days" (from audit-hook-era
  figures) is optimistic for a further reason the spec does not give. Cause of the two reds not established.

### F13 — LOW — §2 Use 3(c): "named literally in the target's source" drops today's import closure

Today's rule picks namers through `_importers` (a target that imports a module naming the path). 3(c) says "the
target's source". State whether 3(c) includes the closure, and whether §5's option-B figures were scored with
it; if not, a target whose helper module names an added path the control did not probe loses a pick today's rule
gives (within the accepted bound only if the helper's branch is mutant-only).

## Fail-closed paths (brief §4) — checked

Missing / unvalidated cache → today's selection for all; partial job → not saved; harness/Python/recorder
mismatch → refused; strace missing or ptrace denied → per-target refusal → today's rule. Each is today's
selection or more, as written. The gaps are the silent-drop cases above (F2, F4, F5, F11), where the trace is
marked `complete` although reads were lost, plus the unkeyed environment (F7).

## Verdict

**NOT CONVERGED** — three HIGH (F1 a constructed miss of the control's own reads; F2 a measured silent drop
in this repo's suites; F3 shadow mode has no data source), five MEDIUM.

VERDICT: NOT CONVERGED
