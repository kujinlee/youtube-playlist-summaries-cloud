<!-- codex-review: model=gpt-6.1-sol -->

## Findings

1. **HIGH — Status migration still lacks mappings for actual first words.**  
   **Spec lines 132–138, 169–170.** The table maps state keywords found within prose, rather than the Status column’s actual first words. Its “(none) — 57 rows” fallback does not identify these cases.

   **Evidence — command:**
   ```python
   import importlib.util, sys, collections
   from pathlib import Path
   sys.path.insert(0, "scripts")
   s = importlib.util.spec_from_file_location("gb", "scripts/gen-backlog-page.py")
   m = importlib.util.module_from_spec(s)
   s.loader.exec_module(m)
   rows = m.parse(Path("docs/backlog.md").read_text().splitlines())
   print(len(rows))
   print(collections.Counter(
       m.plain(r["status"]).strip().split()[0]
       if m.plain(r["status"]).strip() else "(empty)"
       for r in rows
   ))
   ```
   **Output:**
   ```text
   422
   Counter({'✅': 130, '🟡': 97, '🟠': 66, 'pending': 50,
   'OPEN': 28, '🟢': 21, '⟳': 5, 'Open.': 5, '🔴': 4,
   'open': 3, 'SPEC': 2, '(was': 1, 'SCOPE': 1, 'PARTIALLY': 1,
   'FUNCTION': 1, 'BLOCKED': 1, 'half': 1, '🔵': 1, 'FIX': 1,
   'deferred': 1, 'owner': 1, '⏳': 1})
   ```
   **Fix:** Define normalization and classify every remaining row explicitly. Include Status-cell glyphs, `pending`, and prose-leading cells; preserve action markers during migration.

2. **HIGH — Row 4 contradicts D1’s fixed exclusion rule.**  
   **Spec line 179.** D1 excludes rows referenced by **any** live ledger entry; row 4 and §7 exclude only references from live `owner-wait` entries. A routine or `owner-instruction` reference therefore produces different waiting sets.

   **Evidence — command:**
   ```bash
   sed -n '35p;179p;216p' docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md
   ```
   **Output excerpts:**
   ```text
   35: ... status: needs-you that NO live ledger entry references ...
   179: ... MINUS rows a live owner-wait entry references ...
   216: ... minus those a live owner-wait entry references ...
   ```
   **Fix:** Make row 4 and §7 implement the fixed D1 rule consistently, including what happens when a non-wait entry references a needs-you row. Reconcile the completeness requirement with that case.

3. **HIGH — Answering a picked decision has contradictory write requirements.**  
   **Spec lines 182, 187.** Line 182 requires changing the backlog status when answering; line 187 permits closing only the ledger entry. Under the latter procedure, the answered decision immediately returns to “waiting until picked.”

   **Evidence — command:**
   ```bash
   sed -n '179,182p;187p' docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md
   ```
   **Output excerpts:**
   ```text
   ... the row's status is not touched.
   ... when answered, the row's status changes in the same step.
   ... an answer closes the ledger entry or changes the row's status ...
   ```
   **Fix:** Specify one answer transaction: for a ledger item backed by a needs-you row, update that row’s status and close the entry, with interruption recovery. Reserve ledger-only closure for items without such a row.

4. **MEDIUM — Freshness falsifier can remain false indefinitely after an external merge.**  
   **Spec line 224.** `origin/master` is a local tracking reference. Without refreshing it, both the page and comparison reference can remain at the same obsolete commit—the external-merge gap explicitly identified at line 160.

   **Evidence — command:** A temporary Git fixture created a bare remote, cloned writer and reader checkouts, recorded the reader’s HEAD, then pushed another commit from the writer without fetching in the reader:
   ```python
   print("recorded source == reader origin/master:",
         recorded == git("-C", reader, "rev-parse", "origin/master"))
   print("recorded source == actual remote master:",
         recorded == git("--git-dir", remote, "rev-parse", "master"))
   ```
   **Output:**
   ```text
   recorded source == reader origin/master: True
   recorded source == actual remote master: False
   Without fetch, elapsed time cannot change either comparison.
   ```
   **Fix:** Require a freshly fetched or remotely queried master tip, an authoritative merge time, and an explicit failure/unknown result when remote verification fails.

VERDICT: NOT CONVERGED
