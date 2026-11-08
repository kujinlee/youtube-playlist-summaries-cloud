# Round 2 — `dirty-no-ci` (PR #539, backlog #545) — coordinator — Codex NOT CONVERGED; all three folded

```yaml
round: 2
fixes_nontrivial: true
subject: dirty-no-ci
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: true, component: stalled-work-dirty-pr, disposition: fixed}
  - {id: X2, severity: Low, aim: deliverable, fix_induced: true, component: stalled-work-dirty-pr, disposition: fixed}
  - {id: X3, severity: Low, aim: deliverable, fix_induced: true, component: stalled-work-dirty-pr, disposition: fixed}
```

REVIEW GAP: claude — alternation (rounds 2+ run ONE half; round 2 is Codex's, round 3 is Claude's).

Codex (`docs/reviews/codex/dirty-no-ci-r2-codex.md`, its R2-F1 to R2-F3 = X1 to X3 here). All three were caused by
round 1's fold, which added the suite page, the UNKNOWN-MERGE state and the base test. **This is the first round with
fix-induced findings in this component; another one at r3 is THRASHING and fires an architecture review.** So each
fix is aimed at the CLASS the three share, "an incomplete or malformed measurement must never become a confident
diagnosis or silence", and every field the parser reads was audited for it (below).

- X1 (Medium): suites truncated at 20 with no `pull_request` suite among them made `head_has_run` return `None`, and
  `pr_item` still printed DIRTY-NO-CI with its mandatory remedy, "CI will not run until master is merged in". Pagination
  was considered and rejected. The GraphQL `checkSuites` connection takes only `first/last/after/before` and
  `filterBy: {appId, checkName}` (introspected 2026-11-08, read-only), so no page can be ordered to put `pull_request`
  suites first. Paging would mean a second query per truncated head inside the hook's 15 s deadline, and filtering by
  app id would hardcode an id whose being wrong reads as "no run". MEASURED 2026-11-08, read-only `gh api graphql`
  over the last 40 PRs: at most 4 suites on any of 132 heads with PR CI, so truncation is a bound, not the common path.
  **Fix: the no-CI diagnosis is given only for a MEASURED none (`False`).** A conflict whose run was not seen
  (`None`: truncated, a missing key, gh's last commit not the head) is a new stalled state, `DIRTY-UNSEEN`, in the
  hook's second tier. Its line reads "DIRTY, whether PR CI ran on its head was NOT MEASURED" and its action is
  conditional: "open the PR's checks: if no pull_request run is there, merge origin/master in". Case: Codex's
  repro (21 suites, 20 returned, none `pull_request`) through `own_prs` is DIRTY-UNSEEN, with neither the no-CI
  text nor "CI will not run". Mutations: the unseen run given the diagnosis again; DIRTY-UNSEEN out of the stalled
  states; out of the hook tiers. Two r1 cases that asserted the old wording for `None` ("no CI run seen") now
  assert DIRTY-UNSEEN / "NOT MEASURED". That is the claim this finding reverses; neither case was deleted.
- X2 (Low): UNKNOWN-MERGE fired the instant a head was pushed. MEASURED 2026-11-08 on the same 132 heads: the first
  `pull_request` workflow run was created 2 s to 111 s (median 4 s) after the head's first check suite. GitHub
  computes mergeability before it starts that run. **Fix: `MERGE_GRACE_S` = 5 min**, that maximum with room. Inside
  it an UNKNOWN head with no run is `MERGE-PENDING`, a CLI line that is neither a stalled state nor in a hook tier, so
  the check exits 0 and the hook prints nothing. The grace counts from the COMMITTED date, which is never after the
  push, so it can only end early, never late. A head with NO date gets no grace: an unmeasured age is never read as
  young. Cases: 60 s old is MERGE-PENDING (not stalled, no tier); grace + 1 s and an undated head are UNKNOWN-MERGE;
  the last second is inside; the constant is pinned; through `collect`, a 2-minute-old UNKNOWN head gives rc 0, its
  CLI line, and no hook block. Mutations: the grace removed, the grace given to an undated head, the last second
  dropped, the grace widened to 30 min. The r1 `collect` case's UNKNOWN head is 10 min old, so it still reaches the hook.
- X3 (Low): an empty `baseRefName` passed the string check, read as "not master", and suppressed the PR. **Fix:**
  `pr_node_problem` refuses a base that is empty or malformed, meaning not 1-255 characters free of whitespace,
  control characters and `git check-ref-format`'s metacharacters (`BASE_REF_RE`). That is CANNOT RUN. Case: `""`
  and `"a b"` refused, `"stack/base"` accepted. Mutations: the check removed; the pattern accepting the empty string.

**Class audit: every field `own_prs` / `head_has_run` / `head_commit_ts` reads, checked for a missing, truncated,
malformed or not-yet-computed value becoming a confident diagnosis or silence.**

| Field | Before this fold | Now |
|---|---|---|
| `number`, `isDraft`, `isCrossRepository`, `headRefName` | type-checked, CANNOT RUN | unchanged. `headRefName` is display-only and shaped |
| `mergeable` | enum-checked, CANNOT RUN; UNKNOWN reported | UNKNOWN inside the grace is a CLI line (X2) |
| `baseRefName` | string-checked only, so `""` meant silence | non-empty well-formed ref, or CANNOT RUN (X3) |
| `headRefOid` | non-hex emptied, run `None`, which still gave DIRTY-NO-CI | `None` is DIRTY-UNSEEN (X1) |
| `commits.nodes[-1].oid` not the head | run `None`, which gave DIRTY-NO-CI | DIRTY-UNSEEN (X1) |
| `committedDate` missing or unparsable | date `None`: UNKNOWN-DRAFT, "date unknown" | unchanged; an undated UNKNOWN head gets no grace (X2) |
| `checkSuites` missing | `None`, which gave DIRTY-NO-CI | DIRTY-UNSEEN (X1) |
| `checkSuites.totalCount > len(nodes)` | `None`, which gave DIRTY-NO-CI | DIRTY-UNSEEN (X1) |
| `checkSuites.nodes` not a list | **`""` with total 0 read as a measured none** | `None` (NEW, found by this audit) |
| `checkSuites.totalCount` boolean | **`True` with one node read as a complete page** | `None` (NEW, found by this audit) |
| `pullRequests.totalCount` vs nodes | CANNOT RUN when they differ | unchanged |

The audit found two instances beyond the three named, both in `head_has_run` and both fixed: nodes that are not a
list, and a boolean `totalCount`. They have one case and two mutations.

Self-test 217 -> 225 cases. Mutations 122 -> 133: 11 new, 12 existing anchors re-bound to the same edit on the reshaped
lines, none retired. Every one of the 133 binds by the harness's own rule. The 23 new or re-bound entries were each run
in a staged copy and give rc 1, with every `expect` named exactly once by `parse_fail_names`. The fold adds two
reported states and changes what the no-CI diagnosis requires, so `fixes_nontrivial: true` and round 3 (Claude) runs
on the fold.
