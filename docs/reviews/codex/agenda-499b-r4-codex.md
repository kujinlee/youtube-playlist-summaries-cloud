<!-- codex-review: model=gpt-6.1-sol -->

Two remaining findings at `48fc22e7`, both below Blocking and therefore for filing under the round cap.

1. **High — malformed history still crashes page replay.** In [ `_steps_ok()`](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/build-499b/scripts/goal-tree.py:1180), history steps’ optional `refs` are iterated without checking their container type. I changed one otherwise valid history step to `"refs": 1`, wrote the snapshot to a temporary log, and ran:
   ```python
   render_page(read_log(temp_log), built)
   ```
   `read_log()` accepted it; rendering raised `TypeError: 'int' object is not iterable`. Direct calls to `snap_history()`, `agenda_lines()` and `agenda_html()` also raised. Malformed history needs to return a warning rather than throw during validation.

2. **Medium — duplicate step numbers pass `ok` and invent timeline transitions.** [snap_agenda()](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/build-499b/scripts/goal-tree.py:1187) accepts two steps numbered `1`, with states `next` and `merged`. Running `changes(previous, deepcopy(previous))` on that accepted agenda emitted:
   ```text
   agenda step 1: merged → ⬜ next — A
   ```
   These were identical snapshots. Require unique step numbers before comparing steps.

Verification completed:

- **312/312** self-tests passed; docstring says **312**.
- Manifest length and pin both **203**; every anchor unique.
- All **51 backlog #499 mutants** failed every named expected case on a temporary scripts copy, without tracebacks.
- Real recording, derived steps, free-step ticking, snapshotting and page replay passed. Replacement through `main()` with an unread source preserved frozen `cannot`; subsequent agenda validation returned `ok`.
- Reader audit confirmed the two direct forwarding accesses in `tree_blocks()` and `agenda_html()` remain guarded. No additional bypass was found.

Tracked files remain unchanged. Nothing under `.claude/plans/` was read.

VERDICT: NOT CONVERGED
