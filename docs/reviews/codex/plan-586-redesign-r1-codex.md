<!-- codex-review: model=gpt-6.1-sol -->

Found **two BLOCKERs and one MAJOR** in the rewritten plan. These are failures of the specified rules; the proposed scripts do not exist yet.

1. **BLOCKER — The guard permits advancing the watermark past an omitted miss.**  
   **Location:** plan Task 7.3, lines 924–937; Task 8.1, lines 1039–1044.

   **Scenario:** BASE has 20 clean rows and `absorbed_through=T0`. A trusted report at T1 holds a new miss. A ledger PR retains all existing rows and advances only `absorbed_through` to T2, where T2 ≥ T1. None of the enumerated guard refusals applies: no existing decision changed, no count decreased, no unsupported row was added, and the watermark moved forward. After merge, clause 9 ignores the miss report because its timestamp is behind the watermark. The gate opens despite an unabsorbed trusted miss.

   The guard validates the provenance of **added** content but never requires the inclusion of all tightening evidence covered by the new watermark. Correct behavior of `--absorb` does not protect against a manually edited ledger.

   **Fix:** Require the guard to reconstruct the complete absorb result and compare it with HEAD, including every applicable miss and post-switch event. Reject watermark advancement that skips tightening evidence. Add a watermark-only omission case.

2. **BLOCKER — A late-uploaded report can fall behind an honestly advanced watermark.**  
   **Location:** plan Task 7.2, lines 830–838; Task 7.3, lines 914–922; Task 8.1, clause 9.

   **Scenario:** Two permitted overlapping comparator runs execute. R1 writes a miss report with `generated_at=10:00`, but its upload is delayed. R2 writes and uploads a report at 10:01 without that miss—for example, its comparison is inconclusive. An absorb sees only R2 and commits `absorbed_through=10:01`. R1 then uploads successfully. Every subsequent gate listing can download R1, yet clause 9 discards it because 10:00 is not later than 10:01. The switch remains open.

   This requires neither a malicious ledger edit nor false GitHub metadata. Report generation order does not establish publication order.

   **Fix:** Track absorbed report identities and evaluate every unabsorbed report for tightening evidence, regardless of `generated_at`. Keep the timestamp for freshness only. Test delayed publication across an absorb.

3. **MAJOR — The specified epoch reset cannot clear a latch while satisfying the guard.**  
   **Location:** plan Task 7.3, lines 910–912 and 928–936; Task 8.1, clause 4; Task 8.2, lines 1132–1136.

   **Scenario:** The ledger contains a miss or post-switch event. The owner authorizes a new epoch. Task 8.2 says this allows restarting the count and eventually reopening, but the schema places rows and events outside `epoch`, while the reset archives only the old `epoch` object. Retaining the old rows/events makes clause 4 refuse forever; removing them violates the guard’s unconditional preservation rules. The later test referring to old rows “in `previous_epochs`” has no corresponding archive schema.

   **Fix:** Define an archived epoch as a complete snapshot of its decisions and events. Validate that snapshot verbatim during reset, and apply gate conditions only to the active epoch. Add a reset case beginning with an actual latched miss.

**What I tried and could not break**

- HEAD ledger, backlog and Q1 edits cannot directly open their own PR’s gate under the specified BASE reads.
- Extra clean report rows cannot satisfy the committed ledger’s 20-row requirement.
- The union catches an older miss omitted by the newest report when both remain newer than the watermark.
- Ordinary decided-row deletion, miss-to-clean changes and event removal are explicitly refused.
- The workflow dependencies match the existing repository: `verify` has full history; `mutation-sweep-complete` depends on the sweep and uses `always()`. The planned `!cancelled()` addresses the skipped-selector dependency.
- Predecessor search, artifact genesis and ledger concurrency are removed as operational mechanisms.

**Verification limits**

I checked head `18d72977`, its diff, the requested spec sections, slices 6–8, and relevant workflow/script implementations. A small in-memory Python transcription of clause 9 reproduced both watermark failures; this was not execution of an implemented gate.

The ledger, comparator, gate and guard are absent, so their actual validation, report schemas and end-to-end behavior cannot be tested. I made no GitHub calls. `actionlint` is unavailable. No tracked files were changed.

VERDICT: NOT CONVERGED
