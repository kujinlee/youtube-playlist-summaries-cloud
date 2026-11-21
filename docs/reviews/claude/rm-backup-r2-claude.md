# Round 2 — `rm-backup` — Claude adversarial review (PR #608, head `644942d0`)

**Method.** I imported `scripts/check-rm-backup.py` by path and called `plan()`. The probe harness is
`scratchpad/r2-claude/probe.py`, with session `zz`, so the scratchpad exemption never applies, and root
`/nonexistent-root`. I then confirmed each hole in real bash with `scratchpad/r2-claude/real.sh`. That script
makes a fresh `mktemp -d` dir holding `v a b 'a b' sub/keep list`, runs `bash -c "<cmd>"` there and lists which
files are gone. A finding below means three things held: (1) `plan()` returned `[]`, or a set that does not
contain the deleted file, with no Refuse; (2) the file existed when `plan()` ran; (3) real bash deleted it.
Holes already fixed in round 1 (R1-1…7, S1–S14, C1–C5) are not reported again. The bounds stated in the
docstring are not findings.

Self-test: `python3 scripts/check-rm-backup.py --self-test` → `88/88 self-test cases passed`.

## Findings

### R2-1 — MAJOR — a heredoc delimiter is read as only its leading identifier, so real commands after the heredoc are stripped

`HEREDOC = <<-?\s*(['"]?)([A-Za-z_][A-Za-z0-9_]*)\1` matches only the leading identifier of the delimiter word.
Bash's delimiter is the whole word, after quote removal. When the word goes on past the identifier (`-`, `.`, or a
partial quote), the scanner waits for a line that never comes. It then strips every later line as heredoc body,
and only `$(…)` inside that body is read.

| Command (`$'…'` notation) | `plan()` | bash |
|---|---|---|
| `cat <<END-X\nhi\nEND-X\nrm v` | `[]` | `v` gone |
| `cat <<E.OF\nhi\nE.OF\nrm v` | `[]` | `v` gone |
| `cat <<E"OF"\nhi\nEOF\nrm v` | `[]` | `v` gone (delimiter `EOF`, quoted) |

`E\OF` and `'E'OF` fail the same way. Fully quoted `<<"END-X"` does not match at all, so its body is lexed as
commands. That can only cause an extra refusal, never a miss.

**Fix:** read the delimiter as a full shell word, ending at the first unquoted blank or metacharacter. Its value is
the word after quote removal, and it is quoted if any `'`, `"` or `\` appears in it. If the word cannot be read,
refuse. A case per shape: `END-X`, `E.OF`, `E"OF"`.

### R2-2 — MAJOR — a wrapper with an option value hides `find -delete` and `xargs rm` (the S1 fix covers only `rm`)

The S1/R1-6 runner scan, `for a in range(1, len(args))`, looks only for a later `rm` word. `find` and `xargs`
are detected only when they are the command name after `LOOK_THROUGH`. So `nice -n 5 find …` leaves the name as
`5`, and `env -u HOME find …` leaves it as `HOME`. For `timeout 5 xargs rm`, the scan finds the `rm` and
re-roots there. That gives an `rm` call with no targets, which is allowed.

| Command | `plan()` | bash |
|---|---|---|
| `nice -n 5 find . -name v -delete` | `[]` | `v` gone |
| `env -u HOME find . -name v -delete` | `[]` | `v` gone |
| `nice -n 5 xargs rm < list` (list holds `v`) | `[]` | `v` gone |
| `timeout 5 find . -delete`, `sudo -u root find . -delete` | `[]` | (`plan()` only) |

**Fix:** the runner scan should stop at the first word whose basename is `rm`, `xargs` or `find`, and dispatch on
that word. Add `find`/`xargs` behind `nice -n 5`, `env -u X` and `timeout 5` to the wrapper case.

### R2-3 — MAJOR — an unquoted variable holding blanks is not word-split

`expand()` returns the variable's value as a single path. Bash splits an unquoted expansion on IFS.

| Command | `plan()` | bash |
|---|---|---|
| `X="v a"; rm $X` | `[]` (the path `"v a"` does not exist) | `v` and `a` gone |

`FILES="a.tmp b.tmp"; rm $FILES` is a natural pattern. The lexer has already dropped the quotes, so the hook cannot
tell `rm "$X"` from `rm $X`.

**Fix:** follow the C3 approach and read the value both ways. Back up the whole value, and each blank-separated
piece of it, with globbing applied to each piece.

### R2-4 — MAJOR — a `cd` that may not happen is followed as if it did

The `cd` branch moves `here` whenever the cd is "simple". That test allows `&&` before the cd and `;` after it,
and it never checks that the destination exists. If the cd does not happen, bash runs the next `rm` in the
OLD directory, and the hook has backed up a path under the new one.

| Command | `plan()` | bash |
|---|---|---|
| `cd nope; rm v` | `[]` (looked for `./nope/v`) | `v` gone (cd failed) |
| `test -d nope && cd nope; rm v` | `[]` | `v` gone |
| `if false; then cd vd; fi; rm v` (cwd holds `v` and `vd/`) | `[]` (looked at `vd/v`) | `v` gone |

**Fix:** keep a SET of possible working directories. A cd whose command can fail, or that sits under a condition,
adds the destination to the set rather than replacing it. Back up each relative target in every directory in the
set. A cheaper alternative: set `here = None` unless the destination exists as a directory AND the cd begins its
`&&` chain (`prev_sep in (None, ';', '\n')`).

### R2-5 — MAJOR — the `mktemp` exemption trusts `$T` both to be the fresh directory and to hold nothing older; neither is checked

The exemption assumes `$T` is the new directory itself and that the directory is still empty of anything older.
The rule never checks either.

| Command | `plan()` | bash |
|---|---|---|
| `T=$(mktemp -d); mv v $T/; rm -rf $T` | `[]` | `v` gone, no backup |
| `T=$(mktemp -d) && mv v "$T/" && rm -rf "$T"` (the "trash dir" idiom) | `[]` | `v` gone |
| `T=$PWD/v; T=$(mktemp -d) \| cat; rm -rf $T` | `[]` | `v` gone |
| `T=$(mktemp -d)/..; rm -rf $T` | `[]` | (`plan()` only; deletes `$TMPDIR`) |
| `T=$(mktemp -d; echo /victim); rm -rf $T` | `[]` | (`plan()` only) |

- **The pipeline row: the S13 fix is incomplete.** The pipeline check reads `prev_sep`/`sep_after` of the
  assignment word. For `T=$(mktemp -d) | cat`, that simple command is `T=$`, and its `sep_after` is `(`, not `|`,
  so the pipeline is never seen.
- **The last two rows:** the rule `val == "$" and toks[j+1] == "mktemp"` ignores everything after the `)` of the
  substitution, and every other command inside it.

**Fix:**
- Make FRESH only when the substitution body is exactly `mktemp [opts…]` and the word ends at its `)`.
- Find the `)` that closes the substitution, and apply the pipeline/background test to the separator after it.
- Drop the exemption for `$T` (and for `cd $T` relative targets) once any command between the assignment and the
  `rm` names `$T` with a command other than `mkdir`/`touch`/`cp`/`rsync`/`tar -C`. At minimum, `mv`, `ln` and any
  unknown runner should drop it. Alternatively, do the simplest thing: back up `$T` when it exists at hook time.
  It does not exist yet, so this costs nothing in the common case.

### R2-6 — MAJOR — a variable changed other than by `NAME=value` keeps its stale value (`$PWD` after `cd`, `for`, `export`)

Only a bare `NAME=value` word updates `env`. A `cd` does not update `PWD`/`OLDPWD`, and `PWD` is always in the
hook's environment. The hook's `PWD` is also the hook process's own, which need not equal the payload `cwd` even
before any cd. The same applies to `for X in …`, `read X`, `export X=…`, `declare`/`local`/`readonly X=…`,
`printf -v X` and `getopts`: each leaves an older value in place.

| Command | `plan()` | bash |
|---|---|---|
| `cd sub && cd .. && rm -f $PWD/v` (probe ran with hook env `PWD=/Users`) | `[]` | `v` gone |
| `X=sub/v; for X in v; do rm $X; done` | `[]` (looked at `sub/v`) | `v` gone |

(`export X=v; rm $X` with no earlier `X` is refused. The hole is only a STALE value.)

**Fix:**
- Seed `env["PWD"]` from the payload `cwd`.
- On every followed cd, set `PWD` to the new directory and `OLDPWD` to the old one. On an unfollowable cd, set both
  to `None`.
- For `for NAME`, `read … NAME…`, `export`/`declare`/`local`/`readonly`/`typeset NAME[=…]`, `printf -v NAME`,
  `getopts … NAME` and `mapfile`/`readarray NAME`, set the named variables to `None`, or to the literal value where
  it is visible (`export X=v`).

### R2-7 — MINOR — `builtin cd` (and `eval cd`, `source`) move the shell without the hook noticing

| Command | `plan()` | bash |
|---|---|---|
| `builtin cd sub; rm ../v` | `[]` (looked at `<parent>/v`) | `v` gone |

**Fix:** add `builtin` to `LOOK_THROUGH`. Treat `eval`, `source` and `.` as making `here` and every variable
unknown.

### R2-8 — MINOR — `${S:-default}` with an empty `S` drops the default

`expand()` rewrites `${S:-x}` to `${S}`. When `S` is set to the empty string (`S=;`, or an empty variable in the
hook's environment), the target becomes `""`, which joins to the cwd. The hook then backs up the whole cwd (or
refuses it as too large, or exempts it when the cwd is in the scratchpad), while bash deletes `x`.

`S=; rm -f ${S:-/abs/elsewhere/v}` with cwd `D` → `plan()` returns `[D]`. Bash deletes `/abs/elsewhere/v`; in
`real.sh`, `S=; rm -f ${S:-v}` deleted `v`.

**Fix:** for `:-`, use the expanded default when the value is `""` or unknown-but-possibly-empty. For a known
non-empty value, use the value.

### R2-9 — MINOR — the prefilter and the command name are matched before bash's expansions

| Command | `plan()` | bash |
|---|---|---|
| `find . -name v -de""lete` | `[]` (prefilter: raw text lacks `-delete`, no `rm`, no `$`) | `v` gone |
| `{rm,v}` | `[]` (name `{rm,v}`) | `v` gone |
| `/bin/r? v` | `[]` (prefilter) | `v` gone |

These spellings are deliberate. They are not one of the stated bounds, though: the bound names only a command
name from an unknown variable.

**Fix:**
- Prefilter on the quote-stripped text, as `mentions_rm` already does, testing it for `-delete`.
- Refuse when a command name contains an unquoted `{…,…}` or a glob character. Alternatively, glob it and compare
  basenames.

### R2-10 — MINOR — `<<` inside `${…}` opens a heredoc the shell does not open

| Command | `plan()` | bash |
|---|---|---|
| `echo ${a[x<<y]}` `\n` `rm v` | `[]` | `v` gone |

The C1/S10 arithmetic fix covers `((…))`, `$((…))` and `$[…]`. It does not cover a parameter expansion, whose
subscript is also arithmetic.

**Fix:** copy `${…}` whole, matching braces, the way arithmetic is copied, and read any substitutions inside it.

### R2-11 — MINOR — a quoted word made only of operator characters is read as an operator

`words()` splits every token in the set `;&|()<>\n` into operators, and posix `shlex` has already dropped the
quotes. So in `echo ")"`, the `")"` closes a subshell the hook is tracking. In the command below it lowers `depth`
to 0, the following `cd sub` passes the "simple" test, and `here` leaks out of the subshell:

| Command | `plan()` | bash |
|---|---|---|
| `(echo ")"; cd sub; true); rm v` | `[]` (looked at `sub/v`) | `v` gone |

**Fix:** tokenise with quote state kept, for example a custom lexer, or `shlex` in non-posix mode with quotes
stripped afterwards. Only an unquoted punctuation run should become an operator.

### R2-12 — MINOR — one escape crashes the checker, so the whole call is NOT CHECKED

`echo $'\UFFFFFFFF'; rm /x` gives `ValueError: chr() arg not in range(0x110000)` from `_ansi_char`. The exit is 1,
so the call is allowed. The traceback is visible, which is the designed crash path, but one valid token switches
the hook off for everything else in the command. macOS `/bin/bash` 3.2 leaves `\U…` literal.

**Fix:** have `_ansi_char` return the literal text for an out-of-range code point (or U+FFFD). Add a case.

### R2-13 — MINOR (test) — `find -H dir -delete still reads its start path` cannot fail for that reason

In `find -H dir -delete` with cwd `work`, both the real start (`dir`) and the `.` fallback lie outside the
scratchpad. The case therefore returns `"refused"` even when the start paths are never read. What the name claims
is actually covered by the scratchpad `find -H {scratch} -delete` → `[]` case.

**Fix:** rename the case to what it shows (`find -H` outside the scratchpad is refused), or point it at a start
inside the scratchpad.

Self-test otherwise: the cases I read test what their names say. In particular, the S10 case (a quoted heredoc
after `(( a[1] ))`) and the S11 cases (a multi-line `$(`, and a body with no delimiter) cannot pass for an ambient
reason.

## Verdict

Six MAJOR holes, each confirmed in real bash, let a visible `rm`/`find -delete`/`xargs rm` delete a file the hook
neither backed up nor refused. One of them (R2-5, pipeline row) is an incomplete round-1 fix (S13). Two others
(R2-1, R2-10) belong to the same scan component that produced S10/S11. R2-2 is the S1 fix applied to `rm` only.

VERDICT: NOT CONVERGED
