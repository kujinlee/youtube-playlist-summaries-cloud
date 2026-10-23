<!-- codex-review: model=gpt-6.1-sol -->

I would hold the real `--write`. The copy-write path passes, but the fold still permits premature END attribution.

1. **MEDIUM — END records are matched by bare task ID, without validating the task lifetime.**  
   Location: `scripts/backfill-work-lines.py:950–953, 1025–1028, 1041–1042`.

   Executed fixture:
   ```text
   REUSED_ID two.parent= -
   windows [('2026-10-01T12:00:40.000Z', '2026-10-01T12:00:20.000Z', 'bx1')]
   ```
   An earlier completion for reused `bx1` ends the new command **before it starts**. The checkpoint then authorizes `-` while the new task remains running.

   TaskStop is also accepted at its request timestamp, without awaiting a successful result:
   ```text
   STOP_REQUEST_BEFORE_COMPLETION two.parent= -
   ```
   That fixture supplied no successful stop result and completed the task later.

   **Fix:** match structured terminal records to the session and task incarnation, require END after START, and await successful TaskStop results. Ignore quoted notification text and nonterminal statuses. Separate files currently isolate task IDs, but session identity is not checked within each file.

   Corpus checks found no reused IDs or END-before-START cases. However, conservatively extending background lifetimes to session end changes **11 of the 32 selected parents to UNKNOWN**. This does not establish that those links are wrong; it means END validation matters to write readiness.

2. **MEDIUM — a background result does not establish background execution.**  
   Location: `scripts/backfill-work-lines.py:977–979, 1022, 1041–1042`.

   Executed fixture:
   ```text
   AUTO_BACKGROUNDED_RESULT two.parent= -
   windows []
   ```
   A result containing `Command running in background with ID: bx1` sets `task`, but the extended lifetime depends exclusively on input `run_in_background`. Without that flag, the window ends at the initial tool result.

   The real corpus contains one such result, in `agent-a465a4a12463b5c9b.jsonl`, task `b21zliex2`.

   **Fix:** let a recognized background result establish background execution and use its matching completion, or the session-end fallback. A foreground command missing its result also currently falls back to START; use the conservative fallback there too. The real corpus contained zero foreground commands missing results.

3. **LOW — another hook is treated as evidence of the Stop hook.**  
   Location: `scripts/backfill-work-lines.py:993–994, 1046–1047`.

   Executed PostToolUse-only fixture:
   ```text
   POSTTOOLUSE_ONLY two.parent= -
   ```
   No Stop evidence exists in that fixture; the fully ticked `one` should remain its parent.

   **Fix:** require evidence of the relevant Stop hook, grouped by session identity across files. Update the attachment fixture and mutation accordingly.

   Measured present-day effect:
   ```text
   HOOK_ONLY_OTHER_FILES 0
   SPLIT_SESSION_IDS []
   STRICT_STOP_EFFECT_KEEP []
   ```
   Thus this defect changes none of today’s 32 selected parents.

Verification completed:

- `243/243 self-test cases passed`.
- Ground truth passed: `agree 148, disagree 0`.
- Dry run reproduced `keep 24, keep-banner 8, no-marker 91, untouched 2`.
- On a temporary copy of plans plus `last-plan`:
  ```text
  WRITE1 0 wrote 32 plan file(s)
  WRITE_MISMATCH []
  WRITE2 0 wrote 0 plan file(s) ... IDENTICAL True
  LIVE_UNCHANGED ['work-lines-always-on', 'work-lines-backfill']
  ```
- All 12 new mutations returned failure with their declared assertion failures. They are killed for their named reasons; the hook-attachment mutation nevertheless enforces the incorrect assumption in finding 3.
- The L2 comment now identifies the two relevant ignored paths correctly.

No real plans or repository/worktree files were written. Fix END attribution and rerun the affected-row checks before writing the owner’s plans.

VERDICT: NOT CONVERGED
