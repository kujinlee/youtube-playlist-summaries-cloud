# Round 4 — `guards-cannot-run` (PR #440, backlog #357, backlog #331) — coordinator — DEFER, terminal: findings FILED

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 4
fixes_nontrivial: false
subject: guards-cannot-run
halves:
  codex: ran
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - id: R4-1
    severity: High
    aim: deliverable
    disposition: filed
    filed_as: "backlog #414"
    fix_induced: false
  - id: R4-2
    severity: Medium
    aim: deliverable
    disposition: filed
    filed_as: "backlog #414"
    fix_induced: false
  - id: R4-3
    severity: Medium
    aim: deliverable
    disposition: filed
    filed_as: "backlog #414"
    fix_induced: false
```

Codex reviewed `b32a3b28`, the SPLIT fold first. **The SPLIT fold held:**
- C3: the stdin bound is pinned at exactly 1 MiB, with one byte over refused and a 0.5 s late payload accepted;
- C4: FIFO, `/dev/zero`, a directory and symlinks to each are all refused, naming `NOT_REGULAR`;
- C5: the Stop hook reads through `bounded_read`;
- 56/56 and 247/247 cases; 29/29 mutations killed and attributed.

The three findings sit at the unit's edge, and none is fix-induced:
- R4-1: two hook wrappers, plus the selection-card guard, still read stdin with `cat` or directly;
- R4-2: the Stop hook's command substitution deletes a NUL, so a corrupt payload passes;
- R4-3: `check-ci-watched` discards the reader's refusal.

Each path exists unchanged on master, so shipping this PR makes nothing worse, and it bounds the five guards it set out to bound. **Thrashing or prose floor:** neither. No finding in rounds 3 or 4 came from the previous round's fix in the same component. The rounds found successive paths around the reader, which is scope, and DEFER is the rung for it. All three are FILED as **backlog #414**, with the reviewer's inputs and a FAILS IF. The reviewer also qualified C5's "every guard, exit 1" claim, since a blocking-check failure takes precedence with rc 2; that qualification is recorded in #414 and the PR body. The unit closes here.
