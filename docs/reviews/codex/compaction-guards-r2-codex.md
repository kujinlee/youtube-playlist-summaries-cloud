<!-- codex-review: model=gpt-6.1-sol -->

1. **Major — Non-main-session questions still authorize owner answers.** `scripts/compaction-state.py:269–290` **Pre-existing; incompletely fixed.**

   **Reproduction:** In a temporary copy, feed `owner_items()` an assistant AskUserQuestion with `sessionId: "A"`, then a user tool result with the same tool ID and `sessionId: "B"`. The answer reaches the owner-words section. The question also passes with `isCompactSummary: true`, `origin.kind: "task-notification"`, or wrongly typed false-valued flags (`isSidechain: []`, `isMeta: 0`). Session identity is never checked. Repeating the question record after its answer reopens the consumed ID and admits another answer.

   **Fix:** Bind both turns to the payload’s session; validate provenance field types; exclude summary and notification questions as well as results. Keep consumed IDs separately so a repeated question cannot reopen them. Preserve the RECORDED qualification.

2. **Major — The replacement paste parser introduces quadratic execution time.** `scripts/compaction-state.py:234–243` **FIX-INDUCED.**

   **Reproduction:** Execute:

   ```python
   withhold_pasted("<pasted_content>" * 30000)
   ```

   This **450,000-character** input was still running after **16.01 seconds**, when the test killed it. The regex searches from successive candidate openers, repeatedly scanning the remaining input for a nonexistent closer. The one-opener check happens only afterward. Owner extraction runs synchronously outside deadline enforcement.

   **Fix:** Check delimiter counts before attempting a match. Reject ambiguous input immediately, then use an anchored, bounded parse for the single permissible block.

3. **Major — The overall deadline does not bound file reads or process lifetime.** `scripts/compaction-state.py:441`, `:550–572` **Pre-existing; the deadline fix remains incomplete.**

   **Reproduction:** In a temporary hook copy, replace `docs/dashboard-entries.md` with a FIFO, provide valid snapshot stdin, and stub `gh` to return immediately. The snapshot process remained alive after **16.01 seconds**, exceeding its registered **15-second** timeout. The synchronous dashboard read receives no deadline. Transcript reading and extraction likewise run after the executor deadline without enforcement.

   Executor shutdown also does not bound process exit: with an injected three-second `fetch`, a snapshot given a 0.1-second deadline returned after **0.11 seconds**, but its Python process exited after **3.16 seconds**. Python joins the surviving executor thread at shutdown.

   **Fix:** Bound file type, size, reading and parsing under the same budget. Run potentially blocking capture work in a killable subprocess; `shutdown(wait=False)` cannot enforce a process deadline.

4. **Major — PostCompact assigns the latest receipt to another compaction’s summary.** `scripts/compaction-state.py:778–782` **FIX-INDUCED.**

   **Reproduction:** Execute these hook modes in a temporary root:

   ```text
   --snapshot  session_id=A
   --snapshot  session_id=B
   --audit     session_id=A, compact_summary="SUMMARY FROM A"
   --print     session_id=B
   ```

   A’s audit receives **B’s nonce** and prints for B without STALE. PostCompact ignores its payload’s session identity and reads whichever snapshot and receipt happen to be current.

   A related pre-existing freshness gap survives: another SessionStart for B within 30 minutes, with no intervening successful PreCompact, still prints the previous capture. Backward clock movement also passes the one-sided age check.

   **Fix:** Bind PostCompact to its originating session and capture generation; use per-session artifacts and reject overlapping or unidentifiable generations. Reject future-dated receipts. If the harness supplies insufficient identity to establish the triggering compaction, describe the capture as unverified rather than current.

5. **Major — Unread ledger information can still produce an all-clear audit.** `scripts/compaction-state.py:562–564`, `:598–600` **Pre-existing; incompletely fixed.**

   **Reproduction:** With successful empty PR/dashboard results, write `{broken\n` to the temporary ledger. The snapshot records `ledger: []` and `ledger_decisions: []`; auditing an unrelated summary prints:

   ```text
   the summary names everything in the snapshot (0 items checked).
   ```

   The same result occurs when main-checkout discovery fails and the fallback checkout has no ledger. Neither case produces a ledger NOT CHECKED warning in the audit. Only refusal messages beginning with `LEDGER_REL` invalidate coverage.

   **Fix:** Track capture completeness independently of successfully parsed entries. Preserve readable entries, but report corrupt lines and failed main-checkout discovery as incomplete ledger and owner-wait coverage.

6. **Minor — Owner-wait keys bypass the new metadata bound.** `scripts/compaction-state.py:489–494`, `:600–610` **Pre-existing cap defect; incompletely fixed.**

   **Reproduction:** Supply 100 valid ledger records whose IDs are their index plus 120 `x` characters and whose `what` is `WAITS-ON-OWNER: act`. The resulting snapshot was **15,700 characters**, despite `SNAPSHOT_CAP = 8000`; its keys occupied approximately **15,600 characters**. `bound_keys()` trims decisions, ledger IDs and PRs, but never `ledger_decisions`. The oversized keyline consumes the body budget and discards captured content.

   **Fix:** Bound every variable-length metadata field, including owner waits. Include omission accounting in the size calculation and enforce the final serialized cap.

All six original round-1 reproductions are now rejected by their corresponding controls. The broader attacks above refute the provenance and timeout bets; receipt matching also fails to establish compaction identity.

Validation in temporary copies: **82/82 compaction cases**, **57/57 session-state cases**, and all **39 compaction + 30 session-state mutations** killed at every named expected case. Manifest counts equal `EXPECTED_MUTATIONS`: **2,405**. All **18 hook registrations** passed. Worktree ledger reading and worktree `--add`/`--done`, garbage-input rc 0, and the print cap held. The original 48-status scenario completed in **10.03 seconds**. The real transcript, now **81,999,836 bytes**, parsed in **0.45 seconds**.

CLAUDE.md and the owner-words heading correctly say **RECORDED, not proven**. The stronger deadline, generation-identity and metadata-bound claims remain unsupported. Repository files were unchanged.

VERDICT: NOT CONVERGED
