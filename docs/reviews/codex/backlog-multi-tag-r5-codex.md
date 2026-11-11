<!-- codex-review: model=gpt-6.1-sol -->

**The DEFER termination gate passes.** Executed in temporary archive copies of `origin/master` and `cf2f4d59` under `/tmp/multitag-r5.3HvAi3`. Repository unchanged.

**Minor finding — stale verification totals:** `docs/dashboard-entries.md:17945` and [PR #421’s “Gates” table](https://github.com/kujinlee/agentic-ai-docs/pull/421).

Reproduction: compare the published totals with the manifests and executed self-tests. The dashboard still reports 18 backlog mutations and 28 checker mutations; actual totals are **21 and 30**. The PR table reports 185 backlog cases, 48 checker cases, 20 backlog mutations and aggregate 2331; actual results are **186, 49, 21 and 2332**. This is nonblocking documentation drift under DEFER.

1. **Paired probes**

   - Original **61**: zero master-red/HEAD-green; HEAD stricter on **7**.
   - **52 additional paired probes** covered indentation, nested/list tables, blockquotes, BOMs, CRLF, trailing header whitespace and adjoining tables.
   - One additional master-red/HEAD-green result: append a valid six-column table containing `| 999 | 🟡 **Probe** | f | S | (—) | open |`. Master exits **1**, HEAD **0**.

   That last result refutes an *unqualified* “no such input exists” claim, but implements the sentinel behavior explicitly required in this round (`scripts/gen-backlog-page.py:1268`). It is not an undeclared-block bypass. Fully indented or quoted tables remain skipped by **both** refs.

2. **All seven changed cases assert the stricter external contract**

   | HEAD location / case | Before | After |
   |---|---|---|
   | `scripts/gen-backlog-page.py:2589` — no `#` header | Empty unread list | Refusal naming the opening header |
   | `:2611` — same-section legend | Exact three unread lines | Undeclared legend refuses; declared legend still produces those exact lines |
   | `:2639` — own-section legend | Silently ignored | Undeclared legend refuses; explicitly declared legend produces no unread lines and preserves the item |
   | `:2673` — plain/decorated pairing | Read/report booleans equal | Every context reports or refuses; wherever plain rows render, decorated rows are reported |
   | `:2676` — nonvacuous pairing | Both read outcomes occur | Both read outcomes **and** both report/refusal outcomes occur |
   | `:2684` — headerless decorated row | Decorated row silent; plain row raises | Both raise `ShapeError` |
   | `:2735` — new section | Empty unread list | Refusal explicitly names `## Notes` |

   These are contract changes from silence to reporting/refusal, not blanket exception acceptance.

3. **Empty groups confirmed by execution**

   At `scripts/gen-backlog-page.py:1264`:

   ```text
   ()             → ([], True)
   ( )            → ([], True)
   ( / )          → ([], True)
   (—)            → ([], False)
   (tooling) ()   → (['tooling'], True)
   ```

   `check-features` rejects all four malformed forms.

4. **Mutation evidence confirmed**

   Executed:

   ```text
   check-plan-code.py --mutate <temporary HEAD>
     --only scripts/gen-backlog-page.py
     --only scripts/check-features.py --allow-long-local
   ```

   Result: **51/51 killed, 51/51 attributed to their named cases, zero survivors**, with green controls before and after: backlog **21**, checker **30**.

   The rebound anchor at `scripts/mutations/gen-backlog-page.json:95` matches **exactly once**, at `scripts/gen-backlog-page.py:1278`, inside `cell_tags`, not `bundle_tags`. `EXPECTED_MUTATIONS` and actual manifests both sum to **2332**, with no per-file mismatch.

5. **Suite counts and #383 confirmed**

   Executed `collect()`, excluding closed fragments:

   | Feature | Open | Severity |
   |---|---:|---|
   | status-pages | 14 | 🟠3 🟡8 🟢3 |
   | feature-map | 3 | 🟡3 |
   | explainer-pages | 19 | 🟠4 🟡10 🟢5 |
   | Distinct | **31** | |

   These match `docs/backlog.md:363`, `docs/dashboard-entries.md:17957` and the PR’s current suite-count prose/table.

   **#383 has a concrete FAILS IF** at `docs/backlog.md:365`. Reproducing its decorated row inside the real Items table leaves the features fragment **byte-identical to baseline on both refs**, confirming the filed, pre-existing omission.

HEAD self-tests: **186/186 backlog, 49/49 checker, 18/18 features, 246/246 harness**. Corresponding master suites also pass.

VERDICT: CONVERGED
