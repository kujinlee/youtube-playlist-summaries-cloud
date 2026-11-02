Reviewed head: f2d25120e8c9c06246fe23f639bfa7845e860883

# PR #471 (backlog #465), round 2, Claude half

**Subject:** branch `build-465`, head `f2d25120`: the round-1 fold of `scripts/check-agent-large-read.py` (redirect
target ends at an operator, redirects removed per part, the narrowed `cd` rule, the empty-part rule, `$'`, `printf`
out of `LIST_ZERO`), its self-test and `scripts/mutations/check-agent-large-read.json`. Primary diff
`c377529a..HEAD`, plus `origin/master...HEAD` for regressions.

**Harness.** Every payload was piped through `python3 scripts/check-agent-large-read.py --hook` with a top-level
`agent_id` and `cwd` set to a scratch directory holding `f100.txt`, `f200.txt`, `f500.txt` (100/200/500 lines) and
`sub/f200.txt`. The SAME command was run with `bash -c` in that directory, stdout+stderr lines counted. Master's
guard and `c377529a`'s guard were run the same way for comparison. Rows read `command -> verdict / bash lines`.

**What holds (RAN):**
- `--self-test`: 101/101.
- `check-plan-code.py --mutate . --only scripts/check-agent-large-read.py`: 103 mutations, 103 killed, 103 attributed,
  0 survivors (a DIAGNOSTIC slice). It CANNOT RUN in the review worktree (no `node_modules`); it ran in a scratch
  clone of `f2d25120` with `node_modules` symlinked from the main checkout. Matches the pin of 103.
- The redirect fix: `cat f200.txt 2>&1&&cat f200.txt`, `2>/dev/null&&`, `2>>/dev/null;`, `2> /dev/null ;`,
  `>&2;` between two 200-line reads -> all DENY / 400. `cat f500.txt 2>/dev/null|head -5`-style pipelines allowed.
- Trailing `;` and empty parts: `cat f200.txt;` allow / 200; `cat f500.txt;` deny / 500; `cat f200.txt && cat
  f200.txt; ` deny / 400; `cat f200.txt; ;` and `cat f200.txt&&cat f200.txt&&` allow (bash: syntax error).
- `cd`: `cd sub && cat f200.txt && cat ../f500.txt` deny / 700; `cd sub; cat f200.txt` allow (narrowed, stated).
- `echo cat; cat f200.txt; cat f200.txt` deny / 401 (`cat` as an echo argument is not mistaken for a reader part);
  `cd cat && cat f200.txt && cat ../f200.txt` (a directory named `cat`) deny / 400.

## Findings

### F1 — MEDIUM — fold-induced: `cd DIR 2>/dev/null && <reader>` is now allowed silently; master and `c377529a` denied it
The fold moved stderr-redirect removal from `bash_spans` (whole command) into `simple_command` (per part,
`scripts/check-agent-large-read.py:294`). But the `cd` branch of `list_spans` tokenises the RAW part
(`scripts/check-agent-large-read.py:392`, `shlex.split(part)`), so `cd sub 2>/dev/null` is three words, fails
`len(words) == 2`, and the whole list returns [] (allowed). RAN:
- `cd sub 2>/dev/null && head -n 400 ../f500.txt` -> **allow** / bash **400**. master: deny. `c377529a`: deny.
- `cd sub 2>/dev/null && cat f200.txt && cat ../f200.txt` -> allow / 400 (a list inside the design rule but for the
  redirect; master did not sum lists, so this half is not a regression, only the single-reader one is).
A regression toward allow of an input master refused, introduced by this round's fold, with no case pinning it.
Fix: apply `STDERR_REDIRECT.sub(" ", part)` before `shlex.split(part)` in `list_spans` (or tokenise the `cd` part via
`simple_command`'s path), plus a case `cd DIR 2>/dev/null && head -n 400 ../big` -> deny.

### F2 — LOW — fold-induced: `2>&-` is no longer removed, so `cat big 2>&-` is allowed (master denied)
The new target class `[^\s;&|<>()]+` (`scripts/check-agent-large-read.py:127`) excludes `&`, so `2>&-` matches
neither alternative; its `>` then makes the command non-simple and the list unsplittable. RAN: `cat f500.txt 2>&-`
-> **allow** / 500 (master and `c377529a`: deny); `cat f200.txt 2>&-; cat f200.txt` -> allow / 400. Fails toward
allow and `2>&-` is not in the docstring's list of removed forms (`2>/dev/null`, `2>>f`, `2>&1`), so LOW; a
`\d?>&[\d-]` first alternative would restore it.

### F3 — LOW — a stderr redirect right after `;`/`&&` with no space is not recognised (fail toward allow)
`(?<!\S)` sees the `;`. RAN: `cat f200.txt;2>/dev/null cat f200.txt` -> allow / 400; with a space after `;` -> deny /
400. Contrived ordering (prefix redirect, no space); stated-bound direction.

**Observed, not raised (outside the fold or within a stated bound):** `grep "" f500.txt; cat f100.txt` -> allow / 600
(`grep` is a designed zero-line part but can print a file); `cd s* && cat f200.txt` with three matching dirs -> deny /
200 (false refusal, but master gives the same verdict); `: ${ZZQ:=f500.txt}; cat $ZZQ` -> NOT CHECKED, loud (a
`LIST_ZERO` word can assign through `${X:=}`, the `printf -v` class, but the later `$X` is unknown so it never denies).

**Tests that cannot fail:** none found. All 103 mutations were killed by the case each names; the new `cd` cases
use a symlinked `logical/link` and a missing directory, so each denies under its mutation.

VERDICT: NOT CONVERGED
