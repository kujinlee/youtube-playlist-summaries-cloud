<!-- codex-review: model=gpt-6.1-sol -->

Both clauses of the bet are refuted. All reproductions used temporary copies and headless Chromium; the repository remains unchanged.

1. **Major — block-local aliases do not establish the effective palette.** `scripts/brief-compose.py:627`, `scripts/brief-compose.py:723`

   Append this inside the progress-and-plan fragment’s first stylesheet:
   ```css
   :root{--bg:#fff;--em:var(--x);--x:#123}
   :root{--x:#fff}
   ```
   Compose **accepts**. In OS-light with nothing pressed, Chromium resolves `--em` to white on white: **1.00:1**. Every palette token is in a canonical block, and its locally resolved pair passes. The later alias declaration nevertheless changes the browser’s result.

   This variant also passes and renders **1.00:1**:
   ```css
   :root{
     --bg:#fff;--em:var(--x);
     --x:#fff!important;--x:#123;
   }
   ```
   The reader discards the alias’s importance by taking the last dictionary value.

   **Fix:** Make aliases part of the enforced format, including their overrides and importance, or require palette tokens to contain literal hex values. Local resolution cannot justify the claimed exact per-state result.

2. **Major — the state model places the shim after stylesheets that actually follow it, falsely refusing canonical input.** `scripts/brief-compose.py:727`, `scripts/brief-compose.py:1259`

   Append a second stylesheet after the fragment’s existing content:
   ```html
   <style>
   :root[data-theme="dark"]{--bg:#fff;--em:#123}
   </style>
   ```
   Compose **refuses**, predicting the shim’s `#9db8e8` on white at **2.01:1**.

   With only the guard bypassed in the temporary harness, Chromium measures **16.15:1** in both explicit-dark states. All six OS-scheme × pressed-theme states pass. The second stylesheet follows the shim in the generated document and wins equal specificity.

   **Fix:** Preserve actual stylesheet order in the state calculation, or place the shim after all fragment stylesheets. This directly refutes clause (2).

3. **Major — case-sensitive background matching admits a forbidden page ground.** `scripts/brief-compose.py:583`

   Append inside the first stylesheet:
   ```css
   BODY{background:#9db8e8}
   ```
   Compose **accepts**. Chromium treats `BODY` as the HTML body selector and measures **1.00:1** in OS-dark and explicit dark; light states measure **4.39:1**.

   **Fix:** Normalize HTML selector and ordinary property-name casing before enforcing the background restriction. The promised format refusal currently misses this ordinary spelling.

4. **Major — accepted bold overrides still defeat the recorded rendered-contrast bet.** `scripts/brief-compose.py:1305`, `docs/reviews/decision-scheme/decision-log.jsonl:98`

   Append:
   ```css
   .ex-body strong{color:var(--bg)!important}
   ```
   Compose **accepts**. Chromium measures bold at **1.00:1 in all six states**.

   The same override inside `@media(prefers-contrast:more)` passes and measures **1.00:1** with that preference enabled. A forced-colours attack preserving the authored bold colour with `forced-color-adjust:none` produces **2.01:1** in OS-light/explicit-dark and **2.38:1** in OS-dark/explicit-light.

   **Fix:** Align the decision-log bet with the intended token-format guarantee, retaining browser verification for rendered contrast, or enforce rendered contrast before acceptance. The disclaimer does not satisfy the bet as written.

Executed verification:

- **193/193** HEAD self-tests pass.
- HEAD contains **26 tracked fragments**, rather than 25; **all 26 compose, zero refused**.
- The **15 changed behavioral cases are red on `f88f10d0`**. The selector-shape assertion also fails against its old return structure. A temporary adapter accepted the new `themed` argument so the old checker could complete the suite.
- **49/49 mutations killed and attributed to their named cases; zero survivors.**
- Independently summed manifests and `EXPECTED_MUTATIONS` agree, including every per-file count: **2354**.
- Comments within canonical blocks, repeated complete blocks, repeated blocks across stylesheets, uppercase hex and three-digit hex pass. A chain requiring an undeclared-in-block alias is refused.
- The shim’s palette rules are read from `SHIM`. Unthemed pages skip pressed-state checks; no additional reachable theme state was identified in the real fragments. `color-scheme:dark` alone introduced no failure.
- The #376 row, explainer-delivery §2 and dashboard disclaim rendered readability, but their background-enforcement and exact per-state claims remain unsupported by findings 1–3. The decision-log bet retains the broader claim defeated by finding 4.

VERDICT: NOT CONVERGED
