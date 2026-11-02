# Round 1 — hook-launcher — claude

Subject: PR #419, branch `hook-launcher`, head `f6d01b94`, diff `git diff origin/master...HEAD`.
Mandate: refute. Every experiment ran in fresh fixtures or clones under
`scratchpad/r1rev/` with an environment built from nothing
(`env -i PATH=… HOME=… TMPDIR=… LANG=C GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1`).
Nothing in the worktree was edited, and no state-changing git ran there. The only commands
run inside the worktree were read-only: the push-gate simulation in §3, which runs
`git remote`/`symbolic-ref`/`rev-parse`, and `check-hook-commands.py`. `git status --short`
was empty afterwards.

Scripts that reproduce every result:
- `scratchpad/r1rev/exp1.sh`: I/O, exit codes and project-dir variants
- `exp3.sh`: the push gate
- `exp5.sh`: every hook run from the root and from `scripts/`
- `drive.py` / `drive2.py`: mutants

## Blocking

None.

## Major

### M1 — The guard cannot see the hook's stdout or stderr. A launcher that silently discards the push gate's deny decision passes 63/63.

`scripts/check-run-hook.py:61` (`PROBE`) writes only `BASH_SOURCE`, `$#` and stdin to marker
files, then exits 7. Nothing in the suite asserts that the hook's **stdout** or **stderr**
reaches the harness. The IO cases (`:294`, `:310-311`) cover stdin and argc only. But stdout is
the channel `block-default-branch-push.sh` uses to deny a push: `deny()` prints
`{"hookSpecificOutput":{…"permissionDecision":"deny"…}}` and exits **0**. Stderr is the channel
for every exit-2 block message.

I applied three mutants of `.claude/hooks/run-hook.sh:65` to a copy and re-ran **every** world
(`drive.py`):

```
control red: []
X-stdout-dropped     (exec bash "$hook" >/dev/null)  -> []
X-stderr-dropped     (exec bash "$hook" 2>/dev/null) -> []
X-stderr-into-stdout (exec bash "$hook" 2>&1)        -> []
```

All three survive. The first one makes the push gate fail **open** with no other symptom, and
nothing in this PR or in `check-hook-commands.py` would notice. The third one corrupts every JSON
decision whenever a hook writes anything to stderr.

**The launcher as shipped is correct.** I verified that directly (§1), so this is a hole in
the guard, not a live defect. But `--self-test` is the one falsifier for the launcher's
contract, and the architecture review's §4 asked only for "stdin not forwarded". That copied the
review's blind spot into the guard.

**Fix:**
- Have the probe print distinctive bytes on both stdout and stderr, and assert them byte for
  byte in the IO case.
- Add the stdout-dropped and stderr-dropped mutants to `MUTANTS`.

Asserting on stderr requires separating the launcher's own stderr. That is easy here, because
the launcher writes nothing on a successful run.

## Minor

### m1 — Stale counts in the backlog row and the dashboard entry, written before the master merge

`docs/backlog.md:346` and `docs/dashboard-entries.md:17874` both say "`check-hook-commands.py`
… 32 cases, 20 mutations". At HEAD the real figures are higher:

```
$ python3 scripts/check-hook-commands.py --self-test | tail -1
45/45 self-test cases passed
$ python3 -c "import json;print(len(json.load(open('scripts/mutations/check-hook-commands.json'))))"
34
```

The docstring says 45 cases, and `EXPECTED_MUTATIONS` says 34. The figure 32 is the docstring
at `ff8baa9f`. The merge of #414 (`f6d01b94`) updated the manifest and the docstring, but not
these two prose copies. The PR body's "34" is correct.

### m2 — The PR body's problem statement misdescribes the old behaviour

The body says: "registered as `bash .claude/hooks/<name>.sh`, a hook silently runs **main's
copy, or nothing**, once a session `cd`s into a subdirectory or a linked worktree."

Under the old relative form, a session at a linked worktree's **root** ran the **worktree's**
copy. The architecture review's §1 row W2 says "Today: worktree's hook (gate 2)". Below a root,
nothing ran (127). "Main's copy" describes r1's rejected design (`$CLAUDE_PROJECT_DIR` alone),
not the state this PR replaces.

### m3 — "It can only run once this is merged and loaded" is false (PR body, Evidence)

The live falsifier can run before merge. Claude Code loads `settings.json` and the launcher
from `CLAUDE_PROJECT_DIR`, the checkout the session was **launched** in. So a `claude -p`
session launched in a fresh clone of this branch exercises exactly this settings file and
launcher. The clone needs `origin` pointed at a local bare repo, so a fail-open push lands
nowhere real. Then `cd scripts` and attempt `git push origin HEAD:master`.

That is how the architecture review ran its own live check (§3, "`claude -p`, temp repo"). The
backlog row says something different again: "the implementing agent could not run it". The row
and the body give two different reasons why the falsifier was not run, and neither holds.

### m4 — "63 of 63 CI guard steps pass locally" (PR body) matches no count I can find

It is the same number as the self-test's 63 cases. `ci.yml` has 89 `- name:` steps, and 73
`run: python3 scripts/…` lines. Either name the population, or drop the line.

### m5 — W10 depends on the host

The cwd for W10 ("outside any checkout") is `tempfile.TemporaryDirectory()` under the
inherited `TMPDIR`. If any ancestor of `TMPDIR` holds a `.git`, the walk stops there and the
case goes red. That is a false LAUNCHER failure, not an ambient pass. Reproduced by planting
`.git` at the scratch root (`drive2.py`):

```
with X/.git | W10 cwd outside any checkout: the project dir's hook | got 1 want 7
```

It is harmless on CI's `/tmp` and on this Mac's `/var/folders/…` default, but it would read as
a launcher defect on a host whose `TMPDIR` lives inside a repo. Either assert the precondition
and report CANNOT RUN when no ancestor of the world root is free of `.git`, or state the bound
in the docstring.

### m6 — A concrete instance of L4 in this very repo

`find <main> -name .git` turns up `.remember/.git`, a nested repo. A session whose cwd is
`.remember/` runs **every** hook NOT RUN, including the push gate. That is equal to the old form
(127 there), and L4 states it in general. Naming the concrete case in L4 would stop someone from
rediscovering it.

## Verified (attempted refutation that failed)

### §1. Exit code, stdout, stderr and stdin propagate unchanged (`exp1.sh`)

Each probe ran through the exact registered command, `/bin/sh -c 'bash
"${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/run-hook.sh <name>'`, in a fixture with a main
checkout and a `git worktree add` worktree:

```
== exit 2, main/scripts, PD=main   rc=2 out=out-main err=err-main
== exit 2, wt/scripts, PD=main     rc=2 out=out-wt err=err-wt
== json/stdin, wt/scripts          rc=0
stdin identical / stdout identical / stderr identical      (cmp, payload has CRLF, tab, UTF-8, no trailing NL; stderr has \x01 and \n\n)
RC=0 -> 0, 1 -> 1, 2 -> 2, 3 -> 3, 127 -> 127, 255 -> 255
```

### §2. Every registered command, and the settings diff

`old.json` versus `new.json` (`git show origin/master:` / `HEAD:`), walked recursively. Every
difference sits at a `…/command` key and rewrites `bash .claude/hooks/X.sh` to
`bash "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/run-hook.sh X.sh` with the same X. Nothing else
changed:

```
only commands changed; changed: 14
total command hooks: 14 non-launcher: []
```

`check-hook-commands.py` reports: `ok — .claude/settings.json: 14 hook command(s), every one
canonical and present`.

How `CLAUDE_PROJECT_DIR` behaves:

| `CLAUDE_PROJECT_DIR` | Result |
|---|---|
| Unset, worktree root | worktree hook (rc 2) |
| Unset, `wt/scripts` | `bash: ./.claude/hooks/run-hook.sh: No such file or directory`, rc 127 (as documented, "no worse than today") |
| Empty | same as unset (`:-` covers empty) |
| Contains a space, or `$` and `'` | runs correctly. `BASH_SOURCE` = `…/sp ace/wt/.claude/hooks/x2.sh` from `sp ace/wt/scripts` |
| A different checkout | that checkout's launcher runs |

That last row is by design: the harness sets `CLAUDE_PROJECT_DIR` to the checkout whose
`settings.json` it loaded, so launcher and registration come from the same place (L2).

### §3. The push gate through the launcher, from `scripts/` of the real worktree (`exp3.sh`)

**This is a SIMULATION, not a live session.** The registered command ran under `/bin/sh -c` with
`CLAUDE_PROJECT_DIR=<wt-364>`, cwd `<wt-364>/scripts`, and the Bash tool-call JSON on stdin:

```
git push origin HEAD:master         -> {"hookSpecificOutput":{…"permissionDecision":"deny",…"Blocked: this pushes to 'master'…  rc=0
git push origin hook-launcher       -> (silence)  rc=0
git push --force origin hook-launcher -> deny ("bare `--force` push")  rc=0
cd .. && git push origin master     -> deny  rc=0
old relative form, same cwd         -> bash: .claude/hooks/block-default-branch-push.sh: No such file or directory  rc=127
```

The gate **blocks**. Note that it does so through a JSON `deny` on stdout with exit **0**, not
through exit 2. That is why M1 matters: stdout is the load-bearing channel. The old form's 127
from the same cwd is backlog #364's defect, reproduced. The live-session falsifier is still
unrun; see m3.

### §3b. Every hook runs the same from `scripts/` as from the root (`exp5.sh`)

Ten hooks ran through the launcher, in a fresh `git clone` of the branch, from `.` and from
`scripts/`, each with a plausible payload. For all ten, the exit code and normalised stdout were
identical between the two cwds. So running a hook from a subdirectory, which never happened
before, introduced no cwd-relative misbehaviour in this sample. Every hook resolves `REPO_ROOT`
from `BASH_SOURCE`, and its Python from `__file__`.

### §4. `check-run-hook.py`

`--self-test` printed `63/63 self-test cases passed` in about 8 s, in a copy with a clean env.

**Three mutants**, each applied myself, with every world run rather than only the named ones:

| Mutant | Red worlds | Matches its declared killers? |
|---|---|---|
| m4 (outermost `.git`) | W5 ×2, W8 ×2, W9 | yes |
| m7 (`dirname`) | W12 and W13 | yes (declared W13) |
| m15 (`</dev/null`) | "stdin reaches the hook" only | yes |

On Linux, GNU `dirname` does not fail on long paths, so W12 would not kill m7 there. W13 still
does.

**Three cases**, each checked to fail for the reason in its name, not merely on exit code
(`drive2.py`):

| Case | Under mutant | Got |
|---|---|---|
| W6 | m3 | `(7, '…/main/.claude/hooks/probe.sh')` — main's copy ran. Want `(1, None)` |
| W11 plain symlink | m6 | `…/wtlink/.claude/hooks/probe.sh`, want `…/wt/…` |
| W7 `GIT_DIR` | m9 | `…/main/…`, want `…/wt/…` |

The W11 row is not the ambient pass the review saw in its prototype: this suite asserts the
file that ran, so the logical path is caught.

The W12 path is 1,399 characters. Marker files are unlinked before every launch, and each world
has its own marker index, so no case can pass on an earlier case's state. The control and no-op
cases are present and honest. Apart from M1 and m5, I found no ambient passes.

### §5. Prose

- Launcher header (`run-hook.sh:1-37`): true as far as I tested. That covers the sentinel, the
  `${dir%/*}` walk, "no git process", "only CLAUDE_PROJECT_DIR is consulted" (`pwd -P` ignores
  `PWD`, which W7-PWD confirms) and L1–L7.
- `check-hook-commands.py` docstring: true.
- `check-run-hook.py` docstring: true. Its "63 cases" matches the run.
- `check-fixture-variation.py` EXEMPT reason: says "31 cases", and `cases()` returns 31.
- `session-state.py` BOUNDS: true.
- Backlog row and dashboard entry: m1. PR body: m2, m3, m4.

### NOT RUN by me

- CI for `f6d01b94` was **pending** when I looked (`verify` and all 12 `mutation-sweep` shards),
  so the self-test on ubuntu (dash `/bin/sh`, GNU coreutils) is unobserved.
- I did not run `check-plan-code.py --mutate .` for the 34 + 9 manifest entries.

VERDICT: NOT CONVERGED
