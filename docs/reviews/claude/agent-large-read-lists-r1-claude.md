Reviewed head: c377529aa3bae9ef74f61e3cddaf6f39df346f9a

# PR #471 (backlog #465), round 1, Claude half

**Subject:** branch `build-465`, head `c377529a`: `scripts/check-agent-large-read.py` sums a `;`/`&&` list of simple
readers against the 300-line limit, plus its self-test, mutation manifest and the pin in `scripts/check-plan-code.py`.

**Harness.** Every payload was piped through `python3 scripts/check-agent-large-read.py --hook` with a top-level
`agent_id` (a subagent) and `cwd` set to a scratch directory holding `big.txt` (500 lines), `small.txt` (100),
`a.txt`/`b.txt` (200 each). The SAME command was then run with `bash -c` in that directory and its stdout lines
counted, so each row reads `command -> guard verdict / lines bash actually printed`. Master's guard
(`origin/master:scripts/check-agent-large-read.py`) was run the same way for comparison.

**What holds (RAN):**
- `--self-test`: 96/96.
- `check-plan-code.py --mutate . --only scripts/check-agent-large-read.py`: 95 mutations, 95 killed, 95 attributed,
  0 survivors. ⚠ It CANNOT RUN in the review worktree (`node_modules/typescript is missing`); it ran in a scratch
  clone of `c377529a` with `node_modules` symlinked from the main checkout. The pin (95) matches.
- Summed correctly: `cat a.txt;cat b.txt`, tab separators, `cd . && cat a.txt && cat b.txt`,
  `sed -n 1,200p a.txt; sed -n 1,200p a.txt` (400 printed, the same file twice), `ls; wc -l a.txt; grep -c l a.txt;
  cat a.txt; cat b.txt` -> all DENY with 400+ printed.
- Fails toward allow as stated: `cat a.txt & cat b.txt`, `cat a.txt; exit; cat b.txt`, `false && cat a.txt; cat b.txt`,
  `cd -P; cat big.txt`, `cat a.txt\;; cat b.txt` (bash: `a.txt;` is missing, 200 printed) -> allow.
- Quoting: `echo "a;b" ; cat a.txt; cat b.txt` -> deny (401); `echo "a\"; cat big.txt"; cat small.txt` -> allow (101).

## Findings

### F1 — HIGH — `STDERR_REDIRECT` swallows an adjacent `;`, `&&` or `|`, so a list of readers is mis-split both ways
`scripts/check-agent-large-read.py:116` (`2>>?\s*\S+`) is applied to the whole command at
`scripts/check-agent-large-read.py:298`, BEFORE `split_list`. `\S+` runs on through a separator written with no
space before it, so `2>/dev/null;` deletes the `;` and the two commands become ONE reader with the next command's
words as file operands. RAN:
- `sed -n 1,200p a.txt 2>/dev/null; sed -n 1,200p b.txt` -> **allow** / bash printed **400**. Read as one `sed` over
  the stream `a.txt sed 1,200p b.txt` with range 1-200. This is the row's falsifier exactly: a list of simple readers
  printing more than 300 lines, allowed silently. Also `sed -n 1,150p a.txt 2>/dev/null; cat b.txt` -> allow / 350;
  `sed -n 1,200p a.txt 2> /dev/null; sed -n 1,200p b.txt` -> allow / 400.
- False refusals (the costlier direction): `cat small.txt 2>/dev/null; wc -l big.txt` -> **DENY** / bash printed
  **101** (`wc` and `big.txt` became `cat` operands); `cat small.txt 2>/dev/null;echo big.txt` -> DENY / 101; and a
  PIPELINE, which the docstring says is always allowed: `cat big.txt 2>/dev/null|head -5` -> **DENY** / 5.
- The same commands with a space before the separator (`2>/dev/null ; ...`, `2>/dev/null && ...`) are handled right.
- PRE-EXISTING: master's guard gives the identical three verdicts on the three representative inputs. But this PR
  moved the stderr removal to sit directly in front of the new list splitter and claims `;`/`&&` lists, so it is in
  scope. Fix: stop the redirect's target at an operator character (e.g. `2>>?\s*[^\s;&|()<>]+`) or remove redirects
  per part after `split_list`; add the three inputs above as cases (deny / deny-false-positive-gone / allow).

### F2 — LOW — a list that bash rejects as a syntax error is refused
`split_list` drops empty parts (`list_spans`, `if not part.strip(): continue`), so a list bash will not run at all is
counted as if it ran. RAN: `cat big.txt &&`, `; cat big.txt`, `cat a.txt;; cat b.txt` -> DENY / bash printed 0
(rc 2). An agent rarely writes these; the cost is one wasted refusal.

### F3 — LOW — ANSI-C quoting `$'...\'...'` is mis-tracked by `split_list`
`split_list` treats `\'` inside single quotes as a closing quote, which is right for `'...'` but wrong for `$'...'`.
RAN: `echo $'\';cat big.txt;echo ' \'` -> **DENY** / bash printed 1 line (one `echo`). Rare in agent commands.

### F4 — LOW — an unjudgeable part makes the whole list NOT CHECKED, even when a later part is a plain over-limit read
RAN: `echo hi; cat $NOPE_UNSET; cat big.txt` -> NOT CHECKED (exit 1, stderr) / 501;
`sed -n '/x/p' a.txt; cat big.txt` -> NOT CHECKED / 500. Loud, not silent, and consistent with the single-command
`Unreadable` rule, so within the stated bound; noted because the denial of `cat big.txt` was decidable.

**Tests that cannot fail / fail-open handlers:** none found. The `cd -` case builds a `-/big.txt` so a wrong `cd`
would deny; the `#` case denies if `#` leaves `LIST_DOUBT`; the `shlex.split` `ValueError` handler returns `[]`
(allow) which is the stated direction. Every mutation was attributed to the case it names.

VERDICT: NOT CONVERGED
