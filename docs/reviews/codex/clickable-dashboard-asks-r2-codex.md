<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Medium** - `choose` can click a stale selection floater and open the tray with the wrong quote.  
In committed `HEAD`, `fire()` selects the option text and dispatches `mouseup` at `scripts/gen-dashboard.py:587-596`, then the click handler immediately enters `poll()` and clicks the first `button.askbtn[style*="fixed"]` it finds at `scripts/gen-dashboard.py:613-617`. The tray, however, removes any previous floater only inside its own delayed `mouseup` callback: generated `/tmp/review-dashboard-r2-head.html:6928-6931`, then creates the new one at `/tmp/review-dashboard-r2-head.html:6936-6948`. So the first synchronous poll runs before stale removal. I verified this in Playwright on the committed generated artifact: pre-create a selection floater, click the first `.needs .pick`, and the tray opened on `What changed — "You tried to answer..."` instead of the chosen option. This is worse than a missed click because the tray is live but carries the previous selection context.

**Low** - The new local-mode hiding regression test is too narrow to protect the repaired behavior.  
The case at `scripts/gen-dashboard.py:1806-1807` only rejects the exact substring `".pick{display:none"` after removing spaces. It would not catch hiding via an ancestor, `visibility:hidden`, `opacity:0`, media-scoped rules, or other valid CSS spellings that leave that exact substring absent. The adjacent wiring assertion at `scripts/gen-dashboard.py:1802-1803` is similarly incidental: `"closest('.pick')"` proves that one implementation string exists, not that clicking a chooser opens the tray with the selected option. Given this branch already regressed via a vacuous page-wide substring assertion, this repair still needs a behavior-shaped test.

**Notes**

No finding on deleting the `file:` early return by itself: the no-stale `file://` path did open the tray with the option as context, and the lifted tray relabels Send to Copy at `/tmp/review-dashboard-r2-head.html:6852-6868`. In headless Chromium, the clipboard write from `file://` rejected and showed the tray’s error note rather than silently succeeding; I did not count that as the r1 repair’s entry-point bug, but it means “local file copies instead” is not fully proven by the current self-test.

Verification: `python3 scripts/gen-dashboard.py --self-test` passed 324/324 in clean `HEAD`. `python3 scripts/check-plan-code.py --self-test` passed 128/128 in the original checkout; in a detached clean worktree it failed 125/128 only because ignored `node_modules/typescript` was absent.

CONVERGED: no Blocking or High findings.
