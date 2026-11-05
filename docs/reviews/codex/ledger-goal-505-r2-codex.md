<!-- codex-review: model=gpt-6.1-sol -->

Found **3 Mediums and 1 Low**.

1. **Medium — “first wins” changes after an ordinary re-`--add`.**  
   `ledger_threads` uses file order (`scripts/goal-tree.py:298`), while `ledger_add` removes the existing entry and appends its replacement (`scripts/session-state.py:356`). Using the real writer, re-adding `first` changed order from `[first, second]` to `[second, first]`. PR #30 moved from goal `g` to `h`; the warning reversed its winner. Log and `--page` replay reported:
   ```text
   added [side] PR #30: …
   removed [fix] PR #30
   ```
   Refreshing the same declaration therefore changes ownership and creates false history.

2. **Medium — hand-off pairing selects unrelated threads and hides real removals.**  
   `changes` pairs the first new tracked thread sharing **any** ref (`scripts/goal-tree.py:560`).
   
   Replayed ledger `backlog #10, PR #30` against these tracked additions:
   ```text
   side · backlog #10, PR #99
   fix · backlog #11, PR #30
   ```
   It called the PR #99 sibling `declared on master` and reported the actual PR #30 successor as `added`. With the ledger entry completed and only the unrelated sibling added, it still emitted `declared on master`, suppressing the genuine removal. Both failures survive log replay and `--page`. A standalone removal correctly emits `removed [fix] PR #30`.

3. **Medium — five mutation anchors no longer resolve.**  
   Counts match **211 / 97**, but these mutations each match **zero** times:
   
   - relation outside the closed set;
   - trailing prose accepted in refs;
   - duplicate thread in one goal;
   - ledger thread duplicates a tracked thread;
   - `--add` drops the declared kind.

   All **303 applicable mutations** resolved once and failed their named cases, including the three new fix mutations. The requested every-mutation guarantee therefore fails.

4. **Low — warning changes are described as wording noise.**  
   `changes` ignores `ledger_problems`. Adding and then clearing a malformed declaration produced this timeline summary for both transitions:
   ```text
   no change a reader would see (the stored tree differs only in wording)
   ```
   The page displays the warning within the affected snapshot, but its timeline misrepresents its appearance and resolution.

Other checks: **321/321** and **113/113** passed. I could not refute the structured-ref association fix: malformed threads remain visible as problems/loose work, and independently named refs in `id` or `what` retain their associations.

Evidence: [replay script](/tmp/505-r2-replay.py), [replay output](/tmp/505-r2-replay.txt), [rendered pages and logs](/tmp/505-r2-evidence), [mutation audit](/tmp/505-r2-mutations.txt).

Reviewed `ebe8c936^..HEAD` at the requested HEAD. No tracked files modified; no `.claude/plans/` contents read.

VERDICT: NOT CONVERGED
