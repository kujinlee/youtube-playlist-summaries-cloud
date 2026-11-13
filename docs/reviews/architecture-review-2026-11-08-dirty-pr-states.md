Reviewed head: 3a30223f58ba7b2de372159746f4ea8dea098e2a

> **For the r3 fold of `dirty-no-ci` (PR #539, backlog #545).** This review was triggered by **THRASHING** in one
> component, `stalled-work-dirty-pr` (`own_prs`, `head_has_run`, `pr_item` and the hook tiers in
> `scripts/check-stalled-work.py`). r2's three findings were caused by r1's fold, and three of r3's four by r2's
> (`docs/dev-process.md` → *Phases*).
>
> **Verdict: REDESIGN, by removal.** Each fold added a STATE so that an unmeasured case would not be silent:
> UNKNOWN-MERGE (r1), then DIRTY-UNSEEN, MERGE-PENDING and a 300 s grace (r2). Each next round found an edge of the
> state just added: a fresh push, a grace timed from the wrong clock, a future date, a new state in the wrong tier.
> None of those states has caught a real case. The fold keeps ONE hook state, DIRTY-NO-CI, which fires only on a
> MEASURED none. Everything it cannot measure is ONE CLI line, `UNMEASURED`, which is not a stalled state, sits in
> no hook tier, and has no clock. R3-F1 is fixed. R3-F2, R3-F3 and R3-F4 are dissolved, because the code they were
> about is gone. **BLOCKERs: none.**

# Phase 6 architecture review (narrow, triggered by thrashing): the dirty-PR states

Scope: `head_has_run`, `pr_node_problem`, `own_prs`, `pr_item`, `STALLED_STATES`, `HOOK_TIERS` and `MERGE_GRACE_S` in
`scripts/check-stalled-work.py` at the reviewed head, their backlog #545 cases, and the 49 backlog #545 entries in
`scripts/mutations/check-stalled-work.json`.

Read first:
- `docs/reviews/codex/dirty-no-ci-r1-codex.md`, `docs/reviews/claude/dirty-no-ci-r1-claude.md`,
  `docs/reviews/codex/dirty-no-ci-r2-codex.md` and `docs/reviews/claude/dirty-no-ci-r3-claude.md`;
- the r1 and r2 coordinator docs under `docs/reviews/coordinator/`;
- the `dirty-no-ci` row of `docs/reviews/decision-scheme/decision-log.jsonl`;
- `docs/review-method.md` → *Can a redesign remove it?*;
- `docs/reviews/architecture-review-2026-11-08-goal-tree-sibling-cache.md` (branch `suite-cost-a`), for the shape.

No ADR covers the stalled-work report's states, so none is re-litigated. Nothing under `.claude/plans/` was read.

## 1. Thrashing or prose floor?

**Thrashing, and a redesign removes it.** Every finding carried a repro, so none is a prose floor. Each is
classified below by what it needed to reproduce, and by whether that input has been seen from real GitHub.

| Round | Finding | Needed to reproduce | Real input seen? | Kind | fix_induced |
|---|---|---|---|---|---|
| r1 | Codex X1: a commit STATUS fills the rollup, so it read as a run | A head carrying only a legacy status | Yes: the rollup is the wrong signal (PR #529's heads) | The core test was wrong | no |
| r1 | Claude C1: the DIRTY line sorted last in tier 0 and was the first the cap cut | 8 older stalled lines beside it | Plausible (the cap was set from 70 real lines) | Placement | no |
| r1 | Claude C2: `mergeable: UNKNOWN` was silent | GitHub still computing at the moment of the read | Yes, transiently (§4) | **Added a state: UNKNOWN-MERGE** | no |
| r1 | Claude C3: the remedy assumed base master | A stacked PR | Plausible | Scope of the rule | no |
| r1 | Claude C4: a future head date gave a negative age | Clock skew | No | Display | no |
| r1 | Claude C5: a missing rollup key was worded as an absence | A reply without the key | No (GraphQL returns what it is asked) | Malformed reply | no |
| r2 | Codex R2-F1: truncated suites got the no-CI diagnosis | Over 20 suites, none `pull_request` in the first 20 | **No: 0 of 187 heads at a page limit, max 4** | Incomplete reply → **added a state: DIRTY-UNSEEN** | yes (r1's suite page) |
| r2 | Codex R2-F2: UNKNOWN-MERGE fired the instant a head was pushed | A read inside GitHub's computation | Yes, transiently | Edge of r1's state → **added MERGE-PENDING and a grace** | yes (r1's UNKNOWN-MERGE) |
| r2 | Codex R2-F3: an empty `baseRefName` read as "not master" | A blank base | No | Malformed reply | yes (r1's base test) |
| r3 | Claude R3-F1: a suite node with no `workflowRun` key read as a measured none | A malformed node | No: 0 nodes without the key in 187 heads | Malformed reply | no (r1's read; r2's audit missed it) |
| r3 | Claude R3-F2: a head dated in the future got the grace for the whole skew | A committer clock ahead of GitHub | No: 0 of 187 heads dated after their first suite | Edge of r2's grace | yes |
| r3 | Claude R3-F3: the grace was measured from the push and timed from the commit | A commit pushed over 5 min after it was made | Yes: 53 of 187 heads (28%) | Edge of r2's grace | yes |
| r3 | Claude R3-F4: DIRTY-UNSEEN sat in the tier the cap cuts first | 8 older stalled lines plus a truncated page | No (the truncated page is not seen) | Edge of r2's state | yes |

**What the rows share.** From r1 on, the fold's rule was "an unmeasured case must never be silent, so give it a
line in the hook". Each line needed a STATE, and each state needed a time rule, a tier and wording. Every
fix-induced row, R2-F2, R2-F3, R3-F2, R3-F3 and R3-F4, is about one of those states or one of its parts. It
is never about DIRTY-NO-CI's own rule, which has not changed since r1's X1. The states were added for inputs that
are malformed, truncated or transient. Of those, only the transient UNKNOWN has been seen from real GitHub, and §4
shows that it never had the property the hook warns about.

**Can a redesign remove it?** Yes. If an unmeasured case is a CLI line and never a hook item, it needs no tier, no
grace, no clock and no separate wording per cause. Every fix-induced row above is then either impossible or has no
code left to be wrong in.

## 2. What the hook actually needs to tell the owner

PR #529 (2026-11-06): a master-based PR that **conflicts**, whose head has **no `pull_request` run**, and which
therefore **will get no CI** until master is merged in. It read as "waiting" for about 2 h. That is one fact. It
needs three measurements: `mergeable == CONFLICTING`, `baseRefName == master`, and a complete, well-formed suite
page for the head with no `pull_request` run.

All three are present, or the hook has nothing true to say. "GitHub has not worked out whether it conflicts" and
"we could not see whether CI ran" are not that fact. They are a statement that the measurement failed this time.
This hook is read on every prompt and re-measures every time (there is no cache), so a measurement that failed on
one prompt is taken again on the next.

## 3. The designs considered

- **A. Keep the four states and patch r3's three edges.** Floor the grace at "a future date gets none", re-anchor
  the grace on the earliest suite's `createdAt` (a new query field), and move DIRTY-UNSEEN to tier 0. That is three
  more rules on states that have caught nothing. The next round would have new targets: `createdAt` missing or
  skewed, an UNSEEN line crowding DIRTY lines out of tier 0. This keeps the requirement that thrashed. Rejected.
- **B. Make every unmeasured input CANNOT RUN.** It is loud, but one malformed PR node would blank the whole
  report, unpushed tips and review halves included. A transient UNKNOWN would do the same on a normal push, and
  that is R2-F2's noise at its worst. Rejected for UNKNOWN. For shapes the reply should never have (a missing
  `mergeable`, a blank base, a mergeable outside the enum), `pr_node_problem` already does exactly this, and that
  part is kept.
- **C. ONE hook state, DIRTY-NO-CI, on a measured none. Everything else is ONE CLI-only line.** Chosen.
  - `pr_item` returns DIRTY-NO-CI only for CONFLICTING plus `headRun is False`, as before.
  - A CONFLICTING head whose run was not seen, or an UNKNOWN head with no run seen, is `UNMEASURED`: a CLI line
    beginning `NOTE —`. It is not in `STALLED_STATES` and not in `HOOK_TIERS`. It has no grace and no clock.
  - `head_has_run` reads `False` only for a complete page in which every node is well-formed (R3-F1).
  - An UNMEASURED line never hides a stalled one. A stale or undated draft is still STALLED-DRAFT or UNKNOWN-DRAFT;
    UNMEASURED only replaces "OK".
  - Deleted: `MERGE_GRACE_S`, MERGE-PENDING, UNKNOWN-MERGE and DIRTY-UNSEEN as states, and their tier placements.

## 4. What C loses, measured

Every number below is MEASURED on 2026-11-08 unless marked otherwise.

- **Truncated or malformed suite pages (DIRTY-UNSEEN's inputs).** On 187 heads with suites, across the last 40 PRs
  (the r3 reviewer's read-only `gh api graphql`, `commits(last:10)`, `checkSuites(first:10)`, saved as
  `scratchpad/r3/heads.json`): at most 4 suites on any head (164 heads have 4, 23 have 2), **0 at the page limit**,
  and **0 nodes without a `workflowRun` key**. The live query asks for 20. DIRTY-UNSEEN has caught **0** real cases,
  and the input it exists for has not occurred.
- **`mergeable: UNKNOWN` (UNKNOWN-MERGE's input).** GitHub keeps no history of `mergeable`, so the only record is
  what past sessions printed. Over every transcript under `~/.claude/projects/<this repo>/` (`rg` for `mergeable`
  followed by a value), there are 23 UNKNOWN hits in 3 transcripts. Most are review prose. The real gh replies are:
  - 2026-10-07 18:52:24, PR #368 and PR #370 UNKNOWN with 3 and 9 checks pending. Their heads HAD runs, so they
    would be `headRun True` and never reported under any design. By 18:54:41 both read CONFLICTING. That is **at
    most 137 s** of UNKNOWN.
  - 2026-10-07 19:56 (PR #370) and 2026-10-26 20:38: UNKNOWN on a PR that had already MERGED. A closed PR is not in
    the query.

  So **0 observed UNKNOWN reads on an open PR with no run**, and the one UNKNOWN whose end is visible lasted under
  2.5 min. A live read now (6 open PRs) shows 0 UNKNOWN, 2 CONFLICTING with runs (PR #376, PR #392) and 4 MERGEABLE.
  UNKNOWN-MERGE has caught **0** real cases. Under C, a conflict GitHub was still computing appears as DIRTY-NO-CI
  on the first prompt after GitHub settles it. The only cost is that one-prompt delay. For the PR #529 incident
  (about 2 h) that delay is immaterial.
- **The grace (MERGE-PENDING).** It existed only to quiet UNKNOWN-MERGE. With UNKNOWN out of the hook, there is
  nothing for a grace to time. R3-F3's measurement (53 of 187 commits pushed over 5 min after they were made)
  shows it was timing the wrong interval for 28% of real pushes. Removing it loses nothing that was working.
- **What C does NOT lose.** DIRTY-NO-CI's rule, its first tier, its wording and its age are unchanged. The PR #529
  shape (CONFLICTING, app suites only, a complete page) is still reported, and the cases from the build and r1
  that pin it still pass.

## 5. The bound, and why it holds

**In scope:**
- A master-based PR, `mergeable` CONFLICTING, whose head's suite page is complete (`totalCount` equal to the
  nodes returned) and well-formed (every node a dict with a `workflowRun` key, null or a run with a string `event`),
  and holds no `pull_request` run. It is DIRTY-NO-CI, in the hook's first tier, on every prompt it stays so.
- Everything else is a CLI line or nothing. No unmeasured input reaches the hook, so none can be cut for, or crowd
  out, a measured line, and none has a clock that can run fast or slow.

**Out of scope (stated, not defended):**
- A CONFLICTING PR whose head has more than 20 suites and none `pull_request` in the first 20, or whose page is
  malformed. It is UNMEASURED: in the CLI, never in the hook. Measured frequency: 0 in 187 heads.
- A PR GitHub has not finished computing. It is UNMEASURED until a prompt reads it settled. Measured: the one
  observed case settled within 137 s.
- A STALE draft that is also UNMEASURED shows only STALLED-DRAFT. The draft line is a hook item, and the CLI drops
  the UNMEASURED reason for it.
- Anything outside the PR path (unpushed tips, review halves, MERGED) is untouched by this fold.

## 6. Stop condition

From r4, findings are FILED unless BLOCKING (`review-method.md` §0 Q4c). In this component:
- A finding that needs a truncated, malformed or UNKNOWN reply to reach the HOOK is admissible and is a defect in
  this fold. Under §5 that cannot happen.
- A finding that the CLI's UNMEASURED line is worded or placed suboptimally is filed, not folded.
- A finding that proposes a NEW PR state for an unmeasured input is out of scope by this review. It needs a
  measured real case (a reply from real GitHub) before it is built.
- A BLOCKER is a measured none (complete, well-formed, CONFLICTING, master, no `pull_request` run) that is not
  reported as DIRTY-NO-CI, or any unmeasured input reported as a measured absence of CI.

## 7. Not written down until now

The hook had no stated rule for what an unmeasured PR is OWED. r1 answered "never silence", which is right for a
measurement the hook claims to have made and wrong for one it could not make. Each fold then built a state to make
an unmeasured input loud, and each state became the next round's target. The missing sentence is: **the hook
reports what it measured, and a measurement that failed is re-taken on the next prompt, not announced.** It is now
stated in the module docstring, beside `pr_item`'s UNMEASURED branch, and in `HOOK_TIERS`' comment.

## 8. The fold, in numbers

- **Cases: 225 → 225.** Six retired with the code they pinned: DIRTY-UNSEEN's tier, the grace's constant, its window
  and its last second, and two `collect` cases (UNKNOWN-MERGE in the hook, MERGE-PENDING in the CLI). Six added:
  R3-F1 directly and through `own_prs`; an UNKNOWN head is UNMEASURED at every age (now, 60 s, 1 day in the future,
  20 min, 1 day, undated; R3-F2's and R3-F3's inputs among them); UNMEASURED never hides a stale or undated draft; an
  undated non-draft UNKNOWN head is UNMEASURED; and one `collect` case where UNKNOWN and truncated PRs beside a
  DIRTY-NO-CI and a CLEAN one give two UNMEASURED CLI lines and a hook block carrying only the DIRTY line, and alone
  give rc 0 and no block. The UNKNOWN-MERGE stalled-state case became "UNMEASURED is in no stalled state and no
  tier, and DIRTY-NO-CI is the only PR state in either". Three more cases were renamed from the old states to
  UNMEASURED.
- **Mutations: 133 → 133.** Ten retired with deleted code: DIRTY-UNSEEN's branch, stalled state and tier (3);
  UNKNOWN-MERGE's branch, head-run test and stalled state (3); the grace (4). Ten new: UNMEASURED at both OK
  points, the UNKNOWN arm, never hiding a stale or an undated draft, never a stalled state, never a hook tier (7),
  and R3-F1's well-formed node (3). Five anchors were re-bound to the reshaped lines. Three expects were renamed
  with their cases. One of those, `545 r1: a missing checkSuites key reads as a measured absence`, had been STALE
  since r2's fold: r2 renamed its case and not its expect, and the r3 review's hand-check of r2's 23 entries did not
  include it.
