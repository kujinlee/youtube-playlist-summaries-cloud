# Round 5 — `plan-586-redesign` — coordinator — Claude NOT CONVERGED: one BLOCKER in `settled`; the omission predicate is removed, not patched

REVIEW GAP: codex — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

Subject: the round-4 fold, `git diff 5ecf2954 442fcc1b`, reviewed by Claude at
`docs/reviews/claude/plan-586-redesign-r5-claude.md` (1 BLOCKER, 1 MAJOR, 3 MINOR). Every BLOCKER claim was run on
the plan's extracted Task 7.2/7.3 code.

```yaml
round: 5
fixes_nontrivial: true
subject: plan-586-redesign
halves:
  claude: ran
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: F1, severity: High, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: F2, severity: Medium, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: filed}
  - {id: F4, severity: Low, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: F5, severity: Low, aim: deliverable, fix_induced: true, component: plan-text, disposition: filed}
```

## What held

B1's fix held: the exact-identity `held_by_archive`. The reviewer ran Codex's reproduction, the same PR at another
push, another mutant or seed, empty evidence, and the conflation and canonicalisation attacks, and all of them latch.

## F1 is the fourth fold-caused round in `ledger-trust`, and this time the answer is to REMOVE, not patch

r2 C1, r3 F1, r4 B1, r5 F1. Every one of them was a predicate that decides **not to look**: a status filter, a subset
absorb, an archive hold by PR number, and now `settled`, which freezes a run by its age (older than 30 days, GitHub's
re-run limit) without ever having observed its final attempt count. *Can a redesign remove it?* **Yes, for this
one.** `settled` exists only to save API calls. Removing it costs calls, not correctness: the report re-decides every
PR in its scan window on every run. That is the r4 coordinator's pre-committed retreat applied to the mechanism that
failed. `held_by_archive` keeps its place, because it held.

Decision-log row: route `redesign` (the plan-586-redesign accrete bet scored `continued`).

## The fold (round cap: only the BLOCKER, plus what its removal makes moot)

- **F1:** delete `settled` and every call site and prose reference. `report()` re-decides every PR the scan window
  lists, every run. State the call bound **from the code** (runs listed × attempts in the window), and keep the
  120-day window bound. Cases: the reviewer's run-55 re-run at day 30, and an attempt still running at the last
  report before day 31. Both must now be compared. Adjacent pass: an unchanged PR is re-decided to the same result
  and absorbs to an identical row (no churn in the committed ledger).
- **F2, F4:** moot once `settled` is gone. The fold confirms no other `all(...)` over a possibly-empty push list
  decides an omission.
- **F3 (filed):** `miss_evidence` counts a `differing` item that did not replay as a miss, so a later stable miss on
  it is held. A per-item replay record is a schema change past the cap. The reviewer rates it MINOR: the item was in
  a miss row the owner reset. File as a backlog row.
- **F5 (filed):** the prose "a pre-epoch PR can only latch" overlooks `q1_probe_delta`. File, together with the
  question of whether that delta is per-epoch evidence at all.

Round 6 is Codex, scoped to this fold only, BLOCKER-only.
