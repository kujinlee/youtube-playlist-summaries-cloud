# Round 4 — `hse-slice-e` — coordinator — CONVERGED (Codex half)

Codex (`docs/reviews/codex/hse-slice-e-r4-codex.md`) reviewed `b163c95e`, the round 3 fold (`7641849e`) plus the merge of
`origin/master` (slice D, #600): no BLOCKER, 1 MINOR. It confirmed each round 3 fold on its own probes (extra- and
missing-token sources, a new wrongly sourced typed fact, a tracked "absent" ratchet each turn the intended case red; the
condition 4 regrades agree with the cited driver outcomes) and the merge's edge recount (347 → 350, no lost edge, exactly
the three stated gains). Self-tests: `mkt_seed_repo.py` 14/14, `check-shipping-sets.py` 140/140.

Under the round cap (review-method §0 Q4c) every non-BLOCKER from round 4 is FILED, not folded: Xm1 is backlog #676.

**Thrashing or prose floor?** THRASHING. Xm1 is fix-induced (round 3's absent-ratchet case, Cm3), in `mkt-seed-repo`;
round 3's Cm1/Cm2 were caused by the round 2 fold, whose own finding (r2 Xm1) came from the round 1 fold. Three
consecutive rounds carry a fix-induced finding in one component, so the arming condition holds
(`docs/dev-process.md` → *The arming condition*). Phase 6 is convened on `mkt-seed-repo` before the merge:
`docs/reviews/architecture-review-2026-11-20-mkt-seed-repo.md`.

REVIEW GAP: claude — alternation (round 4 is the Codex half's).

```yaml
round: 4
fixes_nontrivial: false
subject: hse-slice-e
verdict: CONVERGED
blockers: 0
filed: [676]
halves:
  codex: ran
  claude: gap
findings:
  - {id: Xm1, severity: Medium, aim: instrument, fix_induced: true, component: mkt-seed-repo, disposition: filed}
```

| Id | Finding | Fold |
|---|---|---|
| Xm1 | the absent-ratchet case counts `ABSENT_RATCHETS` names without requiring them distinct: three copies of `check-roadmap-consistency` pass 14/14 while the other two ratchets drop out of the fact | filed, backlog #676 (round cap) |

## Phase 6 outcome (2026-11-20)

`docs/reviews/architecture-review-2026-11-20-mkt-seed-repo.md`: **file it, no redesign in this PR.** The self-test
re-derives each fact's pairing by hand, so 13 of 20 one-sided edits of the seed pass 14/14; a redesign (each fact
declared once as a command, every answer read by running it, compared whole to one independent literal) turns all 20
red. It is filed, not done here, because no finding says a shipped fact is wrong (the scored `known-facts.json` is
unchanged), the redesign changes that file and owes its own round 1, and no later plan task edits the seed. Backlog
#678 carries it and supersedes #676.
