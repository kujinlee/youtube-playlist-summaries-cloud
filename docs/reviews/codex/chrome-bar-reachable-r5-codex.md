<!-- codex-review: model=gpt-6.1-sol -->


**REVIEW GAP:** claude — not invoked for round 5. `docs/plugins.md` says round 1 runs both halves CONCURRENTLY and rounds 2+ ALTERNATE, because a concurrent pair never reviews the FIXES. Round 1 ran both; rounds 2, 3 and 5 are the Codex side of that alternation and round 4 was the Claude side. This is a single-reviewer round BY CONSTRUCTION, and saying so is the point of this line.

No Blocking findings.

- **High — `scripts/page_chrome.py:236`: nested `<noscript>` hides a live control from every guard.** `<noscript><noscript></noscript><button id="chrome-theme">Theme</button>` leaves the scanner’s shield raised. **Verified:** `assert_wired()` accepted this without palettes or a handler; Chromium found one visible theme button. Moving `has_control()` onto this scan introduced a fail-open.

- **High — `scripts/page_chrome.py:273`: an unterminated script satisfies binding without executing.** Ending an otherwise complete page with `<script>` plus `chrome_script()`, without `</script>`, now contributes the handler marker. **Verified:** `assert_wired()` passed; Chromium clicks left `data-theme` unchanged and the bar computed `position:static`.

- **Medium — `scripts/page_chrome.py:233`: the noscript fix reintroduces last-wins duplicate attributes.** `<noscript id="chrome-theme" id="other"></noscript>` before the real button escapes duplicate detection because this branch uses `dict(attrs)`. **Verified:** the guard passed; Chromium returned the NOSCRIPT from `getElementById()`, and clicking the visible button did nothing. Reversing the attributes falsely refuses a working page. The template branch at line 243 has the same mistake.

- **Medium — `scripts/page_chrome.py:248`: foreign-content controls are incorrectly shielded.** In `<svg><template><g id="chrome-theme"></g></template></svg>`, Chromium treats the template as an SVG element and its child remains live. **Verified:** prepending this to a wired page passed duplicate detection; Chromium bound the SVG `g`, leaving the visible theme button inert.

- **Medium — `scripts/page_chrome.py:233`: shielded template/noscript elements still contribute their own IDs.** Their branches run before the enclosing shield check. **Verified:** adding `<template><noscript id="chrome-theme"></noscript></template>` falsely produced a duplicate-ID refusal. Chromium found only the real button, whose click successfully changed the theme.

- **Medium — `scripts/page_chrome.py:215`: fictitious scripts inside noscript hide subsequent real handlers.** `<noscript><script></noscript><script>…real handler…</script>` puts the scanner into script mode before it sees the real noscript terminator. **Verified:** the guard refused a complete wired page for lacking its handler; Chromium executed that handler and theme switching worked.

- **Medium — `scripts/page_chrome.py:166`: the expanded pin regex accepts unrelated rules.** `/* .chrome-pinned */ .nonexistent{position:fixed}` satisfies the predicate despite containing no pinning rule for the bar. **Verified:** a finished page carrying only this chrome CSS passed `assert_wired()`; Chromium computed the bar’s position as `static`.

- **Low — `scripts/page_chrome.py:1359`: a sixth mutation pair masks its named case.** Combining “the pin selector must touch the brace again” with “the reachability predicate never fires” makes the grouped-selector case pass. **Verified:** the regex mutation alone failed that case; the combined mutant did not. Six other cases still killed the combination. This falls within the documented pair-coverage exclusion.

Verification: **155/155** page-chrome cases and **137/137** composer cases passed. All **62 relevant individual mutations** were killed by their exact named cases using the official `check-plan-code.py --mutate . --shard …` CLI. The unsharded repository-wide run was started and stopped incomplete.

**NOT RUN:** exhaustive revalidation of every prior finding, exhaustive parser or mutation-pair sweeps, real-device testing, physical printing.
