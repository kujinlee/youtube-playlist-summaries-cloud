<!-- codex-review: model=gpt-6.1-sol -->

Found three **Medium** issues:

1. **Ledger declarations can duplicate work across goals.** [goal-tree.py:280](scripts/goal-tree.py#L280) builds `declared` only from tracked threads. Two ledger entries declaring `fix · PR #30` under `g` and `h` both appear. Within one goal, changing the relation also permits duplicate refs. Exact-key collisions silently retain the first entry.

2. **Merge handoff can produce false timeline additions/removals.** [goal-tree.py:290](scripts/goal-tree.py#L290) suppresses ledger threads by shared ref, but `changes` identifies threads by goal and exact key. Replacing ledger `fix · PR #30` with tracked `side · backlog #10, PR #30` produced:
   
   ```text
   added [side] backlog #10, PR #30: …
   removed [fix] PR #30
   ```
   
   I appended both snapshots to a temporary log and rendered its replay; the false removal appears on the page.

3. **Thread prose creates unrelated ledger associations.** [goal-tree.py:301](scripts/goal-tree.py#L301) scans the entire `thread` string. With `fix · PR #30 · depends on PR #777`, `_ledger_numbers` returns `{30, 777}`. A separate tracked `PR #777` thread consequently becomes `inflight` with this entry’s “build” detail. Structured refs should determine this association.

Verification performed:

- Confirmed requested HEAD and read PR #505.
- Parser differential: **234 inputs**, including the complete real threads document, its thread lines, and suite parser inputs. Results and error messages—including line numbers—exactly matched master.
- Suites: **317/317**, **113/113**, compaction **125/125**.
- Mutation counts **208 / 97**; all eight new mutations matched exactly once and failed their named case.
- Confirmed tracked declarations win, preserve tracked order, and suppress shared-ref ledger declarations.
- Extra keys survive ledger reading; session rendering and NEEDS YOU remain unchanged. Both stray flags correctly report `--add`.
- Parked entries remain parked; declared owner-wait entries use the existing parked classification.

Reproduction scripts: `/tmp/review505.py`, `/tmp/review505-extra.py`. No tracked files modified; no `.claude/plans/` contents read.

VERDICT: NOT CONVERGED
