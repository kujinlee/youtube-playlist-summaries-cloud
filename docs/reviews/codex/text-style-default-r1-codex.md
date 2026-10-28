<!-- codex-review: model=gpt-6.1-sol -->

1. **Major — mixed selector lists silently bypass palette checking.** `scripts/brief-compose.py:449`

   **Reproduction:** In a temporary copy of the progress-and-plan fragment, change the OS-dark selector to `:root:not([data-theme="light"]),body` and remove only that block’s `--em`. Compose succeeds. `palette_blocks()` omits the entire rule because it requires **every** selector to begin with `:root` or `html`. Chromium renders bold as `rgb(45,74,124)` against `rgb(22,21,26)`: **2.06:1**.

   **Fix:** Recognise a palette when any selector targets the root. Parse selector lists rather than splitting blindly on commas; alternatively, explicitly refuse unsupported selector forms. Add this full-compose regression.

2. **Major — structured custom-property values cause both false acceptance and false refusal.** `scripts/brief-compose.py:444`

   **Reproduction:** Replace the dark palettes’ `--em:#9db8e8;` with:

   ```css
   --tokens:{--em:#9db8e8};
   ```

   Compose succeeds: the regex counts the nested property-name text as an actual `--em` declaration. Chromium instead inherits the light `--em`, producing **2.06:1** bold contrast.

   Conversely, this valid sequence is refused despite declaring `--em`:

   ```css
   --tokens:{foo:bar};--em:#9db8e8;
   ```

   The scanner stops at the custom-property value’s closing brace. These examples require no nested CSS rules, so the documented CSS-nesting limitation does not cover them.

   **Fix:** Read balanced CSS component values and inspect only top-level declarations in each rule. Cover both acceptance and refusal counterexamples.

3. **Major — bringing an existing switcher bypasses the new refusal.** `scripts/brief-compose.py:902`

   **Reproduction:** In the progress-and-plan fragment, remove `--em` from both dark palettes, supply an `.ex-body` wrapper, and insert `page_chrome.text_style_control()` into its markup. Compose succeeds with exactly one working switcher, but OS-dark bold contrast is **2.06:1**. `want_switcher=False` skips `assert_em_in_every_palette()`.

   Thus claim (2), and the delivery documentation’s broader enforcement promise, do not hold for fragments supplying their own switcher.

   **Fix:** Enforce the palette contract whenever the finished page carries a text-style switcher, including existing-control paths, while preserving duplicate suppression.

4. **Minor — the dashboard promises contrast validation that the guard does not perform.** `docs/dashboard-entries.md:17966`

   **Reproduction:** Replace both dark `--em` declarations with:

   ```css
   --em:var(--x);--x:#16151a;
   ```

   Compose succeeds; Chromium measures bold at **1.00:1** against the page background. `--em:initial` also passes despite resolving to no custom-property value. Declaration presence establishes neither a usable colour nor contrast.

   **Fix:** Describe the guard as detecting missing declarations within its supported grammar. Retain browser contrast measurement as a separate requirement.

5. **Minor — dashboard verification status contradicts the completed evidence.** `docs/dashboard-entries.md:17969`

   **Reproduction:** The dashboard says “Browser verification is still to do”; backlog #376 records completed coordinator verification. I independently reproduced the recorded measurements on both committed pages.

   **Fix:** Update the dashboard to the completed verification status and state its measured scope.

Other checks reproduced successfully:

- **164/164** baseline cases pass; **35/35** mutations fail a case they name. `EXPECTED_MUTATIONS` and the manifest total both equal **2,340**.
- The **22 untouched pages** compose byte-identically under both composers with a fixed stamp, and their committed artifacts match `origin/master`.
- The two changed artifacts contain only the stated changes, plus their stamps.
- Both committed pages have three topmost switcher buttons, changing h2 colour, and OS-dark contrast of **9.04:1** for bold and **7.23:1** for h2.
- Custom-property chains, `html,:root`, nested `@supports`, additional media conditions, second stylesheets, comments/strings, and `!important` behaved as expected in the requested probes. No duplicate switcher was found.

VERDICT: NOT CONVERGED
