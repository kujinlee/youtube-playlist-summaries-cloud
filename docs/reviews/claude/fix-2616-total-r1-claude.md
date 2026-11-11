Reviewed head: 7ffda559e62084cd51cfce0fe9f4a797d5ad13d1

# fix-2616-total — round 1, Claude adversarial half

Subject: `git diff origin/master...HEAD` on branch `fix-2616-total` (PR #460, backlog #430).

## Claim under test

"Every TOTAL->2616 replacement dad5971b made, in ANY file, is restored exactly as the parent had it; no
genuine number was changed; and every reference to the renamed case name still binds."

## What I ran, and what came back

1. **Every TOTAL->2616 pair in `dad5971b`, all 39 files.** `git show dad5971b | grep -E '^[-+].*(2616|TOTAL)'`
   gives exactly five `-TOTAL`/`+2616` pairs, all in `scripts/check-plan-code.py`: the "path bound"
   comment in the `EXPECTED_MUTATIONS` history, the "NO TOTAL IS QUOTED" docstring line in
   `progress_line`, the "PATH 3 — TOTAL SHORTFALL" comment, the case name "a TOTAL SHORTFALL prints no
   tally either", and the "long TOTAL unguarded" comment. `+.*\b2616\b` lines in the commit: 5. No other
   file gained a `2616`. (The other TOTAL hit, the review doc's "m3 ... TOTAL corruption", is an
   added line, not a replacement.)
2. **The forward copy.** `git log -S2807 -- scripts/check-plan-code.py` names one commit, `7b2ac79c`
   (PR #443). It turned the same five `2616` into `2807`, and in the same diff ADDED the genuine
   `declared sum 2807 -> 2808` note (`scripts/check-plan-code.py:2341`). That commit changed no other
   `2616`/`2807` in any file. So the commit message's "not 2807" is accurate: on `origin/master` the five
   read 2807, not 2616.
3. **Exact restoration.** Each of the five `+` lines in this PR's diff exists verbatim (`grep -qxF`) in
   `git show dad5971b^:scripts/check-plan-code.py`: 5 of 5 OK.
4. **No genuine number changed.** At HEAD, `grep -nE '2616|2807' scripts/check-plan-code.py` returns only
   line 2341, the real declared-sum note. `git grep '\b2616\b' -- scripts docs/backlog.md` at HEAD returns
   nothing in `scripts/`.
5. **References to the renamed case.** `git grep` over the whole tree for `(2616|2807) SHORTFALL`,
   `NO (2616|2807) IS`, `(2616|2807) path bound`, `long (2616|2807) unguarded` finds nothing outside the
   backlog row's prose. The three manifests containing `TOTAL` (`begin-plan.json`,
   `check-memory-index-budget.json`, `check-review-recorded.json`) use it for byte limits in their own
   subjects; none names a `check-plan-code` case and none was touched by `dad5971b` or `7b2ac79c`. The
   older review docs that quote "a TOTAL SHORTFALL" (`docs/reviews/claude/anchor-precheck-r1-claude.md:53`,
   `docs/reviews/code-mutation-drift-report-contract-r5-claude.md:104`) bind again after this change.
6. **Gates.** `python3 scripts/check-plan-code.py --self-test` in the foreground: `281/281 passed`, rc 0.
   `check-dashboard-entry.py`: ok. `check-docs.py`: OK.

I could not refute the claim.

## Findings

### F1 — Low — FILE — not fix-induced: wording counts one occurrence twice

`docs/dashboard-entries.md` (the new 2026-11-01 entry, first line) and the commit subject say "Five
comments and one test name". There are five occurrences in total: four comments and one case name. The
backlog row's own wording ("five occurrences restored") is correct. Input: count the `-`/`+` pairs in
`git diff origin/master...HEAD -- scripts/check-plan-code.py`, which gives 5, not 6. Cosmetic only.

### F2 — Low — FILE — not fix-induced: the row's falsifier could not see the defect it closes

Backlog #430's FAILS IF is `grep -n 2616 scripts/check-plan-code.py`. On `origin/master` that grep was
already empty, because PR #443 had moved the five to `2807`, so the falsifier was passing before the fix.
The closing note explains the 2807 move, which is enough for this row. It is worth noting as one more case
of a falsifier keyed to a literal value a later replace can move.

## Verdict

No BLOCKER. Both findings are wording and need no fold before merge.

VERDICT: CONVERGED
