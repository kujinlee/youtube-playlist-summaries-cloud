Reviewed head: c5e3d8caaeab994c94ecd9aa807501f032dcffb0

# Dashboard-retire plan — review round 5, Claude half

Subject: `git diff c5e3d8ca~1 c5e3d8ca -- docs/superpowers/plans/` (Task 13 rewritten, three Task 12
sentences, one carried-findings cell). Round 5 is past the cap: only a BLOCKER is folded; the rest is filed.
Mandate: refute that the new Task 13 is correct and runnable as written.

Fixture: a scratch upstream repo, a clone, and a worktree under the session scratchpad (`r5fx/`). No real
branch was touched.

## Findings

### M1 — Medium — rc 1 means two things in Step 1 (`docs/superpowers/plans/2026-11-24-dashboard-retire.md:822`, `:836`)

The input that breaks it: a missing worktree, or a worktree with a local edit that the checkout would
overwrite. Measured on the fixture:

- `cd <missing dir> && …` returns **rc 1** (`No such file or directory`).
- `git checkout -q --detach origin/master` over a conflicting local edit returns **rc 1** (`would be
  overwritten by checkout … Aborting`).

rc 1 is also L1's "store moved" answer, and the text after it says "On rc 1, L1's message prints the stray
text and the restore command. Repair …". Push mode also runs A1, so an A1 refusal on master (a bad
`docs/asks/` file) is a third rc 1 that this repair text does not fit. The step never PASSES on any of
these inputs, so this is not a blocker. But the shape rule's promise that "that call's own exit status is
the answer" does not hold for rc 1: telling these cases apart means reading stderr. The plan names only
`fetch` (128) and the missing script (2) as controls, and does not mention `cd` or a failed `checkout`.
Fix (filed): say "rc 1 with no `REFUSED` line from the gate is the shell, not the store". Or, following the
task's own SPLIT route, give the gate a single post-cutover entry point with distinct return codes.

### L1 — Low — "any clean worktree serves" is asserted, not checked (`:829`)

The input: a worktree with an uncommitted edit to a file that is the same at HEAD and at `origin/master`.
Measured: `git checkout -q --detach origin/master` returns **rc 0** and keeps the edit. When the edited
file is `scripts/check-ask-store.py` itself, Step 1 runs the working-tree script, not the merged one. So
the claim that "the checkout puts the merged gate file in it" is only true for a clean tree. L1 reads the
committed blob and cannot be fooled by a dirty `docs/dashboard-entries.md`. A1 reads `docs/asks/` content
from the working tree, so a dirty asks file can flip A1. Also, nothing excludes the main checkout. Run
there, the step detaches the owner's main checkout from `master`, and the edits it carries go with it
(the main checkout has uncommitted `docs/` edits today). A clean-tree precondition (`git status
--porcelain` empty) is one more shell link, and the shape rule forbids adding one. That argues for the
SPLIT route if this is ever acted on.

### L2 — Low — Step 5 has no command and no subject pin (`:857`)

"the newest COMPLETED `CI` run on `master` at or after the squash" is a manual observation. It has no
command, and nothing says how "at or after" is decided. The task's shape rule says every command is one
tested call, and Step 5 is outside that rule. Not a blocker: Step 1 already answers L1 over master's tip.
Only the `check-ask-store self-test` half of Step 5 is unique to it.

### L3 — Low — the Test line attributes mutation "L1 compares nothing" to 12.10 (`:864`)

Task 12 Step 8 binds "L1 compares nothing" to 12.3. 12.10 would also go red under that mutation, because
`main([])` would return 0, so the claim is true in substance. But the manifest names 12.3, and a reader who
checks the Test line against the manifest finds a mismatch.

### L4 — Low — the carried-findings cell narrows spec §M1 part (3) without naming the narrowing (`:97`)

The spec row (`docs/superpowers/specs/2026-11-24-dashboard-retire-design.md:337`) says "merges master into
every PR still open". The cell now says "every open PR whose diff still edits the store". The old Task 13
Step 1b already listed only store-editing PRs, so this aligns the cell with the steps and is not a new
behaviour. A PR open at S2 that does not edit the store keeps its green pre-S2 CI and can merge without
ever running the new PR-mode step (C1 + A1). In practice R1 made every such PR carry an entry, so the set
is nearly the same. Name it as a deliberate narrowing, or drop it.

## What was tried and did not break it

- **Store moved before the squash.** The squash's store is S2's pinned header merged with the stray edit,
  so it differs from `LEGACY_STORE_SHA256` and L1 (push mode, `HEAD` blob) is red. The only way the result
  equals the pin is a net-zero change on master, and that is not a moved store. If the two edits conflict,
  GitHub refuses the squash. Step 1 does not pass on this input.
- **Store moved after the squash.** L1 reads master's tip, so it is red. The old squash-parent check passed
  this input, so the rewrite is strictly stronger.
- **S2 not merged yet.** `git ls-tree origin/master scripts/` today holds only `check-dashboard-entry.py`.
  The gate is renamed in S2 (plan `:114`, `:551`), so `python3 scripts/check-ask-store.py` on a pre-S2
  `origin/master` is `can't open file`, rc 2, never a pass. An L1-less copy of the script cannot exist on
  master before S2.
- **Placeholder left unfilled.** `<S2's worktree>` contains an apostrophe, which is a shell syntax error,
  rc 2, as the plan states.
- **Carried state.** No shell variable crosses steps, and no `$SQ` or worktree add/remove is left. Step 2
  relies on the checkout Step 1 left, but S2's own branch also holds the script, so Step 2 runs either way.
- **Task 12's repointed sentences** (`:741–743`, `:798–800`, `:803–805`) agree with the new Task 13.
  Step 6 and Step 10 are the pre-squash `--cutover-check origin/master`, and after the squash the check is
  L1 over master's tip. 12.10 is named as its fixture, in both places. A grep for `Step 1b`, `$SQ`, `SQ^1`
  and "first parent" across the plan finds no stale reference.
- **The entry points exist in the plan.** `main([])` push mode runs L1 (interface `:705–707`, 12.10), and
  `--list-store-prs` is `store_edit_prs` (12.13–12.16). Both are built by Task 12.

No finding makes a step unable to run, or makes one pass while the store is wrong.

VERDICT: CONVERGED
