# Round 3 — `meter-log-tail` (backlog #501, PR #531) — coordinator — ⟳ NOT CONVERGED (Codex half); THRASHING → Phase 6 → redesigned

The Codex half ran on `97788321`: NOT CONVERGED, 1 finding (R3-F1, Low), which Codex itself marked as induced by the
r2 fix. By alternation, the Claude half did not run this round.

REVIEW GAP: claude — alternation (round 3 runs the Codex half)

This is round 3, so the finding is fixed rather than filed. It was fixed by the redesign the Phase 6 review chose, not
by another clause.

```yaml
round: 3
fixes_nontrivial: true
subject: meter-log-tail
halves:
  claude: gap
  codex: ran
findings:
  - {id: R3-F1, severity: Low, aim: deliverable, fix_induced: yes, component: scripts/check-usage-pace.py, disposition: fixed, commit: 740b5083}
```

## ⛔ THRASHING: three rounds of fix-induced findings in one component

| Round | Finding | Caused by |
|---|---|---|
| r2 | R2-F1 (Medium): the order check spanned the whole ~280-day part | r1's C1 fix |
| r2 | R2-F2 (Low): a stale `resets_at` after this window's rows set `earlier_window` | r1's F3 fix |
| r3 | R3-F1 (Low): disorder that crosses the horizon is not checked; the wrong 94 | r2's horizon |

Two consecutive rounds (r2, r3) carried findings caused by the previous round's own fix, all in `pace_line`'s cut-tail
proof in `scripts/check-usage-pace.py`. That is the arming condition in `docs/dev-process.md` → *Phases*, so a Phase 6
architecture review ran before this fold: `docs/reviews/architecture-review-2026-11-07-meter-log-tail-proof.md`
(commit `a94f12f2`).

**Its verdict: redesign (option d).** The cause, in its words: the proof needs a property of the rows that were NOT
read, and every fold checked it with a proxy computed from the rows that WERE read. The ORDER-based proof is replaced
by a TIME-based one over a stated writer contract: rows are stamped as they are appended, with at most
`METER_SKEW_S` = 1 h of skew (W1), and a reading is stamped inside its window (W2). A cut part answers only when its
oldest row is more than 1 h older than the time it must reach back to (`TAIL_TOO_SHORT` otherwise, strict `<`), and a
part that itself breaks W1 by more than 1 h is refused (`TAIL_CONTRACT_BROKEN`, naming the two rows). The horizon, the
`resets_at` order check, `earlier_window` and `this_window_seen` are deleted. Row selection and the uncut path are
unchanged.

## R3-F1: disposition

| Finding | Disposition | Commit | Case that goes red |
|---|---|---|---|
| **R3-F1**: horizon-crossing disorder gives 94 where the whole log gives 92.5 | **fixed by redesign.** The review measured that R3-F1's rows are a W1 breach ACROSS the cut (two rows appended 11 and 14 days late) and that the wrong answer needs no horizon at all: it is present on every head of the PR. Under the contract it is the stated BOUND, one sentence in the docstring and in row 501: *a row appended more than an hour late, with the lateness lying entirely before the part read, is outside the contract and cannot be seen by any rule that reads only the part.* The same rows restamped within the contract are refused. | 740b5083 | `⭐ #501 r3 BOUND (R3-F1's exact rows): …` pins the bound (94, not refused; a change that detects it goes red and must update the sentence). `⭐ #501 r3: R3-F1 IN contract …` → `TAIL_TOO_SHORT`. The class: `⭐ #501 r3 SWEEP …` (60 seeded in-contract worlds, every cut: 0 wrong; its out-of-contract control must find ≥ 1) — **red on the pre-fold head: 2 wrong in contract**. |

## Test-first, measured

The review's 12 cases were written first and run against the pre-fold `pace_line` (`a94f12f2`): **370/392**. Red there,
as the review predicted: case 3 (C1 in contract: 55), case 4 (the (a)-as-briefed counterexample: 75), case 5 (a stale
first row in strict order: 85; whole 87.5), case 6 (a stale old-window row at scale: refused), case 7 (a 1 s inversion
at scale: refused), both witness boundaries (case 8), both canary boundaries (case 9), the named-rows message, and the
sweep (2 wrong in contract). Case 2 was red by reason only. Green there, as pins: case 1 (the bound), cases 10 and 11
(reset day and R1-F3 at scale). The other red cases were the re-pinned fixtures below. After the fold: **392/392**.

### The 10 fixtures that flip, and why each was changed

| Fixture | Change | Why |
|---|---|---|
| *a tail that starts MID-LINE* | OLD row added at the part's front | the 1-row part is too short in time under (d); it still tests the dropped partial line |
| *one invalid byte in the tail* | OLD row added at the front | same; it still tests the skipped row |
| *two rows with the SAME time* | OLD row added at the front | same; it still tests that equal times break nothing |
| *a cut part that reaches back through LAST week's row* (51.5) | OLD row added inside the part | last week's row alone no longer proves the reach; the subject (a window that began after midnight) is kept |
| *R1-F3* (51) | now a refusal (`TAIL_TOO_SHORT`) | its 3-row part spans 2 minutes and proves nothing; the at-scale form is case 11 (22.99) |
| *disorder among rows of an EARLIER window* | the second row moved from 3,600 s to 3,601 s earlier | 3,600 s is inside the contract now; it still pins that rows of every window are checked |
| *R2-F2's three variants* | expected reason `TAIL_TOO_SHORT` | the rows are kept; each part holds only rows after midnight |
| *the earlier window's row PRECEDES* | expected reason `TAIL_CONTRACT_BROKEN` | ⚠ **deviation from the review's §6**, which expected `TAIL_TOO_SHORT`. The row stamped before `HZ` is appended after a row of today, ~14 days later, so the canary (which runs first) refuses it. The prototype measured it the same way: it flipped under the old reason names too |

**Deleted:** *an inversion INSIDE the horizon … still refuses* and *the horizon's boundary*: the horizon no longer
exists. Their mutations went with them.

## Mutations

`scripts/mutations/check-usage-pace.json`: 13 entries retired (the earlier-window row, the old order check and its
advance, equal times, the whole-log order refusal, the r1 F3 at-or-before-midnight clause, and all seven r2 entries
for the horizon and the `resets_at` order). One re-bound (the witness removed, formerly "a cut read is never refused
when it misses midnight"). Nine new entries: the canary removed; the witness's strict `<` made `<=`; the witness without the skew;
`before[0]` replaced by the window bound; the window bound without `HORIZON_SLACK_S`; the running maximum replaced by
the row above; `min_at` taken over this window's rows only; a whole log refused for a breach; and the witness applied
to a whole log. Each was run against the suite before it was written, and each goes red via the cases it names (the
review's §8 named case 3 for "the witness without the skew" and case 4 for `before[0]`; measured, case 3's part is
refused either way, so those entries name case 8 and, for `before[0]`, the sweep's control, which then finds nothing). The pin goes 178 → 174, with a comment in `expected_mutations.py`.
The harness's own `load_manifests`, `manifest_counts`, `pin_drift`, `anchor_problems` and `own_pin_problems` report no
load errors, no drift, no anchor problems and no pin problems. The sweep `--mutate . --only scripts/check-usage-pace.py
--allow-long-local` on `740b5083` (05:10 to 06:05): 174 mutations, 174 killed, 174 attributed to the case each names, 0
survivors. That is a diagnostic slice over one file; CI's sweep is the gate.

## Stop condition for later rounds (from the review's §9)

A later finding in this component is **admissible** only if it gives one of:
1. a log that satisfies W1 (skew ≤ 1 h, everywhere, including across the cut) and W2, where a cut answer differs from
   the whole log's without a refusal;
2. a needless refusal of a part that keeps the contract and spans more than 7 d 2 h + 1 h;
3. a defect in the reading, wiring, message, or a case that cannot fail.

A repro that needs rows appended more than an hour late, with the lateness lying before the part read, is the stated
bound (the BOUND case). It is answered by citing the review and is neither folded nor filed again. **If two consecutive
rounds after this fold again bring fix-induced, admissible findings in this component, stop folding and take option
(c): rotation by the writer (backlog 554), removing the cut rather than proving anything about it.**

## Filed, not built (the review's §7)

- backlog 553: the writer contract has no guard in the repository;
- backlog 554: rotation by the writer (option c);
- backlog 555: stale readings also reach the whole-log rule (an observation).

The decision log records the route `redesign` for the same unit as the r2 row, `outcome: null`, with a refutable
prediction.
