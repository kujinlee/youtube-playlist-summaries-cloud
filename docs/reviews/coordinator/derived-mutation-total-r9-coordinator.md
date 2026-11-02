# Round 9 — `derived-mutation-total` (PR #455, backlog #359) — coordinator — CONVERGED (Claude); two FILE findings filed as backlog #432 and #433, not folded

REVIEW GAP: codex — alternation. Round 9 alternates to the Claude half alone (rounds 2+ alternate, `review-method.md` → *Round topology*; backlog #339).

Claude half: `docs/reviews/claude/derived-mutation-total-r9-claude.md`, which reviewed `3bdff458`.

```yaml
round: 9
fixes_nontrivial: false
subject: derived-mutation-total
halves:
  codex: gap
  claude: ran
findings:
  - {id: C1, severity: Medium, aim: goal, fix_induced: false, component: pin-layout, disposition: filed}
  - {id: C2, severity: Low, aim: doc, fix_induced: false, component: sibling-import, disposition: filed}
verdict: CONVERGED
route: DEFER
```

**Verdict: CONVERGED, no BLOCKER.** No ordinary edit gives READY on a coverage fall that CI also misses.

**The DEFER route was honoured.** The decision log's pre-committed bet was that any further finding in r9 is filed as a
backlog row, not folded, and the PR ships. Both findings are FILE and neither changed a file under `scripts/`:

| Finding | Severity | Filed as | What it is |
|---|---|---|---|
| C1 | Medium | backlog #432 | PRs bumping ADJACENT `EXPECTED_MUTATIONS` pins still conflict (14 of 81 pairs share no unchanged line); the cascade is narrowed, not ended. The dashboard entry is corrected in this PR to say so. |
| C2 | Low | backlog #433 | `check-merge-ready` judges a PR's pins with that PR's own `pin_display`, so "as master trusts it" overstates; CI catches the measured input (the merge-ready self-test goes red). |

**Docs-only after r9.** This commit adds the review documents, the two backlog rows, the #359 row's shipped status and
the dashboard sentence. Nothing under `scripts/` changed after `3bdff458`, so no further review round is owed.

**Merge-time HOLD.** Claude r9 re-confirmed the same 6 `loosens a gate` lines on `scripts/check-merge-ready.py` and
`scripts/check-plan-code.py` that r5 (Claude), r6 (Codex), r8 (Codex) triaged FALSE.

## Ladder (decision log)

- The DEFER row is scored `converged`, observed = r9 produced no BLOCKER and two FILE findings, both filed.
