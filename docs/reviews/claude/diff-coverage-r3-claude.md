# Round 3 — `diff-coverage` (PR #411) — Claude half (adversarial, REFUTE mandate)

Tree: branch `diff-coverage` @ `263dfc28`, reviewed as `git diff origin/master...HEAD` (origin/master `4aaa6ed7`).
Every experiment ran in a `mktemp -d` clone (`/var/folders/.../tmp.aZhJawZjUv/repo`). No checkout was edited.

**The bet (decision-log row, written before round 3):** no changed or deleted decision line is missed or wrongly
cleared, and no input crashes the check or yields a clean zero over something it did not measure.
**Result: LOST.** One construction produces each of the bet's two named failures: a missed line under a clean zero
"— every one is edited by a mutation" (M2, M3, M4, L2), and a line wrongly cleared (M2, L3). In CI the step itself
was SKIPPED on both of this PR's last two runs (M1).

## What HELD (executed)

- `--self-test`: **48/48**. `check-plan-code.py --mutate . --only scripts/check-diff-coverage.py` in a full copy
  with `node_modules/typescript`: **24 mutations, 24 killed, 24 attributed to the case each names, 0 survivors** (20s).
- Re-measured against origin/master `4aaa6ed7`: **57** at `session-state` `16bed21b`, **32** at
  `hooks-absolute-path` `b6e46a3a`, and the 32 include `check-hook-commands.py:80` `if h.get("type") == "command":`.
- Coverage-rule probes, run directly against `edited_lines`. A replacement that re-creates the same line edits
  nothing (`set()`). Splitting and re-joining a line edits nothing. A mid-line insertion edits its line. A
  line-boundary insertion edits none. A whitespace-only edit counts as an edit: it is an equivalent mutation, but
  the harness refuses a mutation that survives, so this is harmless. A find text that occurs several times covers
  every occurrence. That is harmless too: `anchor_problems` and `run_mutations` refuse any anchor that is not
  unique in the text it is applied to. No current manifest has an edit whose find count in the original source
  differs from 1 (scanned all of them: 0).
- Performance: `run_check` takes 0.59s on `session-state`. On a diff of **86,909 inserted lines across 78
  scripts** (base = 400 first-parent commits back) it takes **3.48s**, giving 6,991 warnings over 70 manifested scripts.
- Binary (`-diff` attribute) gives NOT CHECKED. A real textconv driver did not alter the `-U0` output.

## Findings

### M1 — Medium — `.github/workflows/ci.yml:919-921` — the step is SKIPPED whenever any earlier `verify` step fails, so it never ran on r1 or r2
Evidence (`gh run view`, `verify` job, both steps named):
```
run 40459705079 263dfc28  check-review-recorded (PR only)=failure | diff coverage — …=skipped
run 40458501786 8130578c  check-review-recorded (PR only)=failure | diff coverage — …=skipped
run 40454687683 772e0ab8  diff coverage — …=success              | check-review-recorded=failure
```
The r1 fold moved the step AFTER `check-review-recorded`. That step fails on every draft round until the reviews
are filed, and the implicit `if: success()` then skips the warn step. The warnings therefore cannot reach the PR
while review is running, which is the window the tool exists for. A red in any earlier step of `verify` hides them too.
The `::warning` annotations added in r1 have **never been observed in CI**. The only run where the step executed
predates them: `verify` at `772e0ab8` has `annotations_count=3`, and all three are runner notices.
Separately (GitHub's documented limit, NOT measured here): Actions shows at most 10 warning annotations per step.
The survey below has PRs with 79–420 warnings, so the claim "each warning is also an annotation" is false for most
real PRs.
**Fix:** `if: ${{ !cancelled() && github.event_name == 'pull_request' }}`. Executed:
`check-merge-ready.pr_only_steps` still recognises both `!cancelled() && …` and `always() && …`, so the 5-step
accounting does not move. State the annotation cap in the bounds, or emit annotations for the first N only and say so.

### M2 — Medium — `scripts/check-diff-coverage.py:184` — the `self_test` SUBSTRING exempts production functions: changed decision lines are wrongly cleared
`"self_test" in node.name` matches production code. Four manifested scripts have such functions, holding
**14 decision lines** in all:
- `check-diff-coverage.py:self_test_lines` (4) — the tool's own exemption logic;
- `check-selftest-counts.py:run_self_test` (1);
- `check-main-drivable.py:_mentions_self_test` (7);
- `check-ratchet-contract.py:discover_self_tested_nonguards` (2).

End to end, I committed `return True` → `return False` at `check-main-drivable.py:446`, inside
`_mentions_self_test`. Result:
`diff coverage: 0 decision line(s) … across 1 manifested script(s) … — every one is edited by a mutation`.
With `self_test_lines` stubbed to `set()`, the same commit gives `WARN scripts/check-main-drivable.py:446` plus the
deleted-line warning. This is the name-contains shortcut that `check-main-drivable.py:443-445` itself records as
rejected for this exact reason.
**Fix:** exempt only the suite itself: the exact names `self_test`/`_self_test`, plus defs nested inside them. If
helpers such as `_self_test_body` and `_impure_self_test` must also be exempt, list them explicitly. Add a case
with a production function whose name contains `self_test`.

### M3 — Medium — `scripts/check-diff-coverage.py:282-287` — merge-base scope covers only a DELETED script, not the same loss reached by a rename or by deleting only the manifest
This is the XP3 class fixed as one instance. Both runs were executed on real git:
- E2: `git rm scripts/mutations/check-handoff-path.json`, then `if not path.exists():` → `if False:`. Result:
  `0 … across 0 manifested script(s) … — every one is edited by a mutation`.
- E3: `git mv check-handoff-path.py check-handoff-path2.py`, drop its manifest, same weakening. Result: the same
  clean zero. The rename is detected (`git diff -M`), but `p` exists, so `continue`.

Mitigation, which is why this is not High: `EXPECTED_MUTATIONS` forces the same PR to edit `check-plan-code.py`
visibly. That mitigation applied equally to XP3, which was fixed anyway, and the summary line still asserts
"every one is edited by a mutation".
**Fix:** a path is in scope if HEAD has its manifest OR the merge-base has a manifest for `old_path or p`. When
HEAD has no manifest, report the decision lines as uncovered, since every mutation is gone. Add the rename case
and the manifest-only-deleted case.

### M4 — Medium — `scripts/check-diff-coverage.py:250,254` — git's diff is not pinned: a user's `diff.external` or `diff.srcPrefix` gives a clean zero or a mislabelled miss
Executed, each with a committed change to `if not path.exists():`. The default run gives 2 warnings.
- `GIT_EXTERNAL_DIFF=true`: `0 … across 0 manifested script(s) … — every one is edited by a mutation`, rc 0.
- `git config diff.external true`: the identical clean zero.
- `diff.srcPrefix=old/`, `diff.dstPrefix=new/` (git 2.49): the changed line is MISSED. The only output is
  `NOT CHECKED new/scripts/check-handoff-path.py: cannot read the base side`, which names a bogus path and the
  wrong reason.

CI has neither setting, so this is local-only. The docstring advertises local use, and the bet forbids a clean zero
over an unmeasured input.
**Fix:** `git diff --no-ext-diff --no-textconv --src-prefix=a/ --dst-prefix=b/ -U0`. Then add the class fix, which
also catches L1: cross-check `git diff --name-only base...HEAD -- 'scripts/*.py'` against the paths
`parse_diff` ∪ `binary_paths` produced. Any manifested name it lists that was not parsed is NOT CHECKED.

### M5 — Medium — `scripts/check-diff-coverage.py:295,302,156` — two of the bet's NOT-CHECKED arms are unwitnessed, and so is `while`
I severed each line in a scratch copy and ran `--self-test`:
```
SURVIVES  HEAD unparseable not NOT CHECKED   (`if decision_lines(src) is None:` → `if False:`)   48/48
SURVIVES  git show failure not NOT CHECKED   (`if o is None or o.returncode != 0:` → `if o is None:`) 48/48
SURVIVES  while not a decision               (`(ast.If, ast.While)` → `ast.If`)                  48/48
SURVIVES  success suffix always printed      (line 329)                                          48/48
SURVIVES  binary scope `or` → `and`          (line 278)                                          48/48
```
The first two are exactly "a clean zero over something it did not measure". The existing case "a base side that
cannot be read" reaches only the `o is None` arm: its fake returns rc 1 for `merge-base`, so `base_ok` is False and
`git show` is never called. End to end with the first sever, an unparseable HEAD source loses its `NOT CHECKED`.
These arms are correct today and nothing defends them. The PR body and backlog row cite them as delivered.
**Fix:** one case each: an unparseable HEAD source; a merge-base that resolves but a `git show` that fails; a
`while` test; the summary line with warnings present. Add a mutation for each.

### L1 — Low — `scripts/check-diff-coverage.py:124-133` — hunk content that begins `+++ ` is read as a file header
I inserted a docstring line `++ a note in the docstring`, which the diff renders as `+++ a note …`, and changed
`if not path.exists():` further down. Result:
`WARN a note in the docstring (base line 94): … — DELETED`, then
`… across 2 manifested script(s)`. The CHANGED line 95 is missed, and the deleted line is filed under a
nonexistent path. A diff with only added lines after such a line is missed entirely. The control without the
`++` line gives both warnings. The parser does not track `diff --git` / `@@` state. Content `-- ` occurs in real
scripts (`check-anon-exposure.py:469-480`, SQL comments) and is harmless here only because `old` is not reread
after `setdefault`.
**Fix:** treat `---`/`+++` as headers only between a `diff --git` line and the first `@@` of that file. The M4
name-only cross-check would also catch this.

### L2 — Low — `scripts/check-diff-coverage.py:151,223,238` — `ast` line numbers and `splitlines()` disagree with git's `\n` numbering
- A lone CR: `ast.parse` counts `\r` as a line break, even inside a triple-quoted string (executed:
  `'s = """a\rb"""\nif y:'` puts the `If` on line 3). Git does not. I committed `_CR = '''a<CR>b'''` to a
  manifested script, then changed `if not path.exists():`. Result: `0 … — every one is edited by a mutation`.
  The line was MISSED. No current script contains a raw CR (scanned: 0).
- `splitlines()` also breaks on `\x0c \x1c-\x1e \x85 \u2028 \u2029`. **Three manifested scripts today** have a
  line count that disagrees with git's: `check-plan-file-tags.py`, `begin-plan.py` and `observer_log.py`. Executed
  on the real `check-plan-file-tags.py`: changing line 629 to `if not shortfall:` prints
  `WARN …:629: \`if findings:\``. The line number is right, but both the changed and the deleted warning quote the
  wrong text. This is the `splitlines()`-versus-`split("\n")` class already recorded in this project's memory.

**Fix:** use `split("\n")` everywhere. Before `ast.parse`, replace every `\r` not followed by `\n` with a space
(same length, same `\n` positions).

### L3 — Low — `scripts/check-diff-coverage.py:206-209` — difflib's alignment ignores position, so repeated lines can be wrongly cleared
"Survives unchanged" is decided by an LCS that does not know where the edit sits. Executed on `edited_lines`:
- `if a:` / `return 1` / `if b:` / `return 1`. A mutation deletes the `if b` block, anchored by widening backwards
  (`"        return 1\n    if b:\n        return 1\n"` → `"        return 1\n"`) — the idiom
  `check-plan-code.py:1710` describes. Result `{3, 4}`: line 3 (`return 1` under `if a`, untouched) is covered,
  and line 5 (removed) is not. `uncovered` then clears a PR change to line 3.
- Find `"    if a:\n        return 1\n"` → three new lines, where line 4 is again `    if a:`. Result `{3, 4}`:
  the deleted line 2 is uncovered, and the untouched line 4 is covered.

Real corpus: comparing forward and reversed alignment over every manifest edit gives **4 ambiguous edits, 0 that
wrongly clear a line**. One is a block swap in `check-main-drivable.py:2061-2064`, which covers only one of the
two swapped pairs and so produces a false warning.
**Fix:** align by position. Strip the common leading and trailing whole lines of `before`/`after` in order. The
remaining `before` lines are edited, and an empty middle means an insertion. This handles every probe above,
covers both halves of a swap, and passes the existing r1/r2 cases by construction. Add the two cases above.

### L4 — Low — `scripts/check-diff-coverage.py:289-291`, `263` — sources and manifests come from the WORKING TREE, the diff from committed HEAD
Executed: I committed the line-94 change, then added two uncommitted comment lines above it. Result: only the
deleted-line warning. The CHANGED decision line is missed, because line 94 of the working tree is now a different
line. CI is clean, so this is local-only.
**Fix:** read sources with `git show HEAD:<path>` and manifests from HEAD. Or report NOT CHECKED when
`git diff --quiet HEAD -- scripts` fails.

### L5 — Low — `scripts/check-diff-coverage.py:294,297` — a NOT-CHECKED HEAD side also discards the measurable deleted lines
The `continue` skips the `if removed:` block. Executed: an unparseable HEAD plus a deleted `if not path.exists():`
gives only `NOT CHECKED …: it does not parse as Python`. The base side parses, and its deletion is not reported.
**Fix:** record NOT CHECKED for the added side and fall through to the removed side.

### L6 — Low — the PR body, the backlog #251 row and the dashboard entry overstate four points
- "24 mutations … one per round-2 finding": six round-2 findings, five `(r2)` mutations (#7, #21–#24). XL6 (the
  C-quoted Unicode path) has no named mutation. My sever of the octal branch is killed by the r2 Unicode case, so
  the behaviour is defended but the count claim is wrong.
- "Lines inside a `self_test` never warn" really means any function whose NAME CONTAINS it (M2).
- "each warning is also an annotation on the diff" was never observed, and is capped at 10 (M1).
- "a file it can't read, decode or parse … never a silent zero" is refuted by M4 and L2, and its HEAD-parse arm is
  unwitnessed (M5).

The 57 and 32 reproduce exactly, and `:80` is among the 32. "163 and 71" (the pre-narrowing rule) were NOT re-measured.

## Usefulness (task 4)
- `hook-guard-gaps` @ `0b7471d5`: 2 warnings, `check-hook-commands.py:89` and `:90`. Both are lines of ONE
  `raise Malformed(...)` statement that no mutation edits. Real, but counted twice.
- Counting by line inflates every figure: one statement spanning N lines takes N warnings and N of the CAP of 12.
  `session-state.py:113-114` is one `if` test.
- Survey over the last 40 first-parent merges with the HEAD tool: per-PR totals of 32, 12, 6, 12, 23, 80, 420,
  57, 83, 186, 54, 349, 428, 133, 17, 32, 54, 283, 37 (plus two PRs at 1).
- 31 of 110 deleted-line warnings name text that still exists verbatim in HEAD. These are moves and refactors,
  where "nothing will notice it is gone" is likely false.
- At these volumes the warning is a census, not a pointer. This is acceptable for warn-only, but it is the scale
  at which the PR #364 line would be one of hundreds. Consider ranking by "not covered AND inside a function that
  some mutation touches", or reporting statements rather than lines.

## Summary
| # | Sev | Where | One line |
|---|---|---|---|
| M1 | Medium | ci.yml:919 | step skipped whenever an earlier verify step fails — skipped on r1 and r2; annotations never observed; capped at 10 |
| M2 | Medium | :184 | `self_test` substring exempts 14 production decision lines in 4 scripts — clean zero, executed |
| M3 | Medium | :282 | rename or manifest-only deletion drops merge-base scope — clean zero, executed (XP3 instance-not-class) |
| M4 | Medium | :250 | unpinned `git diff`: `diff.external`/`GIT_EXTERNAL_DIFF` give a clean zero; `srcPrefix` gives a mislabelled miss |
| M5 | Medium | :295,:302,:156 | HEAD-parse and git-show NOT-CHECKED arms and `while` survive their severs, 48/48 |
| L1 | Low | :124 | added content line `++ …` read as a header — changed line missed, bogus path |
| L2 | Low | :151,:223 | lone CR shifts `ast` numbering (clean zero); `splitlines` quotes the wrong text on 3 real scripts |
| L3 | Low | :206 | position-blind difflib wrongly clears repeated lines (synthetic); 4 ambiguous real edits |
| L4 | Low | :289 | working-tree sources versus committed diff — dirty tree misses lines |
| L5 | Low | :294 | NOT-CHECKED HEAD side skips the base-side deletions |
| L6 | Low | PR body/backlog/dashboard | "one per r2 finding" (5 of 6), self_test wording, annotation claim, "never a silent zero" |

VERDICT: NOT CONVERGED
