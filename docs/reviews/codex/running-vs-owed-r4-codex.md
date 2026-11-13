<!-- codex-review: model=gpt-6.1-sol -->

- **Medium — scripts/goal-tree.py:452:** Resolved-PR ownership still misses mixed threads. Through real `derive`, a thread declaring `backlog #10, backlog #11 · waits on the owner`, with #10 merged and #11 resolving to open PR #30, derives `merged` with `open_prs=[]`. PR #30 appears as stray **Running** work, bypassing the declared wait. The same happens with `PR #20, backlog #11` when #20 is merged. The r3 fold collects `resolved` only when neither a named PR nor a merge takes precedence.

- **Low — scripts/goal-tree.py:1421:** Preserving the absorbed group’s PR identities lacks failing-by-name coverage. Removing only `g["prs"] |= o["prs"]` leaves **377/377 cases green**. This breaks subsequent merging: groups `[21]` and `[30,40]`, joined by `[21,30]`, lose identity #40; a later entry sharing only #40 becomes a duplicate and can escape wait consolidation.

Verification: **377/377 baseline cases pass; all 23 registered running-vs-owed mutations fail every expected case by name.**

VERDICT: NOT CONVERGED
