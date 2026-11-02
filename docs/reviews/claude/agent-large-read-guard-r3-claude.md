Reviewed head: 5429bd3b271d40f58cca6b2be5fb2fa4acbb1533

# PR #469 (backlog #457), round 3, Claude half

**Subject:** branch `agent-large-read-guard` at `5429bd3b`; the r2 fold is `git diff 91640452..5429bd3b`. The Codex
half is a REVIEW GAP (alternation). Round 3 is the last round that folds non-BLOCKERs (`review-method.md` §0 Q4c).

**Claim under test:** the hook never refuses a main-session call or a compound Bash command; for a subagent it refuses
exactly a simple `cat`/`head`/`tail`/`sed` command, or a Read, that puts more than 300 lines of a file into context and
could have been narrowed; notebooks, PDFs and images on Read are exempt; unresolvable input is NOT CHECKED at exit 1
with no traceback; the r2 narrowing introduced no defect, lost no needed case, and each case fails without its clause.

**Method.** Every probe below was RUN through `bash .claude/hooks/run-hook.sh agent-large-read.sh` from the worktree,
with a crafted payload (`agent_id: a1`, `cwd` = a scratch fixture directory) — fixtures: `big` (1000 lines), `s200`,
`n301` (no trailing newline), `exact300`, `crlf400`, `cr400` (bare CR), `oneline` (200 KB, one line), `empty`, a
directory, a mode-000 file, `sub/big`, `sp ace/big`. Real output was compared with the macOS (BSD) tools the agent runs.
Read's `offset` semantics were MEASURED with this agent's own Read tool on `big`: `offset: 700` starts at line 700
(1-based), `offset: 0` starts at line 1 — both what `read_spans` models.

## Findings

### F1 — Low — a command with no tokens after `shlex` tracebacks (FIX-INDUCED, r2) — fold

`scripts/check-agent-large-read.py:278`, `simple_command`: `tokens[0]` is indexed without checking that `tokens` is
non-empty. `READER_WORD` matches the word in a comment, or in a stderr target that `STDERR_REDIRECT` then deletes, and
`shlex` returns nothing.

    RAN: {"command": "# cat big"}   -> rc=1, Traceback ... IndexError: list index out of range (line 278)
    RAN: {"command": "#cat"}        -> rc=1, same traceback
    RAN: {"command": "2>/x/cat"}    -> rc=1, same traceback
    RAN: {"command": "2>>cat"}      -> rc=1, same traceback

The claim says unresolvable input is NOT CHECKED "never a traceback", and the docstring says so too; this is a crash, not
a NOT CHECKED. It is non-blocking (exit 1, the call proceeds), so not a BLOCKER. FIX-INDUCED: the pre-r2 checker
(`91640452`, run from a copy of its scripts) answers `# cat big` with rc=0, allow. Fix: `if not tokens: return None`
before the index (a comment-only command is not a reader command), with a case for `# cat big` and `2>/x/cat`.

### F2 — Low — `sed -n '0,Np'` is counted as N lines; both seds print nothing (not fix-induced) — FILE or fold

`SED_RANGE` (line 112) accepts a start address of 0 and `take` clamps it to line 1.

    RAN: {"command": "sed -n 0,400p big"}  -> deny, "puts 400 lines"
    real: /usr/bin/sed -n 0,400p big  -> 0 lines, rc=0 (BSD: address 0 never matches); GNU sed rejects line address 0

A refusal of a command that prints nothing. Rare (`0,` is a GNU regex idiom), and the agent can satisfy it, so Low.
Fix: a start of 0 is NOT CHECKED (or 0 lines).

### F3 — Low — `2>/dev/null 1>&2` is stripped as two stderr redirections; stdout goes to /dev/null (not fix-induced) — FILE

`STDERR_REDIRECT` (line 108) deletes `1>&2` and `2>/dev/null` independently of order.

    RAN: {"command": "cat big 2>/dev/null 1>&2"}  -> deny, "puts 1000 lines"
    real: (cat big 2>/dev/null 1>&2) 2>&1 | wc -l  -> 0

Same verdict at `91640452`. Contrived; noted because the docstring says these redirections "are not stdout", and
`1>&2` is stdout. `>&2` alone is correctly denied: Claude Code returns stderr to the context too.

### F4 — Low — `cat -s` (squeeze blank lines) is counted unsqueezed (not fix-induced) — FILE

    RAN: {"command": "cat -s blanks"} (500 blank lines then `x`) -> deny, "puts 501 lines"; real output: 2 lines

`cat` treats every flag as harmless. Satisfiable (narrow with `sed -n`), rare.

## Probed and correct (no finding)

- **Main session:** `cat big` and a 1000-line Read with no `agent_id` -> allow, rc 0.
- **Line counts:** `n301` -> 301 deny; `exact300` -> allow; `crlf400` -> 400 deny (Read and `cat` both see 400);
  `cr400` (bare CR) -> allow (an under-count, not a refusal); `oneline` 200 KB -> allow (the rule is lines, not bytes);
  `empty`, a missing file, a directory, a mode-000 file -> allow, rc 0, silent.
- **`cd DIR &&`:** `cd sub && cat big` deny 1000; `cd sub && head -n 300 big` allow; `cd "sp ace" && cat big` deny;
  `cd sub&&cat big` deny; `cd sub; cat big`, `cd sub && cd .. && cat big` allow (stated bound).
- **Quoting/spaces:** `cat "sp ace/big"`, `cat sp\ ace/big` deny 1000; a quoted `;` inside a sed script is not an operator.
- **sed:** `1,400p` deny; `'1,300p'` allow; `'400,1p'` allow (real sed prints 1 line); `'1,200p;100,250p'` 351 = real 351;
  `'1,400p;350q'` 350 = real 350; `'350q;1,400p'` 349; `1,400p s200 s200` 400 = real 400; `-En`, `-ne`, `--quiet` deny;
  `'$p'`, `'/x/p'`, `'1,+400p'`, `'1~2p'`, `'1,400{p}'`, `--expression=` -> NOT CHECKED rc 1, no traceback; `sed 1,400p`
  (no `-n`) and `sed -n 1,400p` (stdin) allow.
- **head/tail:** `-n 400`, `-400`, `--lines=400`, `-n -100` (900), `tail -n +2` (999), `tail +700` (301), `-n 200 s200 s200`
  (400) are exact; `head -c`, `tail -f` allow; `tail -n 400 s200` allow (200); `head -n 300 -- big` NOT CHECKED (allowed).
- **Compound:** pipelines, `;`, `&`, `cat < big`, `>`/`1>` to /dev/null, `>/dev/null 2>&1` -> allow. `2> err.txt`, `>&2`,
  `3>&1` -> deny (stdout or stderr still reach the context).
- **Read:** `limit: 300` allow; `offset: 700` 301 deny / `offset: 701` allow (matches the measured 1-based offset);
  `offset: 0`, `-5`, `limit: 0`, `-1` allow; `300.0` accepted; `300.5`, `"300"`, `null`, `1e400` NOT CHECKED rc 1;
  `.PDF`, `.Ipynb` exempt (case-folded); `.svg`, `.bmp` holding text counted (they are text to the Read tool); a relative
  `file_path` allow; `tool_input` `[1]` / `null` NOT CHECKED.
- **Quoted glob:** `cat 'f[1]'` (a 1-line file) is denied for the 1000-line `f1` — inside stated bound (2).
- **Suite:** `--self-test` 85/85. `check-plan-code.py --mutate . --only scripts/check-agent-large-read.py`: 83 mutations,
  83 killed, 83 attributed, 0 survivors. The r2 narrowing kept the cases the remaining rules need: `cd` relative and
  `$VAR`, the two-`&&` list, `2>/dev/null`/`2>&1`, glob expansion, `-` as stdin, the 18-digit bounds.

## Verdict

The claim is refuted on one clause: "no traceback" (F1, fix-induced, one-line fix). No false refusal found in a realistic
agent command; F2-F4 are contrived wrong counts, each satisfiable by narrowing. None is a BLOCKER (Q4c): the hook
cannot block (every non-zero exit becomes 1) and never refuses the main session. Fold F1 in this round (the last one that
folds non-BLOCKERs); F2-F4 are FILE.

VERDICT: NOT CONVERGED
