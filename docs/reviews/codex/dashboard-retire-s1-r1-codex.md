<!-- codex-review: model=gpt-6.1-terra -->

**Findings**

- **HIGH — A1 passes when the ask directory is missing.** In [check-dashboard-entry.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/dashboard-retire-s1/scripts/check-dashboard-entry.py:684), deleting and committing the sole tracked `docs/asks/.gitkeep` leaves `git ls-tree` with no names. The code passes `present = []` to `read_asks`, whose missing-directory check runs only under `if names is None:`. Consequently, `problems += read_asks(root / ASKS_REL, present)[1]` returns no problem and A1 passes, even though the directory is absent. F1 excludes `.gitkeep`, so it does not catch this deletion.

- **MEDIUM — A1 accepts a filename with a trailing newline.** In [check-dashboard-entry.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/dashboard-retire-s1/scripts/check-dashboard-entry.py:503), `ASK_NAME` ends in `\.md$`, and the reader tests it with `ASK_NAME.match(name)`. Python’s `$` also matches immediately before a final newline. A tracked file named `2026-11-25-a.md\n` containing `# Question?\n` therefore passes A1 despite violating the specified filename rule. Its displayed stem is also wrong because the reader removes the final three characters assuming they are `.md`.

The goal-tree implementation retains an open ask with no decision block and displays a warning. F1 has direct coverage for an edited question and a deleted ask; both are intended refusals. I did not identify an ambient pass in the reviewed A1 and F1 fixtures.

**Self-tests**

- `check-dashboard-entry.py`: passed, 176/176 plus 23/23 cannot-run cases.
- `goal-tree.py`: passed, 607/607.
- `compaction-state.py`: passed, 130/130.
- `explainer-serve.py`: passed, 297/297.
- `regen-pages.py`: passed, 123/123.
- `check-reference-namespace.py`: passed, 51/51.
- `check-shipping-sets.py`: started but had not completed when the review ended; this gate did **not** complete.

## Loosening answers
LOOSENING-CHECK 4891b8e36209: finding: the self-test now accepts the 370-edge fingerprint that master’s 368-edge fingerprint refused
LOOSENING-CHECK 68ae8d5605c9: not a loosening
LOOSENING-CHECK 28f3eb45d231: not a loosening
VERDICT: HOLD
