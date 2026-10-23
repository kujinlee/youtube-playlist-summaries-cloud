<!-- codex-review: model=gpt-6.1-sol -->

No write-safety findings remain for the current corpus.

Executed verification:

- **END matching** — `scripts/backfill-work-lines.py:1032,1117`: quoted notice, wrong-task ID, two notices, cross-session reused ID, cross-session quoted notice, and non-terminal status all left the window open:
  ```text
  until 2026-10-01T12:00:30.000Z session_end 2026-10-01T12:00:30.000Z
  ```
  The valid same-session control ended at `12:00:20`. Inspection confirms no cross-session tool-use-ID lookup remains.

- **Real harness notices:** `454` terminal user notices begin with the tag; all `454` pass the exact-block rule. Ten genuine notices with a system-warning prefix remain refused, as before this round. This conservatively retains uncertainty; the new rule introduces no observed refusal.

- **Backup ordering** — `scripts/backfill-work-lines.py:1616–1648`: the complete `copytree(..., copy_function=shutil.copy2)` precedes the write loop. Backup comparison covered every copied file’s bytes and nanosecond mtime:
  ```text
  BACKUP_EXACT True
  ```
  Injecting failure after one backup file, against fresh unmarked copied plans:
  ```text
  FRESH_FAILURE 2 … Nothing was written. UNCHANGED True
  ```
  No partial-backup continuation was found.

- **Copied real plans**, using original birth timestamps:
  ```text
  wrote 31 plan file(s)
  MARKERS 31 EXPECTED 31 EXACT True LIVE_UNTOUCHED True
  SECOND 0 wrote 0 plan file(s) … IDENTICAL True
  ```
  Every new parent/source pair matched `links-r9.txt`.

- **Mutations:** five surviving mutations from the original six each exited `1` with `NAMED_REASON True`: empty-session grouping, printed count, “all ticked,” missing backup, and lost backup mtimes. The cross-session mutation was retired with its implementation. Both new notice mutations also exited `1` for their named reasons.

- **Controls:**
  ```text
  268/268 self-test cases passed
  checkpoints: agree 124, disagree 0 (resolved 0), resync from unknown 329
  ```

No repository files, real plans, or git state were written.

VERDICT: CONVERGED
