<!-- codex-review: model=gpt-6.1-sol -->

1. **Major — `scripts/check-features.py:188`, `scripts/gen-backlog-page.py:1123`: the shared parser can silently discard tag cells and make the gate looser than master.**

   Append this block to temporary copies of each ref’s backlog:

   ```markdown
   ## Probe
   | # | Item | Touches | Size | Bundel | Status |
   |---|---|---|---|---|---|
   | 999 | 🟡 **Probe** | f | S | (not-claimed) | open |
   ```

   Run each ref’s `check-features.py` against its corresponding documents. Both unmodified controls exit **0**. With the block appended:

   - `origin/master` exits **1**: `(not-claimed)` is claimed by no node.
   - HEAD exits **0**, reporting all areas claimed.

   `parse()` accepts the misspelled header and assigns `bundle=""` through `col.get("bundle", "")`. Consequently, `backlog_areas()` returns no tag and no problem for that row; the backlog filter treats it as untagged, and `match_rows()` places it nowhere. This refutes both the no-silent-drop and no-looser-gate bets.

   **Fix:** Validate headers in the shared parser. Preserve the existing legitimate three-column `# | Item | Status` table, but reject a six-column item table missing `Bundle` with `ShapeError`. Add the fixture above as a regression case. A temporary in-memory implementation of that validation kept the real backlog green and rejected the fixture.

The remaining requested checks passed:

| Check | Executed result |
|---|---|
| XM1 / Cm5 | Pipe-bearing tags are malformed; their named mutation is killed. |
| XM2 | Extra and missing separators each produce one gate failure naming the row; ShapeError mutations are attributed. |
| CM1 | The nearest-claimant stale-area case kills the any-descendant reversion. |
| XM3 / Cm3 | #288 appears under explainers; reverting its added tag makes the membership probe red. |
| Cm2 | All five chrome rows appear under both suite nodes; removing their status-page tag makes each membership probe red. |
| Cm4 | Published counts match `collect`; checking the pre-fold prose against those counts goes red. |
| Equality floor | Compares every parsed row, with no fixed minimum; passes for one row and fails for an empty comparison set. |
| Three mutation manifests | **59/59 killed, 59/59 attributed to their named cases**, with green controls before and after. |
| Mutation total | Declared counts and all manifest entries independently sum to **2325**, with no per-file mismatch. |

The ledger matches all **33** retagged rows exactly against the pre-retag snapshot; **zero previously closed rows changed**. `collect()` confirms **30 distinct open suite rows**: status-pages **14** (🟠3 🟡8 🟢3), feature-map **2** (🟡2), explainers **19** (🟠4 🟡10 🟢5). These match #381, the dashboard entry, and PR #421’s body. I found no additional live suite omission.

Merge `5395a82f` preserves rows **380/381/382**, both dashboard entries, both decision-log streams, and the correct **2325** pin. Self-tests passed **180/180**, **18/18**, **44/44**, and **246/246**. Both pages rendered with a temporary HOME and seeded Ask tray. Repository status remained clean.

VERDICT: NOT CONVERGED
