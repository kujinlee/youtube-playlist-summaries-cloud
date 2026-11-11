<!-- codex-review: model=gpt-6.1-sol -->

The bet is refuted in both directions: accepted fragments render bold at **1.00:1**, and a fragment within the declared grammar is falsely refused. All execution used temporary copies; repository files were unchanged.

1. **Major — `!important` is discarded, causing both false acceptance and false refusal.** `scripts/brief-compose.py:503`, `scripts/brief-compose.py:584`

   **Reproduction:** In a temporary copy of the progress-and-plan fragment, append:
   ```css
   :root[data-theme="dark"]{
     --em:#16151a!important;
     --em:#9db8e8;
   }
   ```
   Compose succeeds. Headless Chromium with `data-theme="dark"` computes bold and body background as `rgb(22,21,26)`: **1.00:1**. Splitting the declarations between two identical selector blocks produces the same result.

   Reverse the values:
   ```css
   :root[data-theme="dark"]{
     --em:#9db8e8!important;
     --em:#16151a;
   }
   ```
   Compose refuses it as **1.00:1**. Rendering the same fragment with only the guard bypassed in the temporary harness measures **9.04:1**. This directly refutes the no-false-refusal clause.

   **Fix:** Preserve declaration importance and apply CSS precedence both within rules and when merging rules. Add regressions for both declaration orders and split blocks.

2. **Major — attribute whitespace bypasses the promised closed grammar.** `scripts/brief-compose.py:595`

   **Reproduction:** Add a second stylesheet to the same fragment:
   ```html
   <style>
   :root[ data-theme = "dark" ]{
     --bg:#16151a;
     --em:#16151a;
   }
   </style>
   ```
   Compose succeeds. Chromium in explicit dark theme measures **1.00:1**. The same attack succeeds with a fragment-supplied switcher and `.ex-body`.

   `ROOT_FORM` rejects this selector, but the fallback treats any whitespace as evidence of a descendant selector—even whitespace inside an attribute selector—and silently skips it. The single-quoted form without spaces is refused correctly.

   **Fix:** Distinguish selector combinators from whitespace inside brackets and strings. Refuse unsupported root compounds explicitly. The claims in `docs/backlog.md:358`, `.agents/skills/shared/explainer-delivery.md:129`, and `docs/dashboard-entries.md:17983` that other grounded root forms are refused are currently false.

3. **Major — a supported root override without its own `--bg` escapes validation.** `scripts/brief-compose.py:608`

   **Reproduction:** Add this second stylesheet:
   ```html
   <style>
   @supports (display:grid){
     :root[data-theme="dark"]{--em:#16151a}
   }
   </style>
   ```
   Compose succeeds. Chromium in explicit dark theme computes bold and body background as `rgb(22,21,26)`: **1.00:1**.

   This uses supported selectors and supported nesting. The override is collected under a different context, then discarded because that group declares no `--bg`. Its `--em` nevertheless wins in the browser.

   **Fix:** Validate effective root token combinations across applicable contexts, or refuse overrides whose inherited ground cannot be verified. Checking only groups that independently declare `--bg` cannot establish the bet.

4. **Major — the actual page background can invalidate every successful palette check.** `scripts/brief-compose.py:687`

   **Reproduction:** Append:
   ```css
   body{background:#9db8e8}
   ```
   Compose succeeds. Chromium measures **1.00:1** in OS-dark and explicit dark, and **4.39:1** in explicit light.

   **Fix:** Either verify the rendered bold surface, or enforce a supported page-background contract. The function docstring acknowledges its block-ground limitation, but the decision-log bet promises readable rendered bold without that qualification. The narrower prose does not establish the broader bet.

Executed checks:

- **181/181** HEAD self-tests pass.
- Against `aaf6fe67` production code, the **14 behavioral regression cases are red**. An additional case fails because the old palette reader returns sets rather than value dictionaries; positive controls, including the existing var-chain behavior, remain green.
- **49/49 mutations killed and attributed to their named cases**, zero survivors.
- `EXPECTED_MUTATIONS` and the independently summed manifests both equal **2354**.
- Both composers accept all **24 fragments**, zero refusals. The **22 untouched fragments** compose identically; both changed pages match their committed artifacts after masking timestamps. Across all 24, the exact cross-composer equality count is **23**, since the skills page also composes identically.
- Nested `@supports` plus combined dark-media features, merged-block `--bg` var chains, and three-digit hex compose successfully. Eight-digit alpha hex, `rgb()`, `hsl()`, named colours, and `currentColor` are refused as unverifiable.
- The round-1 behavioral repros are covered by the passing HEAD cases, including the own-switcher refusal. Those fixes do not close the counterexamples above.

VERDICT: NOT CONVERGED
