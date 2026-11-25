# Round 2 — `dashboard-retire-plan` — coordinator — ⟳ NOT CONVERGED (Codex); 4 fixed, 0 rejected

REVIEW GAP: claude — alternation (rounds 2+ run one half; the Claude half ran round 1 and runs round 3).

```yaml
round: 2
fixes_nontrivial: true
subject: dashboard-retire-plan
halves:
  codex: ran
  claude: gap
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: true, component: rename, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: true, component: cutover, disposition: fixed}
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: true, component: cutover, disposition: fixed}
  - {id: Xm4, severity: Low, aim: deliverable, fix_induced: true, component: store-gate, disposition: fixed}
```

Subject: `docs/superpowers/plans/2026-11-24-dashboard-retire.md` at `b3cc3c5b` (reviewed), with `origin/master`
(`82a85bb4`, the spec's PR #633) merged in first; fold at the commit after it. The approved spec's decisions
are not reopened.

- Codex half: `docs/reviews/codex/dashboard-retire-plan-r2-codex.md` — 3 MAJOR, 1 MINOR (here XM1–XM3, Xm4).
  NOT CONVERGED.
- Claude half: not run (alternation).

All four were caused by round 1's fold (r1 XM3's same-class fix, r1 XM2, r1 XM1, r1 CM1 respectively).
Round 1 carried no fix-induced finding, so this is one fix-induced round, not two: the THRASHING condition
(two consecutive rounds, one component) is not met. `cutover` holds two of the four.

| Id | Finding | Verified against | Disposition — where fixed |
|---|---|---|---|
| XM1 | Task 9's falsifier `grep -n -- '--pr-body-file' ci.yml` must print nothing, but the review-recorded step keeps the flag | `ci.yml:1138` (`check-review-recorded.py … --pr-body-file /tmp/review-pr-body.md`), a step Task 9 leaves untouched — the grep could never pass | **Fixed.** 9.8 is now the code half only (argparse exit 2), written in Step 1 and expected red in Step 2. New Step 6b reads the gate's step alone (awk to the next `- name:`, comment lines dropped — the comment block between the steps names `BODY`) and asserts the remaining count is exactly 1. Run on copies of today's `ci.yml`: renamed-only → rc 1; Task 9's edit → rc 0; review-recorded flag also removed → rc 1 |
| XM2 | Task 13 finds the squash by `git log --grep='^Ask store S2'`, a title the plan never sets | the plan: the only `Ask store S2` text is Task 8's commit subject, which a squash replaces with the PR title | **Fixed, simpler:** find the squash by the PR that made it — `gh pr view "$PR" --json state,mergeCommit` — then check identity before reading its parent: merged, ancestor of `origin/master`, one parent, `scripts/check-ask-store.py` in its tree; every link `&&`. Controls: the `-q` filter prints nothing for an OPEN PR (jq run on both shapes); the parent count refuses this branch's merge commit and accepts squash `7a6ffa00` |
| XM3 | 12.11 is expected red in Step 3 and green in Step 6 but Step 1 never writes it | Task 12 Step 1: "12.1–12.10 and 12.12–12.16" | **Fixed.** Step 1 writes 12.1–12.16 (12.11 live, patching nothing); Step 2's red includes it; Step 3's expected line names 12.12–12.16 PASS as well |
| Xm4 | Step 5b pipes the self-test into `tail` without `pipefail` | the block: `(cd "$S" && python3 … --self-test \| tail -1)` | **Fixed.** `set -o pipefail` inside the subshell. Measured: a child printing then exiting 1, piped to `tail -1` — rc 0 plain, rc 1 under `pipefail` |

**Mutation arithmetic:** unchanged — no fix adds or removes a mutation, case count aside (9.8 was already in
the table). Pins as round 1 left them.

`fixes_nontrivial: true` — XM2 replaces the coordinator's squash-finding procedure with a new five-link chain,
and XM1 adds a verification step with its own shell; both are new text a reviewer has not read.

Next: round 3, ONE half by alternation (Claude), against this fold.
