Reviewed head: f84fce2bee53e8f8a55583b422def42c3a87df3d

# merge-delta r1 — Claude half (adversarial)

Subject: backlog #426, PR #491, `scripts/check-review-recorded.py` — a guarded path not handed over dirty
is cleared when HEAD's entry equals `merge-tree --write-tree <round's commit> merge-base(base, HEAD)`.
Mandate: find a FALSE CLEAR. Every claim below comes from a real git fixture I built under the
scratchpad. The harness imports the script and drives `round_tails` / `_master_side` over a real
repository, the same way the suite's own `_tails_at` does.

## Findings

### M1 (Medium) — a prose-path `.gitattributes` with `merge=union` clears a CONFLICTED guarded file, in CI's own shape

`scripts/check-review-recorded.py:1091` (`_master_side` → `git merge-tree`). `merge-tree` applies
gitattributes merge drivers from the working tree. In CI the working tree is HEAD, so the branch
chooses those attributes. `docs/.gitattributes` is prose (`is_prose` → True), so committing it is
never charged. A `** merge=union` there makes `merge-tree` resolve a real conflict on guarded gate
code under `docs/superpowers/specs/m4/` CLEANLY. The conflicted set is then empty, and HEAD (the
author's merge, made under the same attribute) equals the synthesised tree. Trap 1's invariant ("a path
that merge CONFLICTED is never cleared", docstring at :82-93 and `master_explains`) is bypassed.

Fixture (S15): base `G=docs/superpowers/specs/m4/gate.sql` (20 lines). Branch sets line 2 to `BR 2`, and
that commit is the reviewed round R. Master sets line 2 to `M 2`. Branch commits `docs/.gitattributes` =
`** merge=union`, then `git merge master` (rc 0, file = `BR 2\nM 2`).
- `round_tails` → tail `[]`, `tail_verdict` rc 0. It is the same on a synthesised merge ref (detached
  master, `merge br`). It is the same with `docs/superpowers/.gitattributes`.
- CONTROL: the identical union resolution typed by hand with no attributes file → tail
  `['docs/superpowers/specs/m4/gate.sql']`, rc 1. So the attribute is the cause.
- Before this PR the path was in `after ∩ branch_delta` and was charged. The hole is new.
- Bound: the cleared content is an interleaving of the two reviewed sides, not new tokens. But it is
  exactly the "conflict resolution is the branch's own choice" case the design says it never clears.

Locally, `.git/info/attributes` and `core.attributesFile` (user-global) have the same effect, along
with an uncommitted worktree `.gitattributes` (S12b: tail `[]`, merge-tree rc 0). That part is
local-only, because CI has none of those.

Fix, measured: `git --attr-source=<empty tree> merge-tree …` (or `-c attr.tree=<empty tree>`) makes the
same fixture report rc 1 (conflict) again. `.git/info/attributes` still applied under `--attr-source`
(rc 0), so also pass `-c core.attributesFile=/dev/null` if local parity matters. Git without
`--attr-source` (older than 2.42) fails rc 129 → `None` → strict, which is the safe direction. Add a
real-git case for S15.

### M2 (Medium) — the call site in `main` that computes `onto` is unprotected. `onto = HEAD` clears EVERY round, and the suite stays green

`scripts/check-review-recorded.py:1443-1445`. No case calls `main`. The real-git fixture `_tails_at`
(:2226) recomputes `merge-base master HEAD` itself, so it copies the call site rather than exercising
it. Mutant: `_git("merge-base", args.base, "HEAD")` → `_git("rev-parse", "HEAD")` gives **217/217
passed**. Under that mutant, `merge-tree(R, HEAD)` for any ancestor R is HEAD's own tree, so every
non-dirty guarded path is "explained" and every post-review commit is cleared. That is a total false
clear from a one-token regression nobody would see. Any wrong ref that contains the branch's commits
(`HEAD`, the branch tip, `origin/<branch>`) does the same. Fix: one case that drives `main` (or a
helper extracted from it that both `main` and the fixture call) over the real fixture repository,
with a post-review branch edit that must be charged. Add a manifest entry for the `merge-base` line.

### L1 (Low) — the `ls-tree` failure check in `_master_side` is unmutated and untested

`scripts/check-review-recorded.py:1096-1097`. Mutant `if ls.returncode != 0: return None` → `if
False:` gives **217/217 passed**. Consequence: a failed `ls-tree` yields `parse_ls_tree("") == {}`, so
`want` is ABSENT for every path. A guarded file that HEAD DELETED after review is then "explained"
(`is_absent(want) and is_absent(now)`). It is a narrow false clear behind a git failure, and this is the
fail direction the PR promises never to take. Fix: a case with an injected `git` whose `ls-tree`
returns rc 128, asserting `None`, plus a manifest entry.

### L2 (Low) — the real-git "trap 1" case does not exercise the conflict exclusion

`scripts/check-review-recorded.py` self-test, case "#426 trap 1: a merge whose conflict RESOLUTION
edits a guarded file is charged". The resolution (`RESOLVED 2`) differs from the synthesised
conflicted blob (which holds markers), so `now != want` charges it with or without `p in conflicted`.
Measured: the manifest mutant "a CONFLICTED path is explained like a clean one" reds exactly 1 case,
the pure one. The pure case is enough to kill the mutant, so this is not a coverage hole. But the
real-git case's name claims more than it tests. M1 is the real-git shape where the conflicted set is
the only thing standing, and it is the case to add.

## Hypotheses tried and REFUTED (no false clear)

| # | Fixture | Result |
|---|---|---|
| S2 | edit before review; master edits another hunk; merge; branch edits the same file again | charged `['lib/a.ts']` |
| S3 | two merges of master, nothing else | `[]` (correct) |
| S3b | sneak edit on a master-touched file between two master merges | charged `['lib/b.ts']` |
| S4 | rebase after review (R not an ancestor) | unusable=1, rc 2 |
| S5/S5b | master renames the file the branch edited; clean merge / plus a sneak edit | `[]` / charged `['lib/a2.ts']` |
| S6 | post-review rename by the branch | charged both paths |
| S7 | master deletes an untouched file | `[]` (correct) |
| S8/S9 | modify/delete and rename/rename resolved by keeping R's exact content | `[]`, but the path is unchanged since R (not in `after`), the same as the strict rule. Not new |
| S10 | modify/delete resolved with an edit | charged |
| S12a/c | union-by-hand resolution; `.gitattributes` committed at ROOT after review | charged (root `.gitattributes` is guarded) |
| S13 | review after an earlier master merge, then a second merge (base = earlier merge) | `[]` (correct) |
| S14/S14b | CI synthesised merge ref with / without a sneak on the branch tip | charged / `[]` |
| S1 | branch hand-applies master's hunk WITHOUT merging master | charged. A false POSITIVE (onto is merge-base, not master's tip), safe direction, by design |
| shallow | depth-1 clone: R missing, `merge-base` rc 1 → `onto=None`; `_master_side` → `None` | strict. CI `verify` checks out with `fetch-depth: 0` (`ci.yml:53`), and the step passes `--base origin/$GITHUB_BASE_REF` (`ci.yml:968`) |

Fail-direction audit: `merge-tree` rc ∉ {0,1} → `None`. Empty output → `None`. `onto=None` →
`None`. An unresolvable merge base → `None`, and it is refused earlier by `changed_paths`. Git too old
for `--write-tree` → rc 129 → `None`. All of those fail toward REQUIRING a round. The exceptions are
L1 (`ls-tree` failure) and M2 (a wrong but successful `onto`).

Stacked PRs (base = a feature branch): the "already reviewed on master's own PR" premise does not hold
for a feature base. But `tail_candidates` already subtracts base-side paths on the same premise, so
this is a widening of a pre-existing assumption, not a new one. Noted, not filed.

## Commands run

- `python3 scripts/check-review-recorded.py --self-test` → `217/217 passed` (1.95 s)
- manual mutant, `main` `onto` = `rev-parse HEAD` → `217/217 passed` (survives, M2)
- manual mutant, `_master_side` `ls-tree` rc check removed → `217/217 passed` (survives, L1)
- manual mutant, `_master_side` `not onto or not paths` guard removed → TypeError crash (killed)
- each of the 10 `#426`-touching entries in `scripts/mutations/check-review-recorded.json` applied to a
  copy → every one reds its named `expect` case(s)
- `python3 scripts/check-plan-code.py --mutate . --only scripts/check-review-recorded.py` → rc 1,
  `CANNOT RUN — node_modules/typescript is missing`: **NOT RUN** (this worktree has no node_modules)
- fixture scripts S1-S15 plus the shallow probe, over temp repositories (git 2.49.0), results as above

VERDICT: NOT CONVERGED
