# Round 2 — `goal-tree-log` (PR #433, backlog #363) — coordinator — NOT CONVERGED (Codex); REDESIGN to structure

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 2
fixes_nontrivial: true
subject: goal-tree-log
halves:
  codex: ran
  claude: gap
findings:
  - {id: Y1, severity: Medium, aim: deliverable, fix_induced: true, component: needs-you, disposition: fixed}
  - {id: Y2, severity: Low, aim: deliverable, fix_induced: true, component: needs-you, disposition: fixed}
  - {id: Y3, severity: Low, aim: deliverable, fix_induced: true, component: needs-you, disposition: fixed}
  - {id: Y4, severity: Low, aim: deliverable, fix_induced: true, component: needs-you, disposition: fixed}
  - {id: Y5, severity: Medium, aim: deliverable, fix_induced: true, component: regen-hook, disposition: fixed}
  - {id: Y6, severity: Medium, aim: deliverable, fix_induced: false, component: backlog-data, disposition: fixed}
  - {id: Y7, severity: Low, aim: deliverable, fix_induced: false, component: needs-you, disposition: fixed}
  - {id: Y8, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
```

Codex on `e28197fb`. Every round-1 reproduction now fails; NOT READ propagates from every source; 63/63 mutations.
**Y1** consolidation merges a different question, or an ACTION into a decision, because both name `backlog #5`;
**Y2** it drops the ledger's count; **Y3** `multiplicity()` reads "backlog #14 answers open" as 14; **Y4** the answered
flag takes `pr #11`, `issue #11`, `color #11` for backlog rows; **Y5** the merge trigger fires on `false && gh pr merge`,
`echo ";" gh pr merge` and a heredoc, and misses `if true; then gh pr merge; fi`; **Y6** #114, #117, #211, #306 and #318
were left as the owner's; **Y7** `--page` replays a stored snapshot; **Y8** the PR's evidence describes the pre-fold code.

⟳ **A correction to my own round-2 prompt:** the "known defect" I handed Codex (the #384 duplicate, 11 not 10) was MY
misread — I rendered `--page`, which replays the logged snapshot, after rewording the ledger; a fresh snapshot gives 10
decisions + 1 action. Codex reproduced exactly that (Y7). The real defect is that the page does not make its replay
obvious.

**Route: REDESIGN to STRUCTURE**, at round 2 rather than round 4, because Y1–Y5 are the wall this session has already
met four times — reading identity, counts and execution out of free text. Merge on an explicit decision identity (row
AND kind), a count only from an explicit annotation, the answered flag only from an explicit `backlog #N`, and the
merge trigger renamed to what a static match is: *a command that may merge*, with its misses stated. **Y6** is my own
error, corrected: the standing rule is "the coordinator decides unless CRITICAL"; a row that names no recommendation
means the coordinator forms one, not that the decision is the owner's. #306 alone stays the owner's (its only
uncautioned option loosens the decision procedure's input contract).
