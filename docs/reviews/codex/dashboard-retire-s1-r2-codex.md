<!-- codex-review: model=gpt-6.1-terra -->

No findings. I could not refute the six round-1 fixes with the probes below, and the requested HEAD-tree cases behaved as intended.

All five self-test gates ran and passed:

- `check-dashboard-entry.py`: 180/180, plus 28/28 cannot-run cases.
- `goal-tree.py`: 608/608.
- `explainer-serve.py`: 298/298.
- `compaction-state.py`: 130/130.
- `regen-pages.py`: 123/123.

Round-1 checks:

- **A — missing store:** A committed temporary repository with no `docs/asks/` returned `"docs/asks/ is not tracked at HEAD … keep .gitkeep until the first ask lands"`.
- **B — invalid names:** `ASK_NAME.fullmatch` returned `False` for both `'2026-11-25-a.md\n'` and `'٢٠٢٦-11-25-a.md'`, and `True` for `'2026-11-25-a.md'`.
- **C — merged ask details:** Two asks declaring `decision: backlog #5`, one with two options and one with only one, produced merged details containing `"• one [recommended]"`, `"• two"`, and `"decision 'pick' offers 1 option(s); at least two are needed"`.
- **D — last-line edit:** Base `b'# Q?'` and head `b'# Q? changed\n'` returned `"changed in place — an ask only grows at its end"`.
- **E — directory mtime:** After removing an ask, with directory mtime 900 and remaining child mtime 100, `source_mtime` returned `(900000000000, 'docs/asks')`.
- **F — HEAD bytes:** A valid committed ask deleted from the working tree returned `([], None)`, so A1 judged the committed version.

Additional `_ask_tree` probes returned a Git error for a repository with no commits (`"Not a valid object name HEAD"`); `([], None)` for a detached HEAD with a valid store; `"is a symlink, not a regular file"` for a committed symlink; and `"not a regular file"` for a committed submodule entry.

I independently diffed the full shipping edge sets: origin/master had 368 edges and HEAD had 370. The only additions were `compaction-state.py → check-dashboard-entry.py` and `goal-tree.py → check-dashboard-entry.py`; no edges were lost.

## Loosening answers
LOOSENING-CHECK 4891b8e36209: not a loosening
LOOSENING-CHECK 68ae8d5605c9: not a loosening
LOOSENING-CHECK 28f3eb45d231: not a loosening
VERDICT: CONVERGED
