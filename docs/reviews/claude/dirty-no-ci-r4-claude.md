Reviewed head: a6e075630b28dd01c020d834e1b24a6a85de9939

# dirty-no-ci r4, Claude half (a fallback for the Codex half: Codex is short of memory on this machine)

Branch `dirty-no-ci`, PR #539, backlog #545. Diff `origin/master...HEAD`, weighted on `a6e07563` (r3 plus the
Phase 6 fold). Read first: `docs/reviews/architecture-review-2026-11-08-dirty-pr-states.md`. Mandate: REFUTE.
Stop condition (§6 of that review, and `review-method.md` §0 Q4c): from r4 a non-BLOCKER is FILED, and a new PR
state needs a measured real case. Nothing under `.claude/plans/` was read.

## What was run (all at the reviewed head, in the `dnc` worktree)

| Check | Result |
|---|---|
| `python3 scripts/check-stalled-work.py --self-test` | `225/225 self-test cases passed`, rc 0 |
| `anchor_problems` (from `scripts/check-plan-code.py`) over EVERY manifest that `load_manifests` reads | `[]`: no orphaned or ambiguous anchor |
| Every `expect` in `scripts/mutations/check-stalled-work.json` against the live case labels (a staged copy with `if got == want` forced false, so every label prints as `[FAIL]`, read with `parse_fail_names`) | 225 labels, 225 distinct; 0 expects that do not resolve to exactly one case |
| Pin `scripts/mutations/expected_mutations.py` against the manifest | 133 = 133 |
| A fuzz of `head_has_run`: 200,000 random suite pages (non-dict nodes, `{}`, null/string/list/0/False runs, events `pull_request`/`push`/None/`PULL_REQUEST`, totals equal/±1/`True`/`"3"`) | 0 cases where it returned `False` while a `pull_request` node was present, any node was malformed, or the page was incomplete |
| 6 mutation spot-checks by the harness's rule (below) | 6 of 6 rc 1, every `expect` named exactly once |

## The four questions

**1. Can DIRTY-NO-CI fire when the head HAS a `pull_request` run?** Not found. `pr_item`
(`scripts/check-stalled-work.py:528`) needs `conflicting` and `headRun is False`. `conflicting` is set only for
`baseRefName == "master"` (`own_prs`, :499-502), so a non-master base can never reach it. `head_has_run` (:424-453)
returns `False` only when gh's last commit IS the head oid (an emptied, non-hex `headRefOid` gives `None`), `nodes`
is a list and `totalCount` a non-bool int, no node has event `pull_request`, every node passes `suite_node_ok`
(:413-421), and `totalCount == len(nodes)`. A malformed node placed BEFORE a `pull_request` node raises
`AttributeError` inside the `any(...)`, which is caught as `None`, never `False`. Pagination: more than 20 suites
leaves `total != len(nodes)`, so `None`. The fuzz above found no counterexample. Both workflows
(`.github/workflows/ci.yml:14-16`, `schema-gates.yml:113-115`) trigger `pull_request` on `branches: [master]` with no
`paths` filter, which is what `PR_CI_BASE = "master"` assumes. See R4-F4 for the one timing window I could not rule
out, which is unmeasured and not a malformed input.

**2. Can an UNMEASURED read hide or suppress any other stalled-work state?** No. Per PR, DIRTY-NO-CI is returned
before the UNMEASURED item is built (:528-530), and the item is returned only in the two places that would
otherwise return `OK` (:547, :553). An undated draft is still UNKNOWN-DRAFT (:545-546), a stale one STALLED-DRAFT
(:550-552); both are pinned by `545 P6: a STALE draft that is UNMEASURED is STALLED-DRAFT, and an UNDATED one is
UNKNOWN-DRAFT`. Across items, UNMEASURED is not in `STALLED_STATES` (:140), so `render` does not count it and the rc
is unchanged; it is not in `HOOK_TIER` (:164-165), so `hook_block` (:683) never shows it, and its line starts with
`UNMEASURED`, not `NOTE`, so `hook_block`'s `notes` filter (:685) does not forward it either. No cap slot, no
summary count, no rc: it cannot crowd out or replace anything.

**3. Does anything deleted leave a dangling reader, orphaned case or orphaned anchor?** No. `git grep` for
`DIRTY-UNSEEN`, `UNKNOWN-MERGE`, `MERGE-PENDING` and `MERGE_GRACE` outside `docs/reviews/`, the dashboard log and
the backlog finds only the history comments in `scripts/mutations/expected_mutations.py:1886-1896`. No other script
or hook reads the stalled-work statuses (`.claude/hooks/stalled-work.sh` forwards the block as text). The manifest
has no anchor on deleted text (`anchor_problems` is empty) and every expect names a live case (table above).
`mergeUnknown` is still produced by `own_prs`, carried by `pr_fact`/`items_from`, and read by `pr_item` (:537).

**4. Mutation spot-checks.** Each in a `stage_tree` copy, the entry's edits applied, `run_suite`, then
`parse_fail_names`:

| Entry | rc | Each expect named once | Fails exactly equal to expects |
|---|---|---|---|
| `545 r3: a suite node with NO workflowRun key reads as a null run` (new) | 1 | yes | yes (both r3 cases) |
| `545 r3: a workflow run with no string event reads as a well-formed run` (new) | 1 | yes | yes |
| `545 P6: UNMEASURED enters the hook's first tier, so it shares the block with the DIRTY line` (new) | 1 | yes | yes (both P6 cases) |
| `545 P6: an UNMEASURED line hides an UNDATED draft` (new) | 1 | yes | yes |
| `545 P6: the undated OK point drops the UNMEASURED line` (new) | 1 | yes | no: 2 more red (`545: a conflict whose head run is UNKNOWN ...`, `545 P6: an UNKNOWN head is UNMEASURED at any age ...`) |
| `545 r2: an UNSEEN head run gets the no-CI diagnosis and its forced merge again (Codex R2-F1)` (re-bound) | 1 | yes | no: 6 red, the expect among them |

The harness's rule (`run_mutations`, `scripts/check-plan-code.py` around :2085) is that each `expect` resolves to
exactly one red case; extra red cases are allowed. All 6 pass it. The control run of the staged tree was rc 0 with
no failures.

## Findings

### R4-F1 — Low — backlog #545 is ticked DONE while its own text says r4 is still owed

`docs/backlog.md:526`. The row reads `✅ (was 🟡)` and `✅ **DONE 2026-11-08 on dirty-no-ci.**`, and the same cell
ends `Remaining: r4 (Codex) on the fold.` Input: the row as committed at the reviewed head. Result: a reader of the
backlog (and `check-backlog-closure.py`, which keys on `✅`) sees the row closed before the review that could still
reopen it has run. The house rule is that the merge tick rides in the PR, so the tick itself is expected; the stale
"Remaining" clause is what contradicts it. Filed: fix the trailing clause at the next fold or at merge.

### R4-F2 — Low — "DIRTY-NO-CI is the ONLY PR state in any tier" is false as written

`scripts/check-stalled-work.py:162` (comment) and the case label at :1309 (`... DIRTY-NO-CI is the only PR state in
either`). Input: `HOOK_TIERS` at :164. Result: tier 1 holds `STALLED-DRAFT` and `UNKNOWN-DRAFT`, which are PR
states (`pr_item` returns them, kind `pr`). The case only passes because it removes those two by hand (:1312)
before comparing. The intended claim is "the only PR state this backlog row adds". Wording only; the code is
right. Filed.

### R4-F3 — Low — `hook_block`'s docstring still lists the old tier order

`scripts/check-stalled-work.py:672-673`: "Most urgent first, by tier — unpushed tips and drafts, then unfolded
halves, then MERGED cleanup". Input: `HOOK_TIERS` at :164, which puts `("DIRTY-NO-CI",)` first since r1's fold.
Result: the one docstring that describes the cap's order omits the tier this branch added in front of it. Filed.

### R4-F4 — Low — a fix push might read as DIRTY-NO-CI for one prompt if GitHub's `mergeable` lags the push (NOT MEASURED)

`scripts/check-stalled-work.py:528` with `head_has_run` :449-453. Input (hypothetical): the owner merges master into a
DIRTY PR and pushes; on the next prompt GitHub still reports the PR's previous `mergeable: CONFLICTING`, and the
new head has a complete page with no suites yet (`totalCount 0`) or only the `cursor`/`claude` app suites. Result:
`headRun False` plus `conflicting` gives DIRTY-NO-CI with the remedy "merge origin/master into the branch and
push", which the owner has just done. I did not reproduce this: I could not observe whether GitHub serves the
pre-push `mergeable` after a head change or resets it to UNKNOWN (the latter would make it UNMEASURED, which is
fine). It costs at most the prompts until GitHub settles, and it is not a malformed input reaching the hook. Per
§6 of the Phase 6 review no state is proposed; if anyone measures a stale CONFLICTING after a push, the cheap fix is
to read it as UNMEASURED while the head has 0 suites. Filed as a measurement to take, not a defect.

## Not findings

- A head whose commit message carries `[skip ci]` and conflicts would be DIRTY-NO-CI. That head genuinely has no
  `pull_request` run, so the report is true; the remedy (a new merge commit) also produces CI. Not a false alarm.
- A `pull_request` run deleted from the Actions UI removes its suite, so the head would read as a measured none.
  Deleting runs is not a practice in this repo; not filed.

No BLOCKER: no measured none goes unreported, and no unmeasured input (a malformed, truncated or UNKNOWN reply)
reaches the hook or is worded as a measured absence of CI.

VERDICT: CONVERGED
