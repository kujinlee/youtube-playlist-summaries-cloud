# rm-backup hook — adversarial review, round 4 (Claude half)

Subject: `scripts/check-rm-backup.py` + `.claude/hooks/rm-backup.sh` at head `0286e19b` (backlog #685, PR #608).
Self-test: `python3 scripts/check-rm-backup.py --self-test` → `123/123 self-test cases passed`, rc 0.

**Method.** Every finding below was RUN, not inferred. The harness
(`<scratchpad>/r4-claude/probe.py`, specs `p1.json`–`p3.json`) builds a fresh fixture dir per probe, runs the real
hook (`check-rm-backup.py --hook`) as a subprocess on a PreToolUse payload (`session_id: probe-session`, so the
fixture is not treated as the scratchpad; `RM_BACKUP_ROOT` inside the fixture), records what got backed up, then
runs the command with `/bin/bash -c` (3.2, the Bash tool's shell) in the same cwd and diffs the file tree.
"NOBACKUP" = files that existed, were deleted by bash, and have no copy under the backup root.
`@` below stands for the fixture dir; cwd is `@/w` unless stated.

## Findings

### R4-1 — BLOCKER — glob: Python's `glob` is not bash's glob (`[^…]`, POSIX classes)

| Command | Hook | Backed up | bash deleted | NOBACKUP |
|---|---|---|---|---|
| `rm -f [^k]*` (files `keep a1 b1`) | allowed | `keep` | `a1 b1` | **`a1 b1`** |
| `rm -f [[:digit:]]*.log` (files `1.log 2.log`) | allowed | — | `1.log 2.log` | **`1.log 2.log`** |

`plan` expands targets with `glob.glob` (fnmatch). In fnmatch `[^k]` is the set {`^`,`k`}; in bash it is the negation
(same as `[!k]`, which the hook gets right — probe `bangneg`: backed up and deleted `a1`). fnmatch has no POSIX
character classes, so `[[:digit:]]` matches nothing. The hook backs up the WRONG files (in the first row it copies
exactly the one file bash keeps). Both are ordinary-looking globs. Component: **scan/backup (target expansion)**.
Not caused by the r3 fold. Fix direction: refuse any bracket expression the hook does not translate itself (`[^`,
`[:`, `[=`, `[.`), or expand with bash (`compgen -G`) instead of Python.

### R4-2 — MAJOR — glob: shell glob options are not modelled (`shopt`, `GLOBIGNORE`)

| Command | Backed up | NOBACKUP |
|---|---|---|
| `shopt -s dotglob` ⏎ `rm -rf *` (files `.env a`) | `a` | **`.env`** |
| `GLOBIGNORE=a; rm -f *` (files `.env a b`) | `a b` | **`.env`** (setting GLOBIGNORE turns on dot-matching) |
| `shopt -s nocaseglob` ⏎ `rm -f A*` (file `abc`) | — | **`abc`** |
| `shopt -s extglob` ⏎ `rm -f !(keep)` (files `keep x y`) | — | **`x y`** |

`GLOBIGNORE=a` is a plain `NAME=value` word, so it passes the r3 allowlist untouched. Component: **scan/backup**. Not
fold-induced. Fix direction: `shopt` (any `-s`) or `GLOBIGNORE` anywhere → refuse glob targets; for `extglob`, a target
word that is `!`/`@`/`+`/`*`/`?` followed by `(` must refuse (today it lexes as `!` + subshell).

### R4-3 — MAJOR — variables/cwd: text is read once, but loop bodies re-run and function bodies run at the call

| Probe | Command | Backed up | NOBACKUP |
|---|---|---|---|
| `loop` | `prev=old.log; for f in new1.log new2.log; do rm -f $prev; prev=$f; done` | `old.log` | **`new1.log`** |
| `whileloop2` | `X=a; while true; do rm -f $X; [ $X = b ] && break; X=b; done` | `a` | **`b`** |
| `fnvar` | `f() { X=victim; }; X=decoy; f; rm -f $X` | `decoy` | **`victim`** |
| `fncwd` | `f() { rm -f victim; }; cd sub && f` (file `sub/victim`) | — | **`sub/victim`** |

The r3 premise "a variable set only by plain `NAME=value` words is read" assumes each assignment runs once, in text
order. A loop body's later assignment feeds its earlier `rm` on the next pass; a function body's assignment runs at
the call, not where it is written; a function body's relative `rm` is resolved against the cwd at the DEFINITION.
Component: **variables + cwd**. Not caused by the r3 fold: the `while` row needs no `for`, so it is independent of
r3's narrowing of `for` to its own names. (The `loop` row is the `for` shape r3 chose to allow by that narrowing.)
Fix direction: inside a loop body or a function body, every variable read and every relative target is UNKNOWN (or a
plain assignment anywhere inside a loop/function body poisons that name for the whole command, and a called function
name makes the cwd unknown).

### R4-4 — MAJOR — backup: targets are judged BEFORE earlier commands in the same call run

| Command | Backed up | NOBACKUP |
|---|---|---|
| `mv precious tmp.txt && rm -f tmp.txt` | — | **`precious`** (its content) |
| `ln -s @/data link && rm -rf link/` (file `data/a`) | — | **`data/a`** |

`plan` stats/globs every target at hook time; a target created, renamed or re-pointed by an earlier command in the
same call is "missing" → needs no backup. The `ln -s` row is a real deletion of a pre-existing tree via the
`link/` rule the docstring itself states. Component: **backup (time of check)**. Not fold-induced. Not stated as a
bound (the docstring's "a glob matching nothing, like a missing file, needs no backup" does not say "missing NOW,
though an earlier command may create it"). Fix direction: at minimum state the bound; better, refuse an `rm` whose
target word is also an argument of an earlier `mv`/`cp`/`ln`/`tar`/`git` in the same command.

### R4-5 — MAJOR — variables: tilde forms other than `~` and `~/` are read as a relative literal

| Command | Backed up | NOBACKUP |
|---|---|---|
| `rm -f ~+/victim` | — | **`victim`** |
| `cd sub && rm -f ~-/victim` | — | **`victim`** (OLDPWD) |
| `rm -f ~kujinlee/<path-under-home>/w/victim` | — | **`victim`** |

`expand` handles only `word == "~"` or `startswith("~/")`; `~user`, `~+`, `~-` fall through as relative names
(`<cwd>/~+/victim`), which do not exist, so nothing is backed up. Component: **variables (expansion)**. Not
fold-induced. Fix direction: any other leading `~` refuses.

### R4-6 — MAJOR — cwd: `CDPATH` redirects `cd`

`CDPATH=@/other; cd x && rm -f f` (dirs `w/x/` empty, `other/x/f`): allowed, nothing backed up, bash deleted
**`other/x/f`**. The hook joined `x` to the cwd. With `CDPATH` set, bash searches it BEFORE `.`. Component: **cwd**.
Not fold-induced. NOT reproduced: the same with `CDPATH` only in the exported environment (bash `-c` used `./x`), so
the environment form is a hypothesis for an interactive/profile-initialised shell. Fix direction: `CDPATH` anywhere
in the command, or non-empty in the environment, makes every relative `cd` UNKNOWN.

### R4-7 — MAJOR — variables: `$_` (and any shell special parameter) is read from the HOOK's environment

`ls victim >/dev/null; rm -f $_`: allowed; the hook backed up **`/usr/local/bin/python3`** (its own `$_`, set by the
wrapper's bash), bash deleted **`victim`** — NOBACKUP. `VAR` matches `_` as a name and `env` is the hook's
`os.environ`. The docstring's bound "the environment is the HOOK's" covers inherited variables; `$_` is not an
inherited variable but one bash rewrites after every command, so the deny rule "a variable with no known value"
is false for it. Component: **variables**. Not fold-induced. Fix direction: never read `_` (and `SHLVL`, `OLDPWD`
before a followed `cd`, `BASH_*`, …) from the environment.

### R4-8 — MAJOR — scan: an unreadable LATER line turns into an allow, but bash runs the earlier lines

`rm -f victim` ⏎ `echo 'oops` (an unterminated quote on line 2): hook rc 1, stderr `… this call was NOT CHECKED …`,
allowed; bash executed line 1 (deleted **`victim`**, no backup) and then failed on line 2 with
`unexpected EOF while looking for matching '`. The NOT CHECKED → allow policy is stated, but its implicit premise —
that a command the lexer cannot split does not run — is false: bash parses and runs a multi-line `-c` string one
command at a time. The "said" half goes to the stderr of an exit-1 hook, which (unverified here) Claude Code shows to
the user, not the model. Component: **scan / exit policy**. Not fold-induced. Fix direction: when the command
`mentions_rm` (or has `-delete`), an `Unreadable` should DENY; keep NOT CHECKED only for commands with no `rm` word.

### R4-9 — MAJOR (not ordinary-looking) — scan: a backslash-newline inside `rm` defeats the fast path

`r\` ⏎ `m -f victim`: allowed, nothing backed up, **`victim`** deleted. `plan`'s `no_rm` fast path runs
`mentions_rm` on the raw text with backslashes dropped (`r` ⏎ `m`), sees no `rm` word, no `$`, no glob → returns
`[]` before `_protect` (which does remove line continuations) is ever reached. The same defeats `-del\`⏎`ete`.
Component: **scan**. Not fold-induced. Fix: remove backslash-newline pairs before the fast-path tests.

### R4-10 — MINOR — variables: `$'\0'` truncates in bash, not in the hook

`rm -f $'\0'*` (files `victim other`): allowed, nothing backed up, bash deleted **both** (`$'\0'` is the empty
string, so the word is `*`). The hook keeps a NUL in the target, which matches nothing. Contrived. Component:
**variables (ANSI-C decode)**. Fix: truncate a decoded `$'…'` at `\0`, as bash does.

### R4-11 — MINOR — command-position: a brace list after a runner

`/usr/bin/nice {rm,-f} victim`: allowed, **`victim`** deleted, no backup. `LOOK_THROUGH` matches only the bare word
`nice`, and the runner scan checks `basename(w) == "rm"`, so `{rm,-f}` is missed. The stated bound names "a glob
word found after a runner's options"; a brace list is not stated. Component: **command-position**. Fix: in the
runner scan, a BRACE word (or a glob word) that can expand to `rm`/`find`/`xargs` raises `PatternName`; state it
otherwise.

### R4-12 — MINOR — exemptions/backup: an `rm` of the backup root destroys the backup it just triggered

`rm -rf @/w @/_backups` (root = `@/_backups`): the hook copied `w/a` into the root and allowed; the same `rm` then
deleted the root, copy included. The root is exempt by design, but naming it alongside another target silently
voids that target's backup (realistic shape: `rm -rf ~/.claude` with a small `~/.claude`, when the default root lies
inside it — that case is otherwise likely caught by MAX_BYTES/MAX_FILES; not run). Fix: refuse when the root is
inside, or equal to, any target.

### Probed and NOT a hole

- `echo hi >#x; rm -f victim` — bash 3.2 also reads `#x` as a comment (syntax error, nothing runs).
- 120-deep nested `$(echo …)` followed by `rm -f victim` — no crash, `victim` backed up.
- `rm -f [!k]*` — correct.
- `X=a; n=0; while [ $n -lt 2 ]; do rm -f $X; X=b; n=$((n+1)); done` — refused (OPAQUE via `$((`).

### Not examined

Self-test case names versus what each asserts; false refusals of ordinary commands; the mutation manifest.

## Verdict

One BLOCKER (R4-1: two ordinary-looking globs delete files the hook did not back up, and it copies the wrong ones),
eight MAJORs across glob expansion, control flow, time of check, tilde, `CDPATH`, `$_`, the NOT CHECKED policy and
the fast path, three MINORs. None is caused by the r3 fold. R4-1/R4-2 and R4-4 share a root cause worth naming for
the fold: the hook re-implements bash's target expansion in Python at hook time, and every divergence — glob
dialect, glob options, state changed by an earlier command — is a silent miss, not a refusal.

VERDICT: NOT CONVERGED
