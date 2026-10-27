<!-- codex-review: model=gpt-6.1-sol -->

1. **Major — `scripts/check-features.py:188`: unread rows disappear from validation, leaving the gate looser than master.**

   Append this block to temporary copies of each ref’s backlog:

   ```markdown
   ## Probe
   | # | Item | Touches | Size | Bundle | Status |
   |---|---|---|---|---|---|
   | ⭐999 | 🟡 **Probe** | f | S | (not-claimed) | open |
   ```

   Run `python3 scripts/check-features.py` in each copy. Both unmodified controls exit **0**. With the probe:

   - **origin/master exits 1:** `(not-claimed)` is claimed by no node.
   - **HEAD exits 0:** reports every backlog area claimed.
   - **Both HEAD page generators exit 0:** the backlog page warns `UNREAD` and omits the row; the features page silently omits it.

   Replacing `⭐999` with `abc` reproduces the same master-red/HEAD-green result.

   `parse()` records rejected row-like lines only when given its `unread` argument (`scripts/gen-backlog-page.py:1116`). `backlog_areas()` supplies no argument, so these rows—and their tags—vanish before validation. The schema check does not close this remaining regression from adopting the shared parser.

   **Fix:** collect unread lines in `backlog_areas()` and return gate failures naming them. Add decorated-number and noninteger-number regression cases, plus a mutation removing that enforcement. An executed in-memory implementation rejects this reproduction while keeping the real backlog green.

The remaining checks passed:

| Check | Executed result |
|---|---|
| Requested header, missing-header, repeated-header, fenced-header, alignment and non-tag pipe probes | No additional findings; no master-red/HEAD-green results |
| `TABLE_SCHEMAS` | Exactly matches both real item-table headers |
| Named mutation kills | **61/61 killed and attributed:** backlog 18, features 15, checker 28 |
| `EXPECTED_MUTATIONS` | Declared counts and manifests independently sum to **2327**, with no per-file mismatch |
| Self-tests | **182/182**, **18/18**, **45/45**, **246/246** |
| Published suite counts | `collect()` confirms **30 distinct open rows**: status-pages **14** (🟠3 🟡8 🟢3), feature-map **2** (🟡2), explainer-pages **19** (🟠4 🟡10 🟢5); matches #381, dashboard and PR body |

Evidence ran under `/tmp/multitag-r3.o436m0`, with temporary HOMEs for rendering. Repository status remains clean.

VERDICT: NOT CONVERGED
