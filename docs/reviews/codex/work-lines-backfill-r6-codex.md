<!-- codex-review: model=gpt-6.1-sol -->

The current 31 markers pass the copy trial, but the END matcher still accepts false terminal evidence.

**Medium — quoted user text can end a background task early.**  
Location: [backfill-work-lines.py:1025](scripts/backfill-work-lines.py:1025).

A user message beginning with `<task-notification>` is trusted even when followed by “This is quoted historical output.” Executed probe, with the matching task and tool-use IDs in another session:

```text
PROBE quoted-user task bx1 until 2026-10-01T12:00:20.000Z session_end 2026-10-01T12:00:30.000Z
```

The quoted text closes the uncertainty window ten seconds early. A later checkpoint could therefore establish certainty while the task still runs. **UNVERIFIED:** a wrong marker caused by this condition in the real corpus.

Fix: require reliable harness provenance for user-form notices; when provenance cannot distinguish a notice from quoted text, retain uncertainty. Add a regression for a verbatim notice followed by explanatory prose.

**Medium — cross-session matching ignores contradictory task IDs.**  
Location: [backfill-work-lines.py:1113](scripts/backfill-work-lines.py:1113).

A terminal notice naming task `other`, but carrying `bx1`’s launching tool-use ID, closes `bx1`:

```text
PROBE wrong-task task bx1 until 2026-10-01T12:00:20.000Z session_end 2026-10-01T12:00:30.000Z
```

Fix: retain and match both task ID and tool-use ID across sessions; reject conflicting launch identities. Detect duplicated launch IDs conservatively.

The real corpus scan found:

```text
TOOL_IDS 30497 CROSS_SESSION_REUSED 0
```

Thus reused tool-use IDs were **not observed**; the real-data impact of this finding is **UNVERIFIED**. A non-terminal `running` notice correctly left the window open.

Executed validation:

- Control: `265/265 self-test cases passed`.
- Write against copied plans, using original birth timestamps: `wrote 31 plan file(s)`.
- Every new parent/source pair matched `links-r8.txt`: `MARKERS 31 EXPECTED 31 EXACT True LIVE_UNTOUCHED True`.
- Backup matched all copied files’ bytes and nanosecond mtimes: `BACKUP_EXACT True`.
- Second write with a fresh backup: `wrote 0 plan file(s)` and `IDENTICAL True`.
- Ground truth: `checkpoints: agree 124, disagree 0 (resolved 0), resync from unknown 329`.
- Injected failure after copying one backup file: returned `2`, reported `Nothing was written`, and `SOURCE_IDENTICAL True`. The write loop follows successful completion of `copytree`; no partial-backup continuation was found.
- All six new mutations exited `1` and failed their named expected case, covering cross-session END, empty-session grouping, printed counts, “all ticked,” missing backup, and lost backup mtimes.

No repository files or real plans were written.

VERDICT: NOT CONVERGED
