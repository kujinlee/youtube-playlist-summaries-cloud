<!-- codex-review: model=gpt-6.1-sol -->

Reviewed `6cc2fd04`, Codex half only. Found **two MAJOR and two MINOR defects**; no BLOCKER.

1. **MAJOR — Auto-open mistakes attribute text for an `open` attribute.** `scripts/brief-compose.py:1292`  
   Reproduced under Python 3.12 and 3.14:
   ```html
   <details title=" open "><summary>S</summary>
     <p data-decision>X</p>
   </details>
   ```
   The regex matches the quoted title, so the renderer adds no `open`. Chromium reports `details.open === false` and the decision tag’s `checkVisibility() === false`, while the counter reports **1 remaining**.  
   **R1 fold caused it:** yes, in the new auto-open implementation. X1/F3 remain incompletely closed.

2. **MAJOR — Named accordion sections defeat auto-open.** `scripts/brief-compose.py:1291–1294`  
   Rendered two `<details name="group">` sections, each containing a decision, under both interpreters. The renderer adds `open` to both and reports **2 remaining**. Chromium enforces the exclusive group: open states become `[true, false]`, and tag visibility becomes `[true, false]`. One counted decision is still hidden on load.  
   **R1 fold caused it:** yes, the chosen auto-open fix does not handle named groups.

3. **MINOR — Ancestor tracking rejects valid, visible decisions after implicit paragraph closure.** `scripts/brief-compose.py:1217–1222`  
   Both interpreters refuse:
   ```html
   <p hidden>Hidden paragraph<div data-decision>Visible sibling</div>
   ```
   Chromium closes the paragraph before the div; the div’s parent is `BODY` and it is visible. The scanner retains the hidden paragraph as an ancestor and aborts composition. This is legitimate HTML with an omitted paragraph end tag.  
   **R1 fold caused it:** yes, through the new ancestor stack. No existing repository fragment triggered this refusal.

4. **MINOR — Contrast test silently ignores CSS alpha channels.** `scripts/brief-compose.py:3041–3046`  
   In memory, appended `00` to every six-digit color in `DECISION_CSS`, producing valid, fully transparent eight-digit CSS colors. **222/222 tests still passed.** Chromium resolved the open tag to foreground `rgba(58, 44, 0, 0)` and background `rgba(255, 228, 92, 0)`. `_hex_lum` reads only the first six digits, so the new readability assertion accepts invisible text.  
   **R1 fold caused it:** yes, in the added contrast test. Current committed colors are readable; this is an instrument defect.

Other disposition checks:

- **Both Python versions:** 222/222 self-tests pass. Hidden/inert/template, table-row and raw-text-element marks are refused; markup inside raw text is excluded consistently. Colliding IDs and names are refused. Whitespace-only answers remain open.
- **X3 and F4’s count/whitespace/offset fixes:** in-memory regressions to constant navigation, wrong answered count, missing `.strip()`, and disabled offset guard each fail their intended test.
- **Every real fragment:** composed all **34** recursively under `docs/explainers/` against master on both interpreters. **33 decision-free fragments are byte-identical**; only the walkthrough differs. No composition refusals.
- **F1/F2 walkthrough:** **13 total / 2 remaining / 11 answered** agrees with the relevant spec passages. The open items are corpus content review and copyright holder; Q1 and spec approval now record their answers, and Q2 reflects shipping evaluation.
- **F5 labels:** fragment labels lead the tags and navigation, are escaped, and the CSS resets inherited capitalization.
- **X2/F6 rename:** no repository links targeting old `#decision-N` anchors were found outside review history.

No files edited, commits created, or GitHub actions taken.

VERDICT: NOT CONVERGED
