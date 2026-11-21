Reviewed head: 2ba7acbdecc6ee7ae448e263c23e352adf1563ed

# Round 8 — `rm-backup` — Claude half — CONVERGED (no BLOCKER; 2 MAJOR, 3 MINOR, all for backlog #686)

Subject: PR #608, branch `rm-backup-hook`, the round-7 fold `git diff 62268ac9..fb91c343` (worktree head `2ba7acbd`,
a merge of master on top of `fb91c343`; the merge does not touch `scripts/check-rm-backup.py` or its manifest).
Mandate: try to REFUTE "every file the `rm` would delete is backed up, or the `rm` is refused". Past the round cap,
so only a BLOCKER is folded; everything below is for backlog #686.

Method: a probe harness (`608r8/probe.py` in the session scratchpad) loads a copy of the hook, builds a fresh
directory, asks `plan` with `session_id: probe` (so the scratchpad exemption does not apply), then runs the same
command through `/bin/bash --noprofile --norc -c` (bash 3.2) in that directory, and diffs what was deleted against
what was backed up. MISS = deleted with no backup and no refusal. Every result below was RUN; none is inferred.

## Results of the required commands

- `python3 scripts/check-rm-backup.py --self-test` → `128/128 self-test cases passed`
- `python3 scripts/check-plan-code.py --mutate . --only scripts/check-rm-backup.py` → `OK — delivered scripts mutated: 1 file(s), 95 mutation(s), 95 killed, 95 attributed to the case each names, 0 survivor(s) — measured over ONLY scripts/check-rm-backup.py — a DIAGNOSTIC slice, not the gate`

## The fold itself: it holds

**Angle 1 — can a `[` reach bash's glob with no literal `[` in the target the hook checks?** Not through any
expansion the hook performs. Each was refused (or, for the controls, backed up correctly):

| Command | Hook | bash 3.2 deleted |
|---|---|---|
| `rm -f $'\x5b'a]` | refused (`[` in `[a]`) | `[a]` |
| `X='['; rm -f ${X}a]` | refused (`[` in `[a]`, after expansion) | `a` |
| `rm -f {\[,x}a]` | refused (brace list) | `xa]` |
| `rm -f {Z..a}a]` (range spans `[`) | refused (brace list) | (bash error) |
| `rm -f $(printf '[')a]`, the backtick form | refused (`$`) | `a` |
| `rm -f $"["a]` | refused (`[`) | — |
| `f(){ rm -f "$@"; }; f victim` | refused (`$@`) | `victim` |

The check at `scripts/check-rm-backup.py:832` runs on the word AFTER `expand_words`, so a variable, ANSI-C string or
`$PWD` holding `[` is refused too (over-refusal, the safe side). ⚠ The one way past it is a word the hook never
treats as a target at all — R8-2 below — and that is a pre-existing option-parsing gap, not the fold.

**Angle 2 — did removing `bash_brackets` / the range regex reopen `*` or `?` alone?** No. All OK against bash:
`rm -f *` over `[a] [x b`; `*a]`; `?a]`; `*\]`; `'a\*'` and `a\\*` (backslash literal vs escape); `*/`; `.*`;
`./*/../*`. With no `[` left in `t`, `pat` can hold a `[` only from `glob.escape(here)`, which is literal. ⚠ One
`?` shape misses, but it predates the fold and comes from the locale, not from brackets (R8-4).

**Angle 3 — lit/pat split.** Kept correctly. `lit` (line 838) is the unescaped name; `pat` (839) escapes only the
`cd` directory; the glob runs only when `t` (not `pat`) holds `*`/`?` (840), so `cd 'app/*' && rm -f x.bak` is read
as the literal name. Confirmed against bash: `cd 'app/[id]' && rm -f *.bak` (only `app/[id]/x.bak`, not `app/d.bak`),
`cd 'app/[id]' && rm -f x.bak`, `cd app/\[id\] && rm -f ?.bak`, `cd 'app/*' && rm -f *.bak`. The unlistable-directory
case is pinned by mutation "a pattern is read only as a pattern" (drops `+ [lit]`), killed by the r7 case.

**Angle 4 — mutation manifest.** 95 entries, `expected_mutations.py` says 95. Every edit anchor occurs EXACTLY ONCE in
the file (checked by script: 0 anchors with a count other than 1). The nine removed mutations each edited code inside
`bash_brackets` or the removed Phase 6 regex line, and none of those anchor strings survives in the file, so none
guarded live code. The new `if "[" in t:` → `if False:` mutation is killed by the R7 case it names. The two rebound
mutations (`+ [lit]` removal; `lit` escaped) are attributed to cases that fail for the right reason.

## Findings

### R8-1 — MAJOR — `find … -rm` deletes with no backup and no refusal (pre-existing; not the fold)

`scripts/check-rm-backup.py:688` (gates `find` only on `-delete` / `-exec*`/`-ok*` + `rm`) and `:802` (the prefilter).
In the Claude Code Bash tool `find` is a shell FUNCTION that runs `bfs` (`declare -f find` → `exec -a bfs "$_cc_bin"
-S dfs …`), and bfs has `-rm`, a synonym for `-delete`. `-rm` is not an `rm` word (`RM_WORD` needs no `-` before it),
so `no_rm` is true and `plan` returns `[]` before reading anything.

Failing input, run end to end through `--hook` in scratch: `find <dir> -name victim.txt -rm` → hook rc 0, silent
(allowed), no backup root created; the file is gone. Not a BLOCKER only by the #686 precedent (the threat is the
agent's accidental `rm`, and `-rm` is not a GNU or BSD `find` primary an agent would type by habit). It is the
closest thing to a BLOCKER this round: `find -delete` is an enumerated, gated deletion channel, and this is the same
channel under another name in the very `find` the agent runs. Fix shape: treat `-rm` like `-delete` in both places.

### R8-2 — MAJOR — a glob word that starts with `-` is skipped as an option, so it is never globbed or refused (pre-existing)

`scripts/check-rm-backup.py:680`: before `--`, any word starting with `-` is an option. bash expands it first, and
macOS `rm`'s getopt stops at `--` or at a bare `-` operand, so the expansion can name files:

| Command (files in cwd) | Hook | bash 3.2 deleted |
|---|---|---|
| `rm -*` (`-`, `-victim`, `keep`) | backs up `[]` | `-`, `-victim` |
| `rm -*` (`--`, `-victim`) | `[]` | `-victim` |
| `rm -?` (`--`, `-v`) | `[]` | `-v` |
| `rm -[-] -[v]` (`--`, `-v`) | `[]` | `-v` |

The last row is a `[` reaching bash's glob past the r7 refusal: the fold's rule "every `[` in a target is refused"
holds only for words the hook classes as targets. It needs a file named `-` or `--` in the directory, so it is not an
accidental command. Fix shape: a word before `--` that holds `*`, `?` or `[` is refused (or read as a target too).

### R8-3 — MINOR — an alias defined in the command runs `rm` unseen

`expand_aliases` is ON in the Claude Code Bash tool (measured: `alias zz='echo …'` on line 1, `zz` on line 2 printed
it; `shopt expand_aliases` → `on`). `shopt -s expand_aliases` + newline + `alias zap='rm -f'` + newline + `zap victim`
→ hook `[]`, bash deleted `victim`. Arguably inside the stated bound "an `rm` the shell builds at run time … inside a
quoted string" (line 62), but the bound names `trap`/`bash -c`/`eval`, not `alias`. Fix: name it in the bound, or
refuse a command whose `alias` body mentions `rm`.

### R8-4 — MINOR — under a C locale set in the command, `?` matches a byte, Python's glob a code point (pre-existing)

`scripts/check-rm-backup.py:840`. `LC_ALL=C; rm -f ??` over `é` (U+00E9, two bytes) and `ab` → hook backs up `ab`;
bash deletes `ab` and `é`. (`LC_ALL=C rm -f ??` as a PREFIX is fine: bash expands before the prefix applies — run.)
`export LC_ALL=C; rm -f ?` over-backs-up (harmless). Not in the #686 list. Fix: treat a command that sets
`LC_ALL`/`LC_CTYPE`/`LANG` like `shopt` (R4-2), or let bash match (the #686 redesign closes it).

### R8-5 — MINOR — no mutation names the `"*?"` glob trigger

`scripts/check-rm-backup.py:840`. Neither `"*?"` → `"*"` nor → `"?"` is in the manifest. Both die today (run in a
scratch copy: 127/128, killed by the S25 `mktemp` link case; 125/128), but the `?`-dropped mutant dies only
incidentally, by a case not about `?`. Add one mutation per character, each naming a `?`/`*` case.

## Re-confirmed, already filed (not new)

R4-2 and R4-5 in backlog #686 still reproduce, as filed: `shopt -s dotglob; rm -f *` and `GLOBIGNORE=zz; rm -f *`
(miss `.env`), `shopt -s nocaseglob; rm -f a*` (misses `A2`), `cd sub && rm -f ~-/x`, `rm -f ~+/x`,
`rm -f ~kujinlee/<path>/x` (each misses `x`).

## Bounds of this review

Probed against bash 3.2 at `/bin/bash`, en_US.UTF-8, APFS (which refuses non-UTF-8 names, so invalid-byte `?` cases
cannot arise here). The probes ran `plan` on a copy of the file at `fb91c343`; R8-1 was also run through `--hook`.
Not probed: bash 5, Linux filesystems, the hook's prune/back-up paths (unchanged by the fold).

VERDICT: CONVERGED
