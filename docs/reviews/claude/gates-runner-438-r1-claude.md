Reviewed head: a09cc99cc53f32007449ca4b6147c4199ea7f490

# gates-runner-438 r1 — Claude half (adversarial)

Subject: PR #465, backlog #438, `scripts/gates-for-pr.py` and its wiring, `git diff origin/master...HEAD` at the head above.

Claim under attack: *"A gate is skipped only if every input that can change its result is in its digest and
unchanged; no failure mode records a non-green run as green; and the gate set equals what CI's verify job runs."*

**Result: refuted, with a quoted false green on a real CI gate.** Every probe below was run, in a throwaway
`git clone` of the worktree (`scratchpad/g438clone`, so the ledger it wrote is the clone's own and the real one in
the main checkout was not touched). Nothing tracked in `wt-438` was edited except this file.

What was run:
- `python3 scripts/gates-for-pr.py --self-test` → `61/61 cases passed` (20 s).
- `--list` → 80 CI gates plus 4 mutation slices; 11 verify steps plus `schema-gates.yml` printed OUT OF SET.
- Two full real runs on the clone at this head (`--base` pointed at a ref equal to HEAD, which drops the mutation
  slices, and `--timeout 200`): run 1 `77 pass · 2 fail · 1 timeout`, 8m39s; run 2 `34 pass · 43 skipped · 2 fail ·
  1 timeout`, 7m49s.

---

## F1 — BLOCKER (Q4c, quoted false green). An imported module whose `.pyc` is warm is NOT in the input set

**Where:** the tracer drops every `open` whose path contains `__pycache__` (`scripts/gates-for-pr.py:242`), and
`place()` drops it again (`:295-296`). CPython's `SourceFileLoader` only **stats** a module's `.py` when a fresh
`.pyc` exists, and reads the `.pyc` instead. `stat` raises no audit event. So a helper module imported through a
warm cache is not an input at all: it is not in `files`, and editing its contents does not change the tree's name
list (`World.names`). `check-fixture-variation`, `fixture_git`, `subject_status`, `bounded_read`, `page_chrome`,
`coverage_verdict` and every `spec_from_file_location` load (`_pin`, `_merge_ready` in this very file) go
through that loader, and `scripts/__pycache__/` is populated on any machine that has run a guard once.

**Not fix-induced** (round 1).

**Input I ran — the real `check-guard-coverage self-test` step, which imports `subject_status`:**

```
# first recorded green was taken on a COLD cache: inputs = check-guard-coverage.py, m4_base_db.py, subject_status.py
# re-record with the cache warm (any re-run does this; --no-skip is the shortest way):
$ python3 scripts/gates-for-pr.py --base probebase --no-skip
PASS        check-guard-coverage self-test  (0.1s)
# ledger's newest entry for it: inputs.files == ['scripts/check-guard-coverage.py']   <- helpers gone

# break ONLY the imported helper, no other change:
$ python3 -c "p='scripts/subject_status.py'; t=open(p).read(); open(p,'w').write('raise SystemExit(1)\n'+t)"
$ python3 scripts/gates-for-pr.py --base probebase
SKIPPED     check-guard-coverage self-test  (last green 2aa0240055713a06)
summary: 2 pass · 1 skipped · 2 CI steps out of set (above)
runner rc=0
$ python3 scripts/check-guard-coverage.py --self-test ; echo $?
1
```

The battery exits **0** with the gate printed SKIPPED, and the real gate exits **1**. Same result with a synthetic
`probe_gate.py` importing `probe_helper.py` (helper flipped `OK = True` → `False`; SKIPPED, real rc=1).

Why the self-test did not see it: its fixtures never import a module through a warm cache, so no case has a
helper whose read the trace can miss. The shape is *the last green's input set is a function of cache state, not
of the code*: a cold run records the helper, a warm run does not, and `last_green` reads the NEWEST entry first.

**Fix direction (a hypothesis, not verified):** run each gate with `PYTHONPYCACHEPREFIX` set to an empty
per-run directory under the gate's temp `work/` (every import then compiles from source, so every `.py` is
OPENED and recorded), or map a `__pycache__/*.pyc` open back to its source with
`importlib.util.source_from_cache` and record that. The first is structural; the second has to be right about
every cache layout. Either way add the case this finding is: a gate that imports a helper with a WARM `.pyc`
has the helper in its input set, and editing the helper re-runs it.

## F2 — Major, FILE (or fold now, cheap). The runner's own gate FAILS under the runner, every time

`gates-for-pr self-test` passes standalone (`61/61`) and **fails when the battery runs it**, in both real runs:

```
FAIL        gates-for-pr self-test  rc=1 (20.8s) · not recorded · …/075-gates-for-pr-self-test.log
  [FAIL] ...a gate that shells out says it is never skipped, and why
  [FAIL] UNCHANGED inputs: a, b and the git-reading gate are not re-run      got ['a','b','g'] want []
  [FAIL] a green answers its own mode, and never another mode of the same script
  … 9 [FAIL] lines, ending in
FileNotFoundError: … gates-for-pr-st-…/repo/.claude/gates-for-pr/last-green.json
```

The inner fixture runs nest a second tracer under the outer one (the inner `sitecustomize` `_chain()`s into the
outer), and the inner runner never records a green. The main checkout's real ledger agrees: 67 entries, **none** for
`scripts/gates-for-pr.py`. Consequence: the battery can never exit 0 on this repo, so the exit code the row
promises carries no information and will be read past. Not a false green — a false red — but it removes the
runner's one machine-readable answer. Not fix-induced. Fix: the self-test should strip the runner's own site dir
from `PYTHONPATH` (or the runner should never trace itself), plus a case that runs the self-test under `run_gate`.

## F3 — Minor, FILE. The symbolic HEAD (the branch NAME) is not in a git-reading gate's digest

`World.core()` hashes `rev-parse HEAD` (a sha); `named()` resolves `HEAD` to that same sha. A gate that reads the
branch name (`git rev-parse --abbrev-ref HEAD`, `symbolic-ref`, `branch --show-current` — the last IS broad by
subcommand, but the broad digest is `for-each-ref`, which does not list the `HEAD` symref) is skipped across a
branch switch at the same commit. Ran: `probe_branch.py` exits 1 on branch `other`; PASS recorded on `okbranch`,
`git switch other` at the same commit → `SKIPPED probe branch`, real rc=1. **No current CI gate reads the branch
name** (grep over the 80 gate scripts: the one hit, `backfill-work-lines.py:2059`, is a string literal), so this is
latent. Fix: add `git symbolic-ref -q HEAD` to `core()`.

## F4 — Minor, FILE. Bounds and edges, none a quoted false green today

- **`PATH`, `GIT_DIR`, `GIT_WORK_TREE`, `GIT_CONFIG_GLOBAL`, `PYTHONDONTWRITEBYTECODE`, `TMPDIR`** are read by gate
  scripts (grep) and are outside `ENV_DIGESTED` (`:83`). The docstring states env as a bound; `GIT_DIR` /
  `GIT_WORK_TREE` are worth adding because they change which repository every git-reading gate sees.
- **A malformed ledger ENTRY** (e.g. `"inputs": {"files": 5}`) passes `read_ledger`'s shape check (`:545`) and
  raises `TypeError` inside `last_green` (`:559`), which `main` does not catch (`:743` catches Runtime/OS/
  Subprocess errors only): a traceback, not the promised *"unreadable; nothing is skipped"*. Fails closed (nothing
  is skipped), but not loudly in the repo's CANNOT RUN form.
- **The gate-set claim:** the derivation matches the `verify` job (80 python one-liners + `Roadmap test counts`
  NOT_LOCAL = 81 of the file's 82 `run: python3` lines; the 82nd is in `mutation-sweep`). CI's `mutation-sweep`
  job (the FULL sweep) is not printed in the OUT OF SET list; each slice's `source` string does say "CI runs them
  all". One OUT OF SET line naming the job would make the list complete.
- **Not probed to a result:** network (`socket.connect` is not an audited event the tracer hooks; grep found no
  real network use in the gate scripts — the hits were the word `requests`), `sqlite3.connect`, files opened by C
  extensions. The `--base` rewrite is digested correctly by design (`origin/<base>` is a NAMED revision →
  `cat-file --batch-check`), and a self-test case covers it; I did not re-run it live.
- **Ledger concurrency:** writes are `flock`ed and `os.replace`d; reads are unlocked but atomic. An entry from
  another branch is re-digested against the current world, so it answers only when the current inputs match —
  sound, given F1 fixed. A corrupt ledger file warns and skips nothing (case covered).

## Observation (not a finding)

Run 2 skipped 43 of 80 gates and saved 50 s of 8m39s: the never-skipped set (33 gates, mostly `writes … inside the
repository` and `runs bash`) and one 200 s+ suite dominate the wall time. The row's savings estimate is in
tokens per call, not seconds, so this is not a contradiction — but the skip saves less than its line count suggests.

---

| # | Severity | Disposition | Fix-induced |
|---|---|---|---|
| F1 | BLOCKER (quoted false green: SKIPPED, battery rc=0, real gate rc=1) | fix before merge | no |
| F2 | Major (false red: runner's own gate always FAILs under the runner) | FILE or fold | no |
| F3 | Minor (branch name not digested; latent, no current gate) | FILE | no |
| F4 | Minor (env bounds, malformed-entry traceback, mutation-sweep not listed) | FILE | no |

VERDICT: NOT CONVERGED
