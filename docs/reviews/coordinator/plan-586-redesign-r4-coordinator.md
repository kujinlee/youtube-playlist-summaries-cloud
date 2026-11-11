# Round 4 — `plan-586-redesign` — coordinator — Codex NOT CONVERGED: one BLOCKER; past the cap, so only it is folded

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

Subject: the round-3 fold, `git diff c5799f17 51bca9e4`, reviewed by Codex at
`docs/reviews/codex/plan-586-redesign-r4-codex.md` (1 BLOCKER, 1 MINOR).

```yaml
round: 4
fixes_nontrivial: true
subject: plan-586-redesign
halves:
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
  codex: ran
findings:
  - {id: B1, severity: High, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: M1, severity: Low, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
```

## The round cap (`docs/review-method.md` §0 Q4c)

Round 4 is past the cap, so only a BLOCKER changes the plan. **B1 is one** by the §8 definition: Codex ran the
plan's extracted `held_by_archive`/`absorb_epoch`/`absorb_errors` and a committed absorb drops a trusted report's
NEW miss (PR #600 on `scripts/y.py`, after #600's miss on `scripts/x.py` was archived), and the guard accepts it.
**M1 is folded, not filed,** because it is the `report()` contract the B1 fix rewrites: filing it would leave the
contract the fold just wrote self-contradictory.

## Thrashing: the third consecutive fold-caused round in `ledger-trust`

r2 C1, r3 F1, r4 B1. *Can a redesign remove it?* The r3 problem was real (a reset must clear the latch it was
granted for), and the r3 fold answered it with a SUPPRESSION predicate, which is the one shape that can loosen.
B1 is that predicate matching too coarsely. **The fix keeps the shape and narrows the match to exact evidence**:
suppress only an item the archive holds byte-for-byte as the same evidence (PR, push HEAD and BASE, target, mutant
or event identity). Anything else latches. That is a one-predicate change, and its failure direction is now
"latch too much" (liveness), never "latch too little". If round 5 finds the suppression loosening again, the
suppression goes, and a reset instead requires every listed report to be absorbed into the old epoch first,
accepting its race as a stated liveness cost.

## The fold

- **B1:** `held_by_archive` matches the EXACT evidence identity, never the PR alone. Cases: Codex's reproduction
  (a different target for an archived PR → latches), the same PR at a different push → latches, and the adjacent
  pass (the identical archived miss repeated by a daily report → held).
- **M1:** Task 7.2's `--report` input description permits the archive read that `report()` needs.

Round 5 is scoped to this fold only and FILES anything that is not a BLOCKER.

## Fold

- **B1** — fixed in plan Task 7.3 (`miss_evidence`, `event_evidence`, `held_by_archive`, and the `absorb_epoch`
  call site now passing the row), prose "What a reset clears", Task 8.2's wording, spec §2 *The ledger* and §8.6.
  Pinned by Task 7.3's **(r4 B1)** cases: Codex's reproduction (#600 archived on `scripts/x.py`, report 11.2's #600
  miss on `scripts/y.py` → latches; a HEAD equal to the r3 absorb → `rows differs from the rebuilt absorb`), the
  same PR at h2/b2 → latches, and the adjacent pass (the identical archived row repeated → held).
- **M1** — fixed in plan Task 7.2 step (1): `--report` reads archived epochs only to OMIT what they hold exactly,
  never an earlier report or artifact ledger. Pinned by Task 7.2's **(r4 M1)** case (`report()` omits the held
  event `{#600, [scripts/x.py]}` and reports `[x.py, y.py]` whole).
- **Class search** (matching coarser than full identity when deciding NOT to latch) — three more, fixed: an empty
  evidence set was vacuously held (Task 7.3, cases: empty `differing` / empty `targets` → latch); `report()`
  omitted any PR the active epoch decided by PR number alone, so a later re-run attempt was never compared (Task
  7.2 `settled`, five #620/run 55 cases); the PR scan used the active `epoch.start` as a time window, so a PR
  pending at a reset was never compared (Task 7.2 step (2) genesis scan + Task 8.1 clause 5 counting only rows
  merged at or after `epoch.start`; cases #630 and `19 of 20`). Spec §2 comparator and §8.6 updated. None
  loosens: each change latches or refuses more. The YAML dispositions are unchanged (both correct).
