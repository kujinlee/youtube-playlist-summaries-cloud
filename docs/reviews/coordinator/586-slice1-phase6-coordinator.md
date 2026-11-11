# Phase 6 — `586-slice1` — coordinator — R1 ADOPTED; backlog #601 built on PR #557

Subject: PR #557 (DRAFT), branch `586-slice-1-strace`. Review:
`docs/reviews/architecture-review-2026-11-11-586-slice1-removal.md`. Thrashing in `removal-detection` armed it:
rounds 2 and 3 both carried findings caused by the previous round's fix.

## Decision: R1 is adopted

- **R1.1 (backlog #601), built in this PR.** `scripts/strace-measure.py` no longer classifies removals. Deleted:
  the `created_in_log` annotation, the creation evidence (`removed_and_created`'s creation half, `created`,
  `kind_of`, `forget`), `KEEP_REMOVALS`, `CREATORS`, the return-value read, the `copies` roots,
  `external_removals`, and the merge's `external_removal_*` tables. Kept: raw remover call counts (each record's
  `syscalls`, merged per target as `removal_calls`), the `unresolved` list, and the raw-line samples. The plan's
  Slice 1 *Decides* and Task 1.1 Step 1, the measurement doc and the driver docstring no longer claim the model.
- **R1.2 (backlog #602) and backlog #600 are not built here.** They belong to slice 2 and slice 4.

## Why the owner is not needed

R1 changes the mechanism, not the spec's goal. Slice 1 still measures whether strace is usable and still supplies
the constants the later slices pin. What it drops is a classification that nothing downstream reads: the review's
grep found no task in slices 2-5 that reads a removal field. The negative the classification pretended to support
is backlog #600's, enforced by slice 2's location rule. R1.2 adds `TMPDIR` to the recording environment, and that
point of spec contact is decided when slice 2's #602 is built, not here.

## The self-test count falls: 68 → 40. This is not a loosening

- **These figures were DERIVED, not counted by hand.** Every case label each version runs was printed, and the two
  lists were compared: 68 → 40, with 36 labels found only in the old version and 8 only in the new one.
- **32 cases were deleted, and each one tested deleted code.** By group: X1 (6) and X2 (5), which tested creation
  evidence; X3 (1), the return read; the X4 case where a join's return decides creation (1); F8 (1), decoding a
  label before matching creation; the `copies` roots (2); r2 X1 (9: annotation, list, totals); r3 F3 (3: `forget`'s
  subtree, max over seeds of the annotation counts, `targets_with_not_created`); and r3 F4 (4: the outcome split).
  The behaviour these cases pinned no longer exists.
- **Four cases were rewritten under new labels:** X4's resumed tail, X4's interleaved pids, and r2 X5 ×2. They now
  assert `unresolved` and `unpaired` rather than the deleted list. Two more cases keep their labels and assertions
  but now go through the `unres` helper: X4's unpaired remover and F5.
- **Four cases are new:** `unresolved` for a relative unlink and for both sides of a rename, `removal_calls` taken
  as the max over seeds (removers only), and `removal_calls` reported null when a record has no log.
- **Each new or rewritten rule was mutated by hand in a temp copy, and every mutation turned the suite red.** The
  rules: `nameable` (always true; ignores the label), `removed_paths` (drop rename's destination; drop renameat's;
  drop `unlink`), the `unresolved` append, and `removal_calls` (sum instead of max; no remover filter; no
  null-unless-whole). The script declares `NO-MUTATIONS`, so there are no manifest entries to update.
- `check-merge-ready.py` will HOLD on the falling count. The review predicted this HOLD and this document explains
  it.

## Decision log

`docs/reviews/decision-scheme/decision-log.jsonl`: the round-3 `split` row is now observed. The observation reads
"Phase 6 (architecture review 2026-11-11): split right but incomplete; R1 deletes the removal model", outcome
`continued`. The prospective row that follows it is **`defer`**, not the `redesign` the brief named.
`check-decision-scheme.py` refuses a second `redesign` on this unit, because it counts a repeated route as a retry.
Its trigger 3 also requires the next bet after a continued `split` to be on the same unit. The only rung left on
the ladder is `defer`, and it fits R1.1: slice 1 stops designing the removal claim and hands it to backlog #600 and
#602. Bet: round 4 (Codex) finds no BLOCKER, and its non-BLOCKER findings are FILED under the round cap.
