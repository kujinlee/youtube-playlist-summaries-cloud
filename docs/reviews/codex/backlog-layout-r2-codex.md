<!-- codex-review: model=gpt-6.1-sol -->

## Findings

1. **LOW — `scripts/gen-backlog-page.py:1026`, rows 153, 311, 423 — clause endings falsely reject genuine lists.** `fix_induced: true`.
   
   Reproducer: render row 423. Its first item ends “before writing a case; (2) dropping…”. Stripping `;` turns `case;` into a reference word, rejecting the entire two-item list. Rows 153 (`step;`) and 311 (`case;`) fail similarly.
   
   Fix: distinguish a reference immediately before a marker from a previous item ending at a clause boundary; add these real-row regressions.

2. **LOW — `scripts/gen-backlog-page.py:1031`, rows 222, 224, 340 — alternative lists lose indentation.** `fix_induced: true`.
   
   Reproducer: render row 340’s `WORK:` block: `(a) cache…; (b) or authenticate…; (c) or set…`. The unconditional `or` rejection suppresses this explicit options list. Rows 222 and 224 also lose genuine `Decide:` lists.
   
   Fix: distinguish sufficiently developed, clause-separated alternatives from bare references such as `(a) or (b)`; retain both positive and negative regression cases.

3. **LOW — `scripts/gen-backlog-page.py:3951` — strengthened wording check still accepts joined words.** `fix_induced: true`.
   
   Reproducer:
   ```python
   _same_words_html(
       "alpha<br>beta",
       '<div class="seg">alphabeta</div>',
   )  # True
   ```
   Both comparisons erase the original `<br>`, so separate rendered words can become one while passing. This demonstrates a test blind spot, not an observed production wording change.
   
   Fix: preserve original markup when checking that only layout wrappers were inserted, and account for existing rendered breaks.

Validation: **233/233 self-tests pass**. All 14 changed mutations have unique anchors and uniquely named expected cases; each fails its named layout case(s). The eight requested rows render correctly. No newly gained block boundary was wrong; lists decrease **72→64**, with no gains, and provenance-clause rows decrease **310→267**.

VERDICT: NOT CONVERGED
