Reviewed head: 98e7877d82566261f881f2c3803297886d13d296

> **Filed by the r4 fold of `merge-delta` (PR #491, backlog #426).** Triggered by **THRASHING**, by the letter of
> `docs/dev-process.md` → *Phases*: two consecutive rounds carried a finding caused by the previous round's own fix, in
> one component (`master-side`). Round 2's X-M1 (`merge.text.driver`) was caused by round 1's `-c merge.default=text`;
> round 3's C-L1 (the temp-dir leak) was caused by round 2's `_isolated_git`.
>
> **Adopted in the r4 fold:**
> - **3c, the recommendation:** `master_explains` now returns `not is_absent(now) and now == want`, so absent == absent
>   never clears. The derivation (§3c) was checked against the gatherer; no counterexample was found (the fold report
>   says why a branch that ADDS a file does not reach it). A case and a mutation pin it.
> - **§4's first bound:** `master_explains`' docstring no longer claims a both-touched file was "already reviewed on
>   master's own PR"; it states the same-file composition waiver.
>
> **Not adopted in r4 (left to the coordinator):** §4's second bound (the isolated repository's init-written
> `core.ignorecase` / `core.precomposeunicode`, a docstring inaccuracy) and §5.1 (a committed `.gitmodules` with
> `ignore = all` hides a gitlink bump from `diff_argv`; latent, 0 gitlinks today, pre-existing, outside this component).

# Phase 6 architecture review (narrow, triggered by thrashing): the "master explains it" clear path in `scripts/check-review-recorded.py` (PR #491, backlog #426)

Scope: `master_explains`, `_master_side`, `_isolated_git`, `isolated_env`, `merge_tree_argv`, `merge_onto`,
`_final_entries`, `ls_tree_argv`, `select_entries`. Read only. Measurement scripts are in this scratch directory
(`measure2.py`, `why.py`, `fx/`), outside the repository.

## 1. Thrashing or prose floor?

**Thrashing by the letter, and the stream is design-caused. It is not a prose floor.** Per finding:

| Round | Finding | Fix-induced | Route | Needed which feature to become a false CLEAR |
|---|---|---|---|---|
| r1 | X-H1 failed HEAD `ls-tree` → `{}` | no | lookup failure | **absent == absent arm** in `master_explains` |
| r1 | C-M1 `.gitattributes` merge driver | no | merge-engine configuration | merge-tree's configurability |
| r2 | X-M1 `merge.text.driver` | **yes** (r1's `-c merge.default=text`) | merge-engine configuration | merge-tree's configurability |
| r2 | X-M2 system gitattributes | no | merge-engine configuration | merge-tree's configurability |
| r3 | C-M1 pathspec magic / NFD in `ls-tree -- <path>` | no | lookup under another name | **absent == absent arm** (both sides miss together) |
| r3 | C-L1 temp-dir leak | **yes** (r2's `_isolated_git`) | cleanup | none (fails toward charging) |

Every false CLEAR came from one of two structural features. Neither is a fix-on-fix chain:

- **(A) The clear is an EQUALITY between two git-produced values, and the predicate includes "both absent".**
  A lookup that fails or misses on both sides gives two equal ABSENT values, and that reads as "explained".
- **(B) The right-hand value comes from a content-merge engine that reads configuration and attributes.**

## 2. The class

The suspected class ("machinery whose behaviour depends on ambient state and on how inputs are named") is right but
too broad to act on. It is really two sub-classes, and they behave differently under redesign:

- **A. Lookup lies read as absence, and absent == absent clears.** X-H1 and r3 C-M1 are in this sub-class.
  **It can be removed structurally (see 3c).**
- **B. The synthetic merge is configurable.** r1 C-M1, r2 X-M1 and X-M2 are in this sub-class. **It is inherent
  to the purpose**, because clearing a file both sides touched needs a content merge (measured in 3a). The isolation
  closes the known sources as a class, not one source at a time.

## 3. Can a redesign remove it?

### 3a. The two narrower rules in the brief: they keep 0% of the purpose (derived, and confirmed by measurement)

`tail_candidates` already intersects with `branch_delta = diff(merge-base(base, HEAD), HEAD)`. That intersection
was there before #426. So a path whose HEAD entry equals master's (`onto`'s) entry is **never a candidate**.

- **Option "HEAD == master's entry AND reviewed == merge-base's entry".** The first conjunct puts p outside
  `branch_delta`, so p never reaches `master_explains`. It clears nothing the pre-#426 rule did not already clear.
- **Option "master changed p and the round did NOT touch it".** If R.p == mb.p and p is still in
  `after ∩ branch_delta`, then HEAD.p differs from both R and master. The branch, or an evil merge, changed p after
  the round, and p must be charged. It clears nothing new either.

**Measured** with the script's own pure functions (`tail_candidates`, `round_tail`, `_master_side`) over the
**last 40 merged PRs** (#448 to #490), at every merge of master on each PR's first-parent chain:

- Of those 40 PRs, 19 had a master-merge commit on a branch with guarded changes.
- At 6 of those merges, the branch was strict-clear just before the merge.
  - 3 stayed clear under the pre-#426 rule, through the intersection alone: #484 `240040b3`, #476 `afc81986`,
    #463 `15d8cfda`.
  - 3 were charged under the pre-#426 rule: #487 `6b5d8b6b`, #453 `61d7fb6a`, #452 `c41ae92c`.
- **In all 3 charged cases, every charged path was touched by BOTH the round and master.** So the narrow options
  clear **0 of 3**.
- **#426's merge-tree rule clears 1 of 3** (#487: `.github/workflows/ci.yml`, `scripts/check-plan-code.py`, clean
  three-way merges).
- The other two were **real conflicts** in `scripts/check-plan-code.py` (and in `check-fixture-variation.py` for
  #452), confirmed by `merge-tree` of each merge's own parents. Those are charged by design, correctly.

Purpose kept: merge-tree design **1 of 3**; narrow options **0 of 3** (n = 3; small).

Lines: the narrow options would delete `merge_onto` through `_master_side` (~123 lines), `master_explains` and
`parse_merge_tree` (~34), and most of the PR's +688 self-test/code and +378 mutation-manifest lines. What they
delete is the purpose, not just the risk. So a narrow option **is a revert in all but name**.

### 3b. Revert

A revert would delete the PR's script delta, but keep `ls_tree_argv` and `select_entries`. The pathspec miss
predates #426, and it also reaches the strict `same()` arm: a dirty-overlay deletion plus a magic name gives
absent == absent there too. Cost: the 1-in-3 measured case pays an extra round again.

### 3c. A targeted redesign that removes sub-class A: delete the absent/absent arm of `master_explains`

**Derivation: for an honest lookup, absent/absent in `master_explains` is unreachable.**

1. `master_explains` is reached only for p ∈ `after` \ `reviewed`, so R.p ≠ HEAD.p.
2. Suppose HEAD.p is absent. Then R.p is present (from 1).
3. p ∈ `branch_delta`, so onto.p ≠ HEAD.p, so onto.p is present.
4. A clean three-way merge of two sides that BOTH hold p cannot produce an absent p. No side deleted it, and a
   rename needs a deletion on one side.

So "both absent" is produced **only** by a lookup that lied. That is exactly X-H1 and r3 C-M1.

Replacing `(is_absent(want) and is_absent(now)) or now == want` with `not is_absent(now) and now == want` turns
every future lookup lie into a false CHARGE (fail closed), whatever route it arrives by. The cost:

- About one line.
- Flipping the pure case at `scripts/check-review-recorded.py:2304`, which today pins `({}, ∅), ABSENT → True`.
- **NOT RUN:** the self-test under this change. I did not modify the tree. The derivation is reasoning, not a run.

Keep the absent/absent arm in `round_tail.same()`. There it is a legitimate reviewed deletion.

## 4. Recommendation

**KEEP the merge-tree design, and narrow ONE predicate: drop the absent/absent arm of `master_explains` (3c).**

- Sub-class B is inherent to the purpose. The isolation closes it as a class, and I found no live source of it (see 5).
- Sub-class A is removable for one line, and it is the sub-class that produced the two lookup-route false CLEARs.

Also fix two stated bounds:

- `master_explains`'s docstring says "already reviewed on master's own PR". For a both-touched file, the same-file
  composition was reviewed by **nobody**: master's reviewer never saw the branch's hunk, and the round never saw
  master's. That is the semantic-composition waiver `tail_candidates` already states for cross-file composition,
  now extended to the same file. State it as a bound; do not claim review.
- `_isolated_git` / `isolated_env` say the repository has "no config". `git init --bare --template=` on macOS
  writes `core.ignorecase = true` and `core.precomposeunicode = true` (measured, git 2.49).

## 5. Open routes (hypotheses tested)

1. **OPEN, same class, OUTSIDE this component and pre-existing: a branch-committed `.gitmodules` with
   `ignore = all` hides a gitlink change from `diff_argv`'s `git diff`.**
   - Fixture (`fx/r`):
     1. Commit a gitlink at `lib/sub`, plus a `.gitmodules` with `ignore = all` (the round sees both).
     2. Commit `a2.py`.
     3. Bump the gitlink.
   - `git diff --name-only -z --no-renames R HEAD` prints `a2.py` only.
   - With `--ignore-submodules=none` it prints `a2.py` and `lib/sub`.
   - Removing the worktree `.gitmodules` does not restore it: the hiding `.gitmodules` is read from the commit, not
     the worktree.
   - So the bumped gitlink is in neither `after` nor `branch_delta`, and it is never charged. The r4 Blocking note in
     `_final_entries` shows that gitlinks are meant to be covered.
   - Fix: add `--ignore-submodules=none` to `diff_argv`.
   - Today the repo has 0 gitlinks and no `.gitmodules`, so this is latent. #426 does not widen it.
2. **Tested, not a finding: the init-probed `core.ignorecase=true` in the isolated repository.** In a case-only
   rename fixture (`fx/c`), `merge-tree` gave the identical tree and conflict list under `core.ignorecase=true` and
   `false`. One fixture only. It is a documentation inaccuracy (section 4), not a measured route.
3. **Reasoned, not run:**
   - A verdict `head` that is a revision expression (a ref name or `:/regex`) resolves in the real repository but
     not in the ref-less isolated one. That gives `None`, the strict rule (fail closed).
   - Differences in the author's `diff.algorithm` / `merge.renames` make HEAD differ from the isolated merge. That
     gives a false CHARGE, never a false clear.

## 6. Measured versus inferred

- **MEASURED:**
  - The 40-PR replay (19 merges; 6 clear before the merge; 3 charged; all 3 both-touched; merge-tree clears 1, by
    the script's own functions).
  - The 2 uncharged-by-design cases are real conflicts.
  - The `.gitmodules ignore=all` hiding, and `--ignore-submodules=none` restoring.
  - The isolated repository's init-written config.
  - `ignorecase` had no effect in one merge fixture.
- **DERIVED (reasoning, not run):**
  - Both narrow options are dominated by the existing `branch_delta` intersection.
  - absent/absent in `master_explains` is unreachable for an honest lookup.
- **NOT RUN:** the self-test and mutation sweep with 3c applied.
- **Replay caveats:**
  - Evaluated at the branch's own merge commit, not at GitHub's synthetic merge ref.
  - `onto` = merge-base(merged master parent, merge commit).
  - "Clear before" uses merge-base(parent, the base at squash time).
  - n is small (3 charged cases).
- **Side observation:** 2 of the 3 measured extra-round triggers were real conflicts in `scripts/check-plan-code.py`,
  the shared pin/count file. #426 cannot help those; the count-pool work (#487) is the relevant lever.
