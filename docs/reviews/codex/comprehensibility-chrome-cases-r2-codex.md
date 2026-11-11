<!-- codex-review: model=gpt-6.1-sol -->

1. **High — `scripts/page_chrome.py:315`: unrelated exclusion admits an inert light control.**

   `_light_by_exclusion` checks that an exclusion exists somewhere, without checking whether the dark palette actually excludes light. I composed a fragment with complete default tokens and:
   ```css
   @media(prefers-color-scheme:dark){
     :root{--bg:#111;--ink:#eee}
     :root:not([data-theme="light"]){--unused:2}
   }
   :root[data-theme="dark"]{--bg:#111;--ink:#eee}
   ```
   Actual output:
   ```text
   compose=ACCEPT missing=[]
   before: theme=null,    bg=rgb(17,17,17), ink=rgb(238,238,238)
   after:  theme="light", bg=rgb(17,17,17), ink=rgb(238,238,238)
   errors=[]
   ```
   Chromium used OS-dark and the actual button. This reopens the documented fail-silent through `brief-compose`, despite passing token completeness.

   **Fix:** validate a bounded exclusion pattern tying the relevant dark declarations to the exclusion; refuse competing unconditional dark rules. Add this accepted-but-inert page as a regression fixture. Correct the “both halves” sufficiency claim in backlog #300 and the coordinator record.

2. **Medium — `scripts/page_chrome.py:2228`: resize callback faults still pass every case.**

   The stub records the resize target but discards its callback. On a temporary copy, replacing:
   ```js
   new ResizeObserver(sync).observe(bar);
   ```
   with:
   ```js
   new ResizeObserver(function(){
     throw new Error('resize-dead');
   }).observe(bar);
   ```
   produced:
   ```text
   233/233 passed
   ```
   Chromium executing the mutated emitted script reported:
   ```text
   errors=["resize-dead"]
   ```
   Resizing can no longer refresh the reserve or threshold. This is an execution gap, independent of real layout. Backlog #305’s closure and `docs/dashboard-entries.md:17437` (“A crash fails the tests”) overstate coverage.

   **Fix:** retain and invoke the resize callback, change fixture dimensions, and assert updated measurements. Add the surviving mutation and qualify the records.

3. **Medium — `scripts/page_chrome.py:280`: valid CSS syntax makes the scanner remove working controls.**

   Prepending either of these to an otherwise complete, working exclusion palette:
   ```css
   @layer base;
   ```
   ```css
   [data-x="{"]{--unused:0}
   ```
   produced:
   ```text
   missing=['light']
   compose=ACCEPT control=False
   ```
   The semicolon at-rule becomes part of the following selector; the quoted brace incorrectly increments depth. Chromium with the original control confirmed both pages work:
   ```text
   before: bg=rgb(17,17,17),   ink=rgb(238,238,238)
   after:  bg=rgb(255,255,255), ink=rgb(17,17,17)
   errors=[]
   ```
   Thus routine stylesheet edits reproduce the working-control removal the fold intended to fix.

   **Fix:** handle quoted selector strings and semicolon-terminated at-rules before counting structural braces. Add both fixtures.

Verification: unchanged suites passed **233/233** and **215/215**. The partial-palette examples remained refused by `brief-compose`. Across all six September pages, sampled old/new text and computed colors, fonts, and display properties outside chrome/tray matched with light selected under both OS themes. No worktree files were written; git status remained clean.

VERDICT: NOT CONVERGED
