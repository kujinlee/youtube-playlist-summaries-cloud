<!-- codex-review: model=gpt-6.1-sol -->

Found two remaining issues at `6caef115`.

1. **High — an agenda accepted as `ok` still crashes page replay.** [snap_agenda()](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/build-499b/scripts/goal-tree.py:1197) validates `refs` as a list without validating its entries. I supplied an otherwise valid agenda with:
   ```json
   "refs": [1]
   ```
   `snap_agenda()` returned `ok`. Both `goal_agenda_steps()` and `render_page(read_log(temp_log), ...)` raised:
   ```text
   TypeError: 'int' object is not iterable
   ```
   The failure comes from `_refset()` converting each entry to a tuple. Validate reference entries before returning `ok`.

2. **Low — falsy malformed history is silently discarded.** [snap_history()](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/build-499b/scripts/goal-tree.py:1207) normalizes the value with `or []` before validation. I confirmed `agenda_history: false` returns `([], None)`, hiding malformed history without the promised warning.

The literal “only readers” claim also fails: `tree_blocks()` reads `snap.get("agenda")` at line 1354, and `agenda_html()` indexes `snap["agenda"]` at line 1535. Both pass through guarded readers; I found no separate crash from those accesses.

Verification completed:

- **312/312** self-tests passed; docstring says **312**.
- Manifest length and pin both equal **201**; every mutation anchor occurs exactly once.
- All **49 backlog #499 mutations** failed every named expected case on temporary scripts copies, without tracebacks.
- Real `main()` recording, free-step ticking, snapshotting and page replay succeeded. Derived and ticked steps read `ok`.
- Replacement through `main()` with an unread source preserved frozen `cannot` states; the subsequent snapshot read `ok` and replayed successfully.

Tracked files remain unchanged. Nothing under `.claude/plans/` was read.

VERDICT: NOT CONVERGED
