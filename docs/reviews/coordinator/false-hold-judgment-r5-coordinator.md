# Round 5 — `false-hold-judgment` (backlog #508) — coordinator — CONVERGED (Claude), capped confirmation

```yaml
round: 5
fixes_nontrivial: false
subject: false-hold-judgment
halves:
  codex: gap
  claude: ran
findings:
  - {id: F1, severity: Low, aim: deliverable, fix_induced: false, component: scripts/check-merge-ready.py, disposition: filed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: false, component: scripts/check-merge-ready.py, disposition: filed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: false, component: scripts/codex-review.py, disposition: filed}
```

REVIEW GAP: codex — alternation, per `review-method.md` -> Round topology: round 4 was Codex's, so round 5 is Claude's.
Not a failure to run. This round exists because `check-review-decision.py` said ROUND_OWED after round 4: round 3's
fold was non-trivial and the rule wants a second clean round after it. It is capped (§0 Q4c): only a BLOCKER folds.

Claude reviewed `16b401a4` (the merging tree) and returned CONVERGED: no BLOCKER. `check-merge-ready.py --self-test`
328/328, `codex-review.py --self-test` 232/232, plus a 20,000-diff random comparison of master, r2 and HEAD: on no
input does HEAD let through a line master flagged, except via the intended rising-count exemption or the
identical-text pairing already filed as backlog #527.

## The findings — all MINOR, all filed, none caused by round 3's fold

- **F1 — added to backlog #527.** A raised `--self-test # N cases` line excuses whichever removed count line comes first,
  not preferring one far from a failure word (came in at round 2). #527's identical-text fix would not cover it, so the
  row now names it.
- **F2 — backlog #532.** The rising-count matching takes the first fit, so it can over-flag (6, 8 removed; 9, 7 added →
  `# 8` still flagged). Fails closed: a false HOLD.
- **F3 — backlog #532.** Any 12-hex token after the `VERDICT:` line voids the whole answers section (a short SHA in the
  verdict line does it). Fails closed: a false HOLD. Round 3's fold report named this risk.

**Its loosening answers are the point of this PR.** Four `finding:` answers each name an intended #508 relaxation; two
are `not a loosening`. They keep the PR on HOLD, which is correct: it is the owner-chosen card-A loosening
(2026-11-05 08:14) and goes to the owner.

**A coordinator slip, recorded:** this round's brief first went out with a literal `FLAGBLOCK` placeholder in place of
the gate's flagged-lines block, corrected by message before the review was written. Nothing checks that a Claude half's
brief carries the block; it fails closed (no answers → HOLD). Noted in #532.

**The loop stops here, under the cap.** `check-review-decision.py` reads `ROUND_OWED — r5 left a defect open in the
deliverable (disposition 'filed')`: by design it counts `filed` as open. Past the round cap (§0 Q4c) findings below
Blocking are FILED, not fixed. That is the same disposition `agenda-499` r4, `agenda-goal-509` r4 and `diff-coverage`
r4 recorded before they merged. No sixth round is run.
