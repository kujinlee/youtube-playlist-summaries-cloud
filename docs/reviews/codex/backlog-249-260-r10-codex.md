<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established.

## High

1. **The third dependency install breaks `mutation-sweep-complete`.** `.github/workflows/ci.yml:811` installs from `requirements.txt`, but this job has **no checkout step**. Jobs use separate runners; another job’s checkout cannot supply this file. Even with every mutation shard green, the completion job will fail opening `requirements.txt`. Remove this unnecessary install from the job, or provide a checkout.

2. **Parser absence can report success.** Availability is checked only when a candidate backtick pair reaches `inline_block_spans`, not when `main()` starts.

   Reproductions:
   - Prepared venv interpreter with `-S`, running `--base HEAD --strict`: **rc=0**, “nothing to withdraw,” despite no `markdown_it`.
   - With `_MD=None`, a fixture correcting `1,414` to `1,416` while another document contains `the count was 1,414 anchors today`: **rc=0**, one correction examined, remaining hit suppressed as history.

   Check availability before success paths. Also catch `ParserUnavailable`: the current self-test without dependencies produces an uncaught traceback and **rc=1**, contradicting the class docstring’s promised `main()` conversion to rc=2.

3. **`gfm-like` introduces lenient regressions against cmark-gfm.** These two documents produce marker `''` under `0792dcab`, but `'was '` under HEAD:

   ```text
   > the count was `wrong:
   <span>
   holds 1,414 anchors today`
   ```

   ```text
   the count was `wrong:
       | h |
   | --- |
       holds 1,414 anchors today`
   ```

   With the pinned **markdown-it-py 4.2.0**, each becomes one inline block covering the complete document, so HEAD pairs the backticks and masks the paragraph boundary. **cmark-gfm splits both**: the first closes the quote before an HTML block; the second creates a table and then indented code. Neither contains an inline code span. The old boundary answer was right here. Calling the selected preset GFM does not establish fidelity to GitHub’s parser.

4. **Line ranges do not preserve table-cell boundaries.** `inline_block_spans` at `scripts/check-withdrawal.py:613–616` converts each inline token’s line map into a character range. Separate cells on one row therefore receive identical ranges.

   ```text
   | the count was `wrong. | holds 1,414 anchors today` |
   | --- | --- |
   ```

   Both parsers report **two separate cells and no inline code**. HEAD records two identical spans, pairs the backticks across cells, masks the whitespace after `wrong.`, and reports marker `'was '`. With that whitespace preserved, the figure’s sentence has no history marker.

   This defect also existed before the swap; the new implementation retains it while claiming that separate inline blocks cannot pair. Token identity and cell boundaries must survive the conversion.

## Medium

1. **Python’s `splitlines()` disagrees with the parser’s line numbering.** At `scripts/check-withdrawal.py:607`, VT, FF, NEL, U+2028 and U+2029 are counted as line breaks even though markdown-it treats them as inline content.

   For `pad\x0bthe count was ` followed by `` `v1. 2` and 1,414 today ``, HEAD records range `(0, 4)` and misses the genuine code span. The old marker is `'was '`; HEAD’s is `''`. Both cmark-gfm and markdown-it recognize `v1. 2` as inline code. All five separators reproduced this false-survivor regression. Build offsets using the parser’s newline rules.

2. **The new memo outlives its declared run scope.** `_BLOCK_SPANS` is never cleared; `main()` clears only `_MASKED_DOCS`. The current corpus retained **1,791 keys containing 30,807,795 UTF-8 bytes of source**, plus span structures. After adding 100 distinct documents and calling `main()`, all cache entries remained.

   Value keys are correct for identity, but repeated calls over changing documents retain every previous version indefinitely. Give this cache a run lifecycle or a bounded eviction policy.

3. **The supplied corpus replay cannot reproduce its positive control.** `final_check.py` loads the current guard as `SHIP`, so at this HEAD both control columns agree instead of differing. It exits **rc=1**, asserting “control detected 0, want 2,” before examining the corpus.

   An independent comparison loading `0792dcab` explicitly passed the positive controls and found zero differences. However, the exact **95,786** population was not reproducible from either committed tree: baseline contains **95,778** matching figures; HEAD contains **95,797**. Freeze the replay’s source versions and document population.

## Low

- **A current stdlib-only assertion remains.** `scripts/check-merge-ready.py:133` still says “the project is stdlib-only, so `yaml` is unavailable.” The repository-wide premise is now false. The narrower statement that PyYAML is not installed remains supportable.
- `mask_inline_code`’s docstring still describes fenced-code masking as deferred and carried, although this commit deliberately closes that deviation.

## Checked and found SOUND

- Withdrawal self-test: **172/172**.
- Plan-code self-test: **237/237**.
- Binding, Python-pin and documentation checks: **passed**.
- Manifest retirement: **56 → 30**, exactly **26 removed**; every retired entry has at least one anchor absent from HEAD.
- All **30 remaining mutations** changed source, exited nonzero, and failed their expected case by **exact name equality**. No no-op or attribution failure found. Declared total: **1,529**.
- Both deliberately moved cases agree with **cmark-gfm directly**: the leading-tab document is indented code; the fenced example contains literal single backticks. Neither has inline code spans.
- Independent corpus comparison: **zero verdict differences** on both committed populations, after successful positive controls.
- `verify` and `mutation-sweep` install dependencies before withdrawal execution. `schema-gates.yml` does not execute or import this parser-dependent guard; its omitted install is appropriate.
- Value-based memo keys avoid the identified `id(text)` reuse defect.
- The #153 supersede is recorded where its decision is stated, and `requirements.txt` records the interpreter coupling. The structural-reader versus removed boundary-machinery distinction is supported.

## CANNOT RUN

**The supplied `final_check.py` replay failed its positive control. Treat that replay as NOT RUN.** Its failure does not count as corpus evidence; the independent comparisons above completed successfully.

## Instruments

Prepared Python 3.12 venv; pinned markdown-it-py **4.2.0**; direct cmark-gfm rendering; baseline source loaded from `git show`; frozen baseline documents from `git archive`; per-entry mutation execution with exact failure-name attribution; parser-absence and cache-lifecycle probes.

Reviewed **d8c02e22**. No review file or repository changes created. **Convergence remains 0 of 2** because High findings remain.
