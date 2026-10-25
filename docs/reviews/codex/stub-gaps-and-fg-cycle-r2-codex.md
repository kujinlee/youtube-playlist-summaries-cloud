<!-- codex-review: model=gpt-6.1-sol -->

1. **MEDIUM — `scripts/page_chrome.py:2175`: the resize assertion cannot detect a stale reserve height.**

   The case claims “the slot reserves the bar’s measured height … after a resize,” but its resize stimulus is only `sch.b=20;rcb([])`. The bar remains 43.109375px tall.

   Reproduced this `chrome_script()` mutant entirely in memory:

   ```js
   var h=bar.getBoundingClientRect().height;
   h=parseFloat(slot.style.minHeight)||h;
   ```

   **233/233 cases pass.** It keeps the first height indefinitely while still updating the observer margin. In Chromium, resizing decision-ladder from 1280×900 to 320×568 grows the bar from **44.40625px to 130.5625px**, while the mutant leaves both reserve and `--chrome-h` at **44.4062px**. This is a measurement-wiring defect within the stated bound.

   **Fix:** change `bar.h` to a different fractional height before invoking the resize callback; assert both published values equal the new height. Add this survivor to the manifest.

Other checks passed:

- All eight new manifest entries bind exactly once and fail the case each names.
- In-memory recomposition of both fragments reproduces the committed pages except for the stamp.
- Chromium 148.0.7778.96, six states per page: no unexpected computed-style or geometry changes outside OS-light-nothing-pressed and the stamp. `--fg2` resolves throughout; minimum bold contrast is **7.79:1**.
- Backlog #350/#351’s specific closures and the dashboard’s qualified rendering claim are supported. The broader no-survivor bet is refuted by finding 1.

No repository/worktree files or Git state were changed.

VERDICT: NOT CONVERGED
