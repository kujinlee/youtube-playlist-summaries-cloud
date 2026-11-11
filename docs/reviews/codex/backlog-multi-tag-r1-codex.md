<!-- codex-review: model=gpt-6.1-sol -->

1. **Major — `scripts/gen-backlog-page.py:1430`, `:2081`: an accepted tag can never match its filter.**

   **Reproduction:** In a temporary backlog copy, change #288’s Bundle to `(tooling/a\|b)`. `check-features` exits **0**; `cell_tags` returns `(['tooling / a\\|b'], False)`. The card renders:
   ```html
   data-tags="tooling|tooling / a\|b"
   ```
   The browser’s `.split('|')` separates the leaf into two strings. Selecting its filter or chip therefore hides the row, although the features page assigns it through the `tooling` family.

   **Fix:** Encode the tag array as JSON and parse it accordingly, or explicitly reject pipe-bearing tags with an actionable diagnostic. Add a case exercising filter membership for an escaped pipe.

2. **Major — `scripts/check-features.py:187–190`: table corruption bypasses the malformed-cell gate.**

   **Reproduction:** In a temporary copy of the real backlog, replace #288’s Bundle with `(tooling) | (tooling)`. Running `check-features.main()` against that copy exits **0**, reporting all areas claimed. Running the backlog page’s parser against the same file raises:
   ```text
   ShapeError: row has 7 cells, header has 6
   ```
   The checker reads only `cells[-3]`, accepting the second fragment and ignoring the corrupted table shape.

   **Fix:** Obtain Bundle cells through the shared header-aware row parser and turn `ShapeError` into a gate failure. Test extra and missing column separators.

3. **Major — `docs/backlog.md:278`: #288 remains missing from the comprehensibility suite.**

   **Reproduction:** With the committed files, `match_rows` assigns #288 only to `guard-and-gate-harness`. Its text concerns enforcement of the **explainer delivery procedure**, including `.agents/skills/shared/explainer-delivery.md`. Adding `(comprehensibility/explainers)` also places it under `explainer-pages`.

   Calling it a “guard row” does not consistently justify exclusion: the retag includes suite-specific coverage and validation work such as #113, #143, and #344. Consequently, suite status still omits open work on its delivery contract.

   **Fix:** Retain `(tooling)` and add `(comprehensibility/explainers)` to #288; update the ledger and derived counts.

Validation completed:

- Read #381 first and ran `git diff origin/master...HEAD`.
- All **333 origin/master rows**, plus all **334 pre-retag rows**, retain their legacy filter tags.
- Probed every requested adversarial cell, deeper nearest claims, duplicate claims, and stale areas.
- Both pages rendered with temporary HOME directories; features rendering required seeding an existing Ask-tray source.
- All **57 mutations** were killed and attributed to their named cases; controls passed before and after. The manifest sum is **2,266**.
- Inspected all **32 changed rows** and **25 unchanged open rows** against their text. The retag changes **zero closed rows**.
- No additional false-code claim found in the dated survey artifact. Repository status remains clean.

VERDICT: NOT CONVERGED
