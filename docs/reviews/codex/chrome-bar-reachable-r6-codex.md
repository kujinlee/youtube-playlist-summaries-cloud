<!-- codex-review: model=gpt-6.1-sol -->

1. **High — IN scope: existing text-style controls remain unreachable after scrolling.** `scripts/page_chrome.py:802` searches only inside the slotted `.chrome`; `scripts/brief-compose.py:823` preserves hand-authored switchers outside it.

   Failing inputs: the real October 5, October 6, and October 15 fragments, composed unchanged. In Chromium at 1280×900 after scrolling to 1800 and waiting 1600ms, their `#schemer` positions were respectively **−1262, −1459, and −1104px**, all `position:static`. October 5 had no pinned bar; the other two pinned the theme bar while leaving the text-style control behind. The predicate misses controls already present in the declared subject.

2. **Medium — IN scope: a fully invisible button can remain unpinned indefinitely.** `scripts/page_chrome.py:833` waits for the entire slot to stop intersecting, including its padding.

   Failing input: the unchanged October 6 fragment, composed at 320×568, then scrolled to 231px. After 1600ms, the theme button occupied **y=−31.02 to −1.39**, entirely outside the viewport. The slot still extended to **y=5.80**, so the bar remained unpinned. This is a stable threshold defect, independent of callback latency.

3. **Medium — OUT under the explicit exclusion; the bound is wrong for ordinary CSS comments.** `scripts/page_chrome.py:49` excludes a `.chrome-pinned` mention inside a CSS comment; `scripts/page_chrome.py:410` nevertheless accepts it as the pinning mechanism.

   Concrete input: a finished document containing `chrome_bar()`, both palettes, `chrome_script()`, and only this purported pin rule:

   ```css
   /* .chrome-pinned */ .nonexistent { position:fixed }
   ```

   `assert_wired` accepts it. A fragment author commenting out a selector while editing CSS is a plausible mistake within this guard’s stated purpose. Unlike nested malformed shields, this exclusion removes ordinary authored CSS from protection. Recording the false acceptance witnesses the exclusion; it does not justify it.

Verification and remaining limits:

- Self-tests reproduced **178/178**, **143/143**, and **178/178**.
- The shipped `run_mutations` runner, with its exact-name attribution, reproduced **80 killed, 80 attributed, zero survivors**, with green controls before and after.
- All five temporary scanner tightenings reddened their corresponding recording cases. None proved decorative under those experiments.
- Inspection of all 20 fragments found one explicit title pair apiece and no `<noscript>` or `<template>` shapes. I found no additional concrete title-placement failure.
- I found no remaining dependency on `body.chrome-pinned-host`, duplicate control introduced by the exercised compositions, or contradictory print reservation rule. Physical printing was not tested.
- The tested pinned resize and return did not produce a feedback loop. Font-load, late-image, zoom, real-device, runtime-injection, and no-IntersectionObserver behavior remain unverified.
- The five recordings honestly assert scanner behavior rather than browser behavior. No browser comparison of those five shapes was run here.
- The scheme-CSS presence arm remains near-vacuous on producer paths, as its existing comment acknowledges.
- The 250–500ms failures disappearing later do **not establish** observer-callback latency as the cause. That explanation needs callback and scroll instrumentation. Finding 2 persists beyond that delay.

**NOT CONVERGED — real fragment controls still scroll away, and the observer threshold permits a completely hidden theme button.**
