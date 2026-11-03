Reviewed head: c00590ea2dee27360d0a18ab9124cbf6ad2f4ba2

# Round 5 — `merge-delta` (PR #491, backlog #426) — Claude half, final-tree check

REVIEW GAP: codex — alternation. Round 5 runs ONE half; round 4 ran the Codex half.

Scope: `git diff 98e7877d..ffee496a` (the r4 fold), plus `ffee496a..c00590ea` (the master merge).
Read: `docs/reviews/codex/merge-delta-r4-codex.md`, `docs/reviews/coordinator/merge-delta-r4-coordinator.md`.
This round is under the round cap (`docs/review-method.md` §0 Q4c), so findings are FILED unless they are a BLOCKER.

## What I checked, and how

1. **The master merge is docs only.** `git diff --name-only ffee496a..c00590ea | grep -v '^docs/'` returns
   nothing. All 12 changed files are under `docs/`. Confirmed.

2. **No git read is still in text mode.** `grep -n 'text=True\|subprocess\.\(run\|check_output\|Popen\)'
   scripts/check-review-recorded.py` finds three hits:
   - `:1056` is the docstring.
   - `:1063` is `_run_git` itself, which captures bytes.
   - `:2369` and `:2772` are self-test fixture runners. Both capture bytes; `:2369` decodes with
     `surrogateescape` on purpose, and `:2772` is `hash-object` fed an encoded input.

   No `check_output` and no `Popen`. `_git`, the isolated runner, `changed_paths` and `added_paths`
   (the shallow check, both `merge-base` calls and both diffs) all go through `_run_git`. The two
   imported modules (`check-dashboard-entry.exemption_reason`, `check-review-rounds.has_gap_line`) are
   text parsers and run no git. Confirmed.

3. **The bytes conversion changes no behaviour except the intended one.**
   - Line ends: `git_text` decodes with no newline translation. Every non-`-z` consumer (`rev-parse`,
     `merge-base`, `--is-shallow-repository`, `hash-object`) still calls `.strip()` on a `str`, so its
     trailing `\n` goes exactly as before. On POSIX, text mode only translated `\r` and `\r\n`, so the
     sole difference is that CRs inside names now survive. That is the fix.
   - `-z` splitting: `split_nul`, `parse_ls_tree` and `parse_merge_tree` still receive `str` and
     split on `"\0"` as before.
   - Error messages: `stderr` is decoded by `git_text` before it is formatted, so no `b'...'` repr
     can leak into a CANNOT RUN line. Confirmed by reading `_run_git` (`:1063-1064`).
   - `**kw` passthrough: the only `kw` callers are the isolated runner (`cwd=`, `env=`). No caller
     passes a `str` `input=`, which bytes mode would reject.

4. **The narrowed predicate breaks no legitimate clear.** I derived the narrowing's premise by hand,
   case by case, to see whether an honest lookup can reach "both absent":
   - **Branch adds `p`, round sees it, branch deletes it.** The merge base lacks `p` and HEAD lacks
     it, so `p` is not in the delta and never reaches `master_explains`.
   - **Master deletes `p` and the branch merges master.** `onto` lacks `p` and HEAD lacks it, so `p`
     is again not in the delta.
   - **Stale `--base`.** `onto` holds `p` and HEAD lacks it, so the merge keeps `p`: present versus
     absent, which was charged before the fold and still is.
   - **Every remaining case.** Being in the delta with HEAD lacking `p` forces `onto` to hold `p`.
     Being changed since the round forces the round's commit to hold it. A clean three-way merge of
     two sides that both hold a path keeps it.

   So "both absent" never happens honestly, and the r4 docstring (`:955-961`) is right. PR #487's
   shape still passes in the self-test: `#426, PR #487's shape: the genuine change is charged, master's
   two files are not`. The control `merge-delta r4 control: ...while a present HEAD equal to the
   merge is still explained` passes too.

5. **Every failure still requires a round.** `master_explains` only got stricter. `None` gives
   False, a conflicted path gives False, and an absent HEAD now always gives False, so no input that
   charged before r4 clears now. The fold also took `check-review-recorded.py` out of `MAIN_DEBT`
   in `check-main-drivable.py`, and that is earned: the new CLI cases drive `main` in-process over a
   constructed repository, and `check-main-drivable.py` passes.

## Findings

**F1 — Low — BLOCKER: no — pre-existing, not introduced by this fold.**
`scripts/check-review-recorded.py:1461` (`split_nul`) drops every NUL record whose name is all
whitespace (`if ln.strip()`).

- **Fixture:** a branch whose only change is a top-level file named ` ` (one space) or `\t`.
  `split_nul("lib/a.ts\0 \0\t\0")` returns `['lib/a.ts']`, measured by loading the module.
  `guarded_changes([" ", "\t"])` returns both names, so the gate would charge them if it ever saw
  them. It does not see them, so a branch that adds only such a file reads as having no code and
  clears without a round.
- **Why not a BLOCKER:** the name is adversarial. Nothing in this repo executes a file whose name is
  only whitespace, and a name nested under a directory (`lib/ `) is kept. It also predates the fold:
  `git log -S` puts the filter at `b7a4de7c`. In text mode a top-level `\r` name was dropped too,
  because it became `\n`.
- **Fix:** filter `if ln`, not `if ln.strip()`. `-z` output's only empty record is the trailing one.
- **Disposition:** FILE.

No other finding. I tried to refute each of the four hypotheses in the brief, and none survived.

## Commands and results (on c00590ea, worktree clean apart from an untracked hook log)

| Command | Result |
|---|---|
| `python3 scripts/check-review-recorded.py --self-test` | **285/285 passed**, rc 0, 10.8 s |
| `python3 scripts/check-main-drivable.py` | `D2 OK`; 61 guards, 54 in population, rc 0 |
| `python3 scripts/check-ratchet-contract.py` | `ratchet contract OK`, rc 0 |
| `python3 scripts/check-fixture-git-isolation.py` | ok, 91 self-tests isolated, rc 0 |
| `python3 scripts/check-fixture-variation.py` | `fixture variation OK` |
| `python3 scripts/check-plan-code.py --self-test` | 278/281: the 3 reds are all `node_modules/typescript is missing` in this worktree. That is the environment, not the PR; CI has `node_modules` |
| mutation sweep | **NOT RUN by me**, per the brief; the fold reports 109/109. No finding of mine needs a sweep to settle it |

VERDICT: CONVERGED
