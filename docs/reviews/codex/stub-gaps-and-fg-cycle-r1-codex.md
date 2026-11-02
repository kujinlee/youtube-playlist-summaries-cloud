<!-- codex-review: model=gpt-6.1-sol -->

1. **MEDIUM — `scripts/page_chrome.py:2179`: default-press button state remains unobserved.**

   The report checks only the attribute and storage: `"REP.back=[root.getAttribute('data-scheme'),'explainer-scheme' in ST]"`.

   Reproduced a `chrome_script()` mutant by inserting immediately after the `bs` lookup:

   ```js
   if(s===TD&&bs[0].className==='on')return;
   ```

   **233/233 cases still pass.** After plain → default, the attribute and stored key disappear, but plain remains `class="on" aria-pressed="true"` and default remains unpressed. This is control wiring within the stub’s stated bound.

   **Fix:** report and assert all three buttons’ classes and `aria-pressed` values after the default press; add this survivor to the manifest.

2. **LOW — `docs/explainers/2026-10-23-topic-decision-ladder.html:237`, `docs/explainers/2026-10-20-topic-why-not-converging.html:236`; overstated at `docs/dashboard-entries.md:17470–17478`.**

   The claims “nothing else on those pages changed” and “only OS-light-nothing-pressed changes” are false for the committed pages. Recomposition changed the generated timestamp, changing `.chrome-when` width and its position in **every state**.

   At 1280×900, decision-ladder’s timestamp container grows **391.609375 → 398.3125px**; why-not-converging’s grows **397.15625 → 398.3125px**. Chromium detects differences on `.chrome-when` and its `<time>` element in all five states where no change was allowed.

   **Fix:** preserve the original stamps for this palette-only change, or explicitly disclose the stamp changes and qualify the differential claim.

Chromium **148.0.7778.96**, comparing every element’s computed standard properties and bounding box against committed `origin/master`, found:

| State | Both pages |
|---|---|
| OS light, nothing pressed | Expected palette correction, plus timestamp differences |
| OS light, light pressed | Timestamp differences only |
| OS light, dark pressed | Timestamp differences only |
| OS dark, nothing pressed | Timestamp differences only |
| OS dark, light pressed | Timestamp differences only |
| OS dark, dark pressed | Timestamp differences only |

The literal values match each block’s original palette. `--fg`, `--fg2`, and `--fg3` resolve in all six states on both revised pages; the cycle is gone.

Backlog #350’s **specific closure is supported**: each new manifest edit binds exactly once, and each fails the named new case. Its report shows independently corrupted reserve values and the retained storage key. The default press follows a confirmed stored opt-out, so removal does not pass merely because storage started empty. The closure does not establish complete coverage of default-button behavior, as finding 1 demonstrates.

No worktree files or Git state were changed.

VERDICT: NOT CONVERGED
