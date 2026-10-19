<!-- codex-review: model=gpt-6.1-sol -->

**Choose C: retain bounded wiring checks in text; assert reachability and operation in a browser test in CI.** The coordinator identifies a real verification gap, but overstates its causal explanation. Neither module separation nor browser testing would eliminate every finding driving this branch’s review loop.

**High · structural — the automated suite observes the mechanism without observing its execution.**

`bar_unreachable` explicitly checks for a pinning declaration rather than reachability (`scripts/page_chrome.py:591–602`). The implementation’s own boundary is honest; the missing piece is a repeatable assertion of the reader’s property.

I ran a controlled Chromium experiment using the current `chrome_css`, `chrome_bar`, and `chrome_script`:

| Artifact | `assert_wired` | At 320×568, scrollY=2000 |
|---|---|---|
| Unmodified generated fixture | Accepted | Theme button y=8.19–32.56; pinned |
| Same fixture, with a runtime `throw` before the unchanged script | Accepted | Theme button y=−1926.38–−1902; unpinned; page error |

This is a synthetic fault injection, **not a current production defect**. It demonstrates the observation gap directly: preserving the text and JavaScript syntax preserves the guard’s approval while destroying the behavior.

The browser assertion must require positive operation: controls are reachable, clicks change the intended state and rendering, and no startup error occurs. “Zero class flips” alone cannot distinguish stability from dead JavaScript.

The coordinator’s six leads resolve as follows:

| Lead | Verdict |
|---|---|
| **Seven consecutive fix-created-finding rounds** | **Not confirmed as stated.** The inclusive range r2–r8 contains seven rounds, but r8 explicitly declines to establish an eighth causal sequence and calls its remaining growth loop pre-existing (`docs/reviews/claude/chrome-bar-reachable-r8-claude.md:21`, `:172`). The inventories establish repeated thrashing; their mixed counting units do not independently prove seven consecutive rounds of one causal mechanism. |
| **Six instruments, each failing differently** | **Partly confirmed; taxonomy misleading.** Substrings, regexes, comment handling, HTML scanning, caller facts, and exact-expression assertions all appear. But caller facts are not failed browser emulation: r4’s Blocking was a fact derived from the wrong CSS parameter (`docs/reviews/claude/chrome-bar-reachable-r4-claude.md:10`). That is integration wiring, not another failed parser generation. |
| **Missing brace, 201 green cases, inert controls, zero flips** | **Core event recorded; tally wrong.** The current code records **190/190**, invalid JavaScript, and misleading zero flips (`scripts/page_chrome.py:2069–2077`). Commit `2ee4371c` records the same. **201/201** instead belongs to r7’s undetected removal of theme persistence (`docs/reviews/codex/chrome-bar-reachable-r7-codex.md:83`). The transient broken-brace artifact was **NOT RUN** here; I did not recover an exact committed version of it. |
| **Every real defect in r6–r8 found and fixed in a browser** | **Refuted.** Browser measurements found important runtime defects. They did not establish r6’s lexically unfalsifiable cases (`docs/reviews/claude/chrome-bar-reachable-r6-claude.md:239`), r7’s ambient substring suppliers (`docs/reviews/codex/chrome-bar-reachable-r7-codex.md:83`), or r8’s deleted mutation entry (`docs/reviews/claude/chrome-bar-reachable-r8-claude.md:39`). These are real verification defects established through severance or manifest comparison. |
| **Playwright exists; mutation harness is browserless** | **Dependency/staging claim confirmed, absolute claim too strong.** Playwright is declared (`package.json:36`, `:44`), and Chromium launched successfully here. `HARNESS_TREE` stages TypeScript but no Playwright package (`scripts/check-plan-code.py:199–214`). However, suites inherit an environment and invoke subprocesses (`scripts/check-plan-code.py:557–570`); the tuple alone does not prove browsers are structurally impossible. It proves the harness does not provision a portable browser dependency. |
| **Each fold re-reddens the gate; procedure cannot terminate** | **Conditional behavior confirmed; impossibility refuted.** `round_tail` compares guarded tree entries, including reviewed dirty state (`scripts/check-review-recorded.py:889–912`). A changed entry not seen by a usable round invalidates that evidence. But an unchanged final tree can pass, reviewed uncommitted changes can pass, and explicit waiver paths exist (`:915–967`). Repeated failure to converge is evidence about this run, not proof that the procedure has no fixed point. |

There is enough evidence for the Phase 6 trigger without inflating these claims. The process requires two consecutive fix-generated rounds, not seven (`docs/dev-process.md:93`).

**F1 — producer and checker coexist: confirmed. Causal architectural violation: unsupported.**

The producer functions and checker entry point are present in the same module (`scripts/page_chrome.py:831`, `:968`, `:1302`, `:1335`). But `CONTEXT.md:109` defines **the renderer** specifically as `page_markup.py`; “a renderer checks nothing” describes that component’s role. It does not establish a universal ban on libraries validating their output.

More importantly, **I cannot name a historical finding that merely moving the checker into another file would have prevented**:

- r3’s whitespace-sensitive consumer signature remains whitespace-sensitive after a file move (`docs/reviews/codex/chrome-bar-reachable-r3-codex.md:6`).
- r6’s unguarded re-arm remains unguarded (`docs/reviews/claude/chrome-bar-reachable-r6-claude.md:25`).
- r7’s wrong selected bar remains wrong (`docs/reviews/claude/chrome-bar-reachable-r7-claude.md:21`).
- r8’s deleted mutation remains deleted (`docs/reviews/claude/chrome-bar-reachable-r8-claude.md:39`).

The causal problem is **what the assertion observes**, not where its function lives. File separation could clarify responsibilities, but is not demonstrated prevention.

The “anchors bind by TEXT” analogy is useful for exact-expression assertions, yet incomplete. Mutation anchors select edits; assertions decide outcomes. Their shared sensitivity does not make their failure modes identical.

**Medium · structural — accepted behavioral bounds live in code and review history rather than the governing design vocabulary.**

F2’s counts reproduce exactly, using case-insensitive substring searches:

| Search | Hits |
|---|---:|
| `chrome` | 0 |
| `page_chrome` | 0 |
| `Playwright` | 0 |
| `browser` | 0 |
| `self-test` | 0 |
| `reachab` | 2 |

The two reachability mentions concern blob addresses and YAML lines (`CONTEXT.md:62`, `:133`). The Verification Stack introduction does record the earlier seven-round vocabulary failure (`CONTEXT.md:121`).

**The numerical analogy proves nothing causal.** Missing the word “Playwright” is not itself an architectural defect. The substantive omission is that a reader cannot find the distinction between wiring, pinning mechanism, and rendered reachability—or their accepted limits—in the governing vocabulary.

What this branch decided without recording it there includes:

- **D has already been adopted:** assertions cover repository generators and skill-authored fragments, excluding enumerated parser shapes (`scripts/page_chrome.py:29–70`).
- Controls use **one bar**, under the title in flow and pinned after scrolling; the slot preserves its space (`scripts/page_chrome.py:315–338`).
- An existing fragment switcher is moved into the bar at runtime (`scripts/page_chrome.py:2110–2123`).
- Resize while pinned deliberately retains the last in-flow measurements; a measured one-pixel overlap is accepted (`scripts/page_chrome.py:1197–1218`).
- Text styling is opt-in for prose, rather than enabled across the tabular producers (`scripts/page_chrome.py:1302–1317`).
- Composer output depends partly on the externally selected Ask-tray source, so identical fragment and commit do not necessarily reproduce identical pixel measurements (`scripts/page_chrome.py:1183–1196`).

These are discoverable in code, but that is precisely ADR-0014’s propagation warning: a decision buried in one file reaches only readers of that file (`docs/adr/0014-a-guards-main-is-drivable.md:35–42`). Record the contract in an anchored design document under ADR-0010’s existing rule; do not reopen either ADR.

**Medium · transitional — the coordinator’s evidence conflates distinct failures.**

The incorrect 201 tally and universal browser-discovery claim materially strengthen the proposed remedy beyond its evidence. Correct them before using this inventory as a decision record. Browser tests address execution and layout; they do not repair mutation-set accounting or prove review termination.

My proposed C has a deliberately bounded cost:

- Generate the five real producer outputs and representative composer branches in isolated fixtures.
- Run Chromium in CI with explicit browser provisioning.
- Exercise desktop and wrapped phone layouts, scroll transitions in both directions, and resize while pinned followed by return to flow.
- Require positive control operation and rendered effects, alongside visibility and stability.
- Keep fast text wiring checks and syntax checks. Do not require a browser during ordinary page generation.

Fixtures must pin composer inputs, including the tray source. Otherwise this branch’s already-recorded ambient dependency undermines reproducibility.

**What would make C wrong:** if it is sold as exhaustive reachability proof across arbitrary markup, browsers, zoom levels, or dynamic content; if it only measures boxes without operating controls; or if unreliable infrastructure leads to routine skips. Missing browser execution must report **NOT RUN and fail**, following the existing glossary.

B is defensible only if the owner explicitly accepts that layout remains unverified automatically. D is useful and already implemented, but cannot exclude ordinary resizing and wrapping without abandoning the complaint being fixed. A and C substantially overlap; C makes the essential delivery obligation—CI execution—explicit.

The honest counterargument stands: **the owner’s original complaint is fixed, with all-five-producer browser verification recorded** (`docs/reviews/codex/chrome-bar-reachable-r7-codex.md:103`). “The feature is done; stop reviewing the guard” is reasonable. I did **not** independently regenerate and browser-check all five producers in this review.

The invalid-JavaScript incident alone is **insufficient** to mandate browser testing: the added Node parse gate directly addresses that failure. The stronger argument is the repeated runtime/layout failures plus the demonstrated distinction between syntactically valid output and operating controls. That supports C without claiming it will end all review thrashing.

The owner may instead declare `NO-REVIEW: <reason>`; that is an explicit acceptance of the review gap, not convergence, and is their decision (`scripts/check-review-recorded.py:856–885`).

Current checks I actually ran: **223/223** page-chrome cases and **153/153** composer cases passed; Chromium launched; the two-artifact probe above ran. **NOT RUN:** full mutation harness, remote CI, historical transient-brace reproduction, fresh all-five-producer browser sweep, real devices, physical print, zoom, and font/image reflow. Those remain verification gaps, not passes.
