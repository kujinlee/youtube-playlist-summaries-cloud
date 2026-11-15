<!-- codex-review: model=gpt-6.1-sol -->

`python3 scripts/goal-tree.py --self-test`: **524/524 passed**. Concrete counterexamples remain:

1. **MAJOR — `scripts/goal-tree.py:435`: CLOSED unmerged satisfies a merge prerequisite.**  
   Breaking input: item says `START ONLY AFTER PR #460 merges`; PR #460 is `CLOSED`, unmerged, closed at `2026-11-02 08:00`. Output: `blocker done 11-02 (PR #460), not started`. The required code never landed; closure does not satisfy this prerequisite.

2. **MAJOR — `scripts/goal-tree.py:2229`: unreadable ledger silently becomes “none”.**  
   Breaking input: a logged snapshot with `goals: []`, `inflight_loose: []`, and both `cannot` and `needs_not_read` reporting `ledger: .claude/inflight.jsonl NOT READ (PermissionError)`. Output: `OWED AND IDLE: none — every Owed item has a reason`. The report ignores the stored source failure and asserts completeness.

3. **MAJOR — `scripts/goal-tree.py:474`: DST fallback invents almost a year of idleness.**  
   Breaking input in America/Los_Angeles: ledger recorded November 1, 2026, **01:50 PDT**; snapshot taken **01:10 PST**, twenty elapsed minutes later. Stored inputs are `11-01 01:50` and `2026-11-01 01:10`. `idle_days` returns **364**, because the repeated hour triggers the previous-year heuristic. Changing time zones can trigger the same failure.

4. **MAJOR — `scripts/goal-tree.py:457`: completion instructions become prerequisites for starting.**  
   Breaking entry: `what="Build the UI now"`, `on_done="After PR #451 merges, remove the temporary flag"`, with PR #451 open. The parser derives `waits for: PR #451 (open)` for the UI work, although only later cleanup depends on that PR. Likewise, `Do not wait until after PR #451; start now` still matches. Exact token matching does not establish a prerequisite.

5. **MAJOR — `scripts/goal-tree.py:2223`: hook discards remaining waits.**  
   Breaking snapshot item: `waits="owner approval"`, blockers PR #442 done on `10-30` and PR #451 open. Output:
   ```
   job — blocker done 10-30 (PR #442), not started · work
   ```
   Neither owner approval nor the open prerequisite appears. The item is prioritized as idle despite recorded reasons it cannot start.

6. **MINOR — `scripts/goal-tree.py:2248`: error output exceeds the hook’s width bound.**  
   Breaking input: `owed_idle_report(Path("/nonexistent/goal-review-file"))`. The emitted error line is **196 characters**, exceeding `OWED_IDLE_WIDTH = 170`. Error paths bypass the truncation applied to item lines; the bounded-output fixture tests only successful reads.

VERDICT: NOT CONVERGED
