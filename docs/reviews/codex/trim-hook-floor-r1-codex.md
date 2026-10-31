<!-- codex-review: model=gpt-6.1-sol -->

- **HIGH — `scripts/session-state.py:367–374`: unmarked owner waits disappear.** Input: an entry with `what="Blocked pending owner approval to merge #453"` and `on_done="Only merge after owner says yes"`, followed by five routine entries. The approval entry disappears entirely, and the output says `0 waiting on the OWNER`. Even within the five shown, its `on_done` restriction disappears. Previously both fields were printed.

- **HIGH — `scripts/compaction-state.py:774–777`: recorded owner decisions are hidden.** Input: an owner prompt or paired answer saying “Do not merge #453 until I approve” in the owner’s recent words section. The digest retains its headings but drops the decision without flagging that omission. The new test at line 1240 explicitly expects the existing “pause and finish the guards” instruction to disappear.

- **MEDIUM — `scripts/session-state.py:369`: “newest” means physical file position.** Input: six entries with the latest `at` timestamp on the first line and older timestamps on the following five. The latest entry disappears. `_parse()` preserves file order; this selection never compares timestamps. Re-adding an old job also promotes it by moving it to the end.

- **MEDIUM — `scripts/session-state.py:376`: the recovery path resolves against the wrong checkout.** Input: run the hook from linked worktree `/repo/wt` while its ledger is read from `/repo/main/.claude/inflight.jsonl`. Printed `full: .claude/inflight.jsonl (main checkout)` resolves from the current directory to `/repo/wt/.claude/inflight.jsonl`; the actual absolute path is unavailable in this output. The compact block now depends on that recovery path.

- **MEDIUM — `scripts/compaction-state.py:777`: a retained warning can lose its warning text.** Concrete input to `digest()`: a non-owner section body line containing `"x" * 210 + " NOT CAPTURED — status unavailable"`. Selection finds the marker, but `clean(line, 200)` removes both marker and explanation. I reproduced output containing only the truncated `x` prefix. This violates the promise to retain every `NOT CAPTURED` line.

Both requested self-tests ran in the foreground and passed: **73/73** and **100/100**. The size fixtures use matching nonces and fresh receipts, so their reductions are not passing merely because the snapshot was rejected. Retained data remains cleaned and inside DATA framing. The existing “shows the snapshot” test now checks only its title, so it no longer establishes its original meaning.

**NOT CONVERGED**
