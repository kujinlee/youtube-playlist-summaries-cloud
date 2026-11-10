<!-- codex-review: model=gpt-6.1-sol -->

Found **one BLOCKER** in the round-3 fold.

**B1 — BLOCKER: an archived miss suppresses unseen misses for the same PR.**  
Location: plan Task 7.3, [`held_by_archive`, line 1150](docs/superpowers/plans/2026-11-09-observed-reach-selection.md#L1150), called by `absorb_epoch` at line 1181.

The miss predicate checks only the PR number. It never compares the incoming miss’s targets, pushes, mutants or seeds with the archived evidence.

Concrete failure:

1. An epoch archives PR #600’s miss on `scripts/x.py`; the owner resets it.
2. The active epoch accumulates 20 clean rows and satisfies the remaining opening conditions.
3. A trusted report from an older checkout discovers another miss for #600, on `scripts/y.py`—for example, from a previously pending push or a later CI attempt. The archive never held that evidence.
4. Absorption logs `HELD BY ARCHIVE`, drops the new miss and records the report’s identity as absorbed.
5. The guard rebuilds the same defective result and accepts it. Subsequent gate reads skip that report, leaving no active latch.

I extracted and ran the plan’s Python unchanged. The reproduction returned:

```text
new_miss_present: false
absorbed["11.2"]: "2027-01-11T00:00:00Z"
guard_absorb_errors: []
clean_rows: 20
active_events: []
HELD BY ARCHIVE: 11.2 #600 miss
```

Before absorption, gate clause 9 closes on this report. After the accepted absorb, clauses 4 and 9 no longer refuse. This satisfies §8’s BLOCKER definition: a committed ledger change loses a trusted report’s new miss and passes the prescribed guard.

**Suggested fix:** identify archived miss evidence precisely—at least by PR, push HEAD/BASE, target and mutant, with the relevant replay evidence. Suppress only evidence actually archived. A report containing any unseen miss must latch even when the archive already holds another miss for that PR. Add the reproduction above as an adjacent case to the repeated-miss case.

**MINOR — contradictory report instructions.** Task 7.2 says `--report` never reads an archived epoch, but its `report()` contract requires consulting archived epochs to omit held events. An implementation cannot satisfy both. Update the input description to permit that archive read explicitly. This is not a BLOCKER.

What I tried and could not break:

- Different-PR misses latch; post-switch events for a different PR or a new target are not held.
- Extracted `absorb_errors` rejects deleted decided rows, miss-to-clean edits, dropped events, omitted listed reports, omitted miss rows and altered absorbed timestamps.
- Extracted `decide_pr` preserves misses across attempts and handles the tested mixed-sample, pending and inconclusive cases.
- The page parser reads both pages; mismatched report identities fail.
- `new_start_errors` rejects the tested backdated start.
- A no-report stub stores `null` without advancing freshness.
- Archive editing has no permitted bypass in the written guard: absorbs preserve it, and resets must append BASE’s active epoch verbatim.

Verification limits:

- The ledger, comparator, gate and guard are not implemented in this checkout. I ran the extracted functions; the complete guard and gate outcomes follow their written contracts.
- I checked the existing workflow and scripts: the checkout depth, permissions, seed restriction and aggregate-job behavior match the cited integration assumptions.
- I could not verify artifact visibility timing after attempt completion. The `null` optimization permanently skips that attempt, so its safety depends on the stated assumption that a completed attempt’s “no report” result cannot later become a visible report.
- No GitHub calls or repository edits were made.

VERDICT: NOT CONVERGED
