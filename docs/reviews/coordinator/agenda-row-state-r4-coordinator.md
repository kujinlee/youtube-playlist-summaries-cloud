# Round 4 — `agenda-row-state` — coordinator — NOT CONVERGED (Codex, 1 BLOCKER), folded

Round 4 ran ONE half by alternation: Codex (`docs/reviews/codex/agenda-row-state-r4-codex.md`), reviewing `938a908c`
(the r3 fold `80d60a88` plus the REVIEW GAP line fix). The Claude half is a gap by alternation.

REVIEW GAP: claude — alternation.

Round 4 is the round cap (`docs/review-method.md` §0 Q4c): only a BLOCKER is folded here; anything less is filed.

## Finding

| # | Severity | Caused by the r3 fold? | Disposition |
|---|---|---|---|
| B1 | BLOCKER | **no**: the r2 fold (`b1e98095`) added `and not cells_held` to two conditions in `goal-tree.py` and left three anchors unbound | **FIXED** |

**B1.** Three edits in `scripts/mutations/goal-tree.json` matched `scripts/goal-tree.py` zero times, so the CI sweep
would refuse the manifest:

- entry 139, *review r1 X2: a backlog-only thread's merge time ignores GitHub's mergedAt*;
- entry 472, *backlog #515: a merged PR naming a still-open row ticks the step*;
- entry 490, *r1 C7: a failed git/gh read makes an all-✅ step CANNOT RUN*.

Each is rebound to the current condition and still deletes the clause its case names: 472 drops `not row_open`, and
490 drops `not by_cells`, each keeping `not cells_held`. The manifest count is unchanged at 502.

## Evidence

- Diagnostic slice of the three, on a scratch copy: `OK — delivered scripts mutated: 1 file(s), 3 mutation(s), 3 killed,
  3 attributed to the case each names, 0 survivor(s) — measured over ONLY scripts/goal-tree.py — a DIAGNOSTIC slice, not the gate`.
- Class search, an all-manifest anchor resolve: every edit in `scripts/mutations/*.json` checked against its file on all
  three open branches. agenda-row-state had 6162 edits with 0 unbound, usage-hook-master 6146 with 0, and rm-backup 6221 with 0.

## Thrashing

The r4 finding was not caused by the r3 fold, so the Phase 6 redesign holds. It was caused by the r2 fold, in
`mutation-manifest`, which no earlier round flagged.
