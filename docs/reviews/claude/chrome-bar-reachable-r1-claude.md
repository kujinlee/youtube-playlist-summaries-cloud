# chrome-bar-reachable — round 1, Claude half

Reviewed `git diff master...HEAD` at `6d07ea3a`. Worktree unmodified; outputs to `/tmp/rv`.
Browser measurements via Playwright against pages generated into `/tmp/rv`.

## BLOCKING — `page_chrome.py:197` / `brief-compose.py:809` — the composer emits a second `id="schemer"`, and the one it emits is the DEAD one

`chrome_for` branch 3 adds `chrome_bar(..., textstyle=True)` to a fragment that may already
carry the prototype's inline switcher. `chrome_script` binds `getElementById('schemer')`,
which resolves to the FIRST match — the fragment's inline copy — so the buttons in the new
chrome bar have no handler.

Composed all 20 real fragments and classified the branch each takes:

    branch 2 stamp-only × 17      branch 3 FULL BAR + switcher × 2      branch 1 own-control × 0

Both branch-3 fragments (`2026-10-06-brief-dev-process-speed`,
`2026-10-15-brief-status-alignment`) already carry `id="schemer"`. **2 of 2 — every real
page that gets this feature gets the collision.** In the browser:

    schemerCount: 2
    locations: [{parentClass:"ex-body", inChromeBar:false}, {parentClass:"chrome", inChromeBar:true}]
    getElementByIdIsInChrome: false
    click bar's data-s="1"    -> attr unchanged (null)
    click inline data-s="2"   -> attr "2"
    barButtonClasses:    ["on:true", ":false", ":false"]
    inlineButtonClasses: [":false", "on:true", ":false"]

## BLOCKING — `page_chrome.py:235-237` — the switcher's entire consumption layer is unguarded, and inert on any page without `.ex-body`

`text_style_css()` styles only `.ex-body …`. Nothing in the repo EMITS `.ex-body` —
`grep -rn "ex-body" scripts/ .agents/` returns only those three lines. It is hand-authored:
3 of 20 repo fragments, 7 of 95 live pages.

`assert_wired`'s two switcher arms cannot see this. The token arm passes because SHIM
declares `--accent`/`--em` on `html`; and `if has_text_control(page) and TEXT_ATTR not in
page` is **vacuous on the only path that produces the control**, since `chrome_for` always
emits `text_style_css()` (which contains `data-scheme`) alongside it.

Composed a fragment with both palettes and no `.ex-body` (rc=0), then in the browser:

    3 (colour, default): rgb(51,96,122) | rgb(21,27,35) | rgb(21,27,35)
    2 (headings only):   rgb(51,96,122) | rgb(21,27,35) | rgb(21,27,35)
    1 (plain):           rgb(51,96,122) | rgb(21,27,35) | rgb(21,27,35)
    attrAfter: "1"   distinct renderings: 1

And the coverage half — deleting all three `.ex-body` rules from the shipped source:

    page_chrome.py: 103/103 passed      brief-compose.py: 132/132 passed

**235 cases, zero see it.** A survivor the manifest's 20 entries do not cover.

## HIGH — `page_chrome.py:308` — `background:inherit` resolves to `transparent` on 4 of 4 generator pages

The comment asserts `inherit` takes `<body>`'s own background. False wherever an
intermediate wrapper is transparent, which is every generator.

| page | `.chrome` parent | computed background | body bg |
|---|---|---|---|
| gen-dashboard | `DIV.shell` | `rgba(0,0,0,0)` | `rgb(246,245,242)` |
| gen-goals-page | `HEADER.mast` | `rgba(0,0,0,0)` | `rgb(246,245,242)` |
| gen-features-page | `HEADER.mast` | `rgba(0,0,0,0)` | `rgb(246,245,242)` |
| gen-backlog-page | `DIV.wrap` | `rgba(0,0,0,0)` | `rgb(247,246,243)` |

Holds only on the brief-composed path, where `.chrome` IS a direct `<body>` child.

## HIGH — `page_chrome.py:296` — `position:sticky;bottom:0` is a provable no-op on all five non-composed producers, and the refusal message asserts something false about them

A `bottom`-only sticky offset only pulls an element UP into view; it never pushes down a box
whose flow position is above the fold. On every generator the bar is near the TOP.

    gen-dashboard         y=126  (child 1 of 374 in div.shell)  docH=29041  visibleAtMidScroll=false
    gen-goals-page        y=151                                 docH=7355   visibleAtMidScroll=false
    gen-features-page     y=151                                 docH=12759  visibleAtMidScroll=false
    gen-backlog-page      y=87                                  docH=42518  visibleAtMidScroll=false
    explainer-serve index y=99                                  docH=2419   visibleAtMidScroll=false
    dashboard sweep: 0 -> top 126 visible | 2000 -> -1874 | 10000 -> -9874 | 28241 -> -28115

The guard's text — "It is the last child of `<body>`, so on a long page that is the final
pixels" — is wrong on all four generator pages, which are where it will most be read.

## HIGH — `page_chrome.py:148-150` — the "no `.chrome` rule" exemption is a hole a page reaches end-to-end

`assert_wired` runs on the FRAGMENT only; `compose()` never checks the document it returns
(`grep -n assert_wired scripts/brief-compose.py` -> one hit, line 796, argument `content`).
A wired fragment with no `.chrome` rule is exempted, branch 1 adds nothing, and the composed
page ships a control with no chrome CSS at all.

    bar_unreachable on the fragment: False
    assert_wired: ACCEPTED
    composed page: '.chrome{' occurrences: 0
    browser: position="static" absoluteY=8423 docH=8481 stuckAtMidScroll=false hasThemeButton=true

That is backlog #300's exact defect, reproduced THROUGH the guard shipped to prevent it.

## MEDIUM — `page_chrome.py:296-299` — the pin is applied to stamp-only bars, which have nothing to reach

17 of 20 real fragments take branch 2: no control, stamp only — but `chrome_css()` is still
emitted, so the bar now sticks. On `2026-09-24-brief-velocity-ledger.html`: `hasControl=false`,
`stuckAtMidScroll=true`, `height=38`. 38px of every viewport, permanently, for a timestamp.

## MEDIUM — `page_chrome.py:296` + `flex-wrap:wrap` — the bar takes 22.7% of a small phone viewport

    400x700 -> barHeight  96px = 13.8% of viewport
    320x568 -> barHeight 129px = 22.7% of viewport   (no horizontal overflow)

## MEDIUM — `page_chrome.py:243` — unselected switcher options are below AA

Compositing the 0.6 opacity against the bar's own ground, on composed
`2026-10-15-brief-status-alignment`:

    light: unselected 2.32:1   selected 6.62:1
    dark:  unselected 2.85:1   selected 7.02:1

The module docstring records retuning the dashboard because `--ink-soft` measured 4.32:1
"under AA". This control ships at roughly half that and was not measured.

## LOW — `page_chrome.py:298` + the manifest — the stated z-index of the tray is wrong, and the case asserts the literal rather than the property

Comment and `expect` both say the tray "owns z-index 5". Measured: `#tray` computes
`z-index: 50`, and the pages declare `z-index:70`. The conclusion (chrome below tray)
survives; the cited number is invented. Mutating `z-index:1 -> 0` — still below the tray, so
the stated property is preserved — reddens that case, so it pins the string, not the ordering.

## LOW — two shipped declarations have no mutation

Applied against a clean 103/103 control:

    SURVIVED   border-top:1px solid var(--rule,transparent)  ->  border-top:0
    SURVIVED   padding-block:.45rem                          ->  padding-block:0

## NOT RUN

Real-device phone rendering (viewport emulation only); OS `prefers-color-scheme` simulated
via `data-theme` rather than the media query; print rendering; the ask tray in its OPEN
state; corpus was 18 live control-carrying pages + 20 recomposed fragments + 5 freshly
generated pages, not all 95.

## Design answers requested by the coordinator

**`fixed` keeps the bar visible at mid-scroll on 5 of 5; `sticky` on 0 of 5.** Width needs
explicit `left:0;right:0` or the bar shrink-wraps and `.chrome-when{margin-inline-start:auto}`
stops reaching the right edge.

**Containing-block breakers: none.** Walked the full ancestor chain for `transform`, `filter`,
`backdrop-filter`, `perspective`, `contain` and `will-change` on all five producers and the
composed brief — empty list everywhere.

**Occlusion is real and is what `fixed` costs.** `body` computes `padding-bottom: 0px` on
dashboard/goals/features/backlog. Text-bearing leaves inside the final `barH` px:

| page | barH | covered |
|---|---|---|
| gen-features-page | 44 | **60** |
| gen-backlog-page | 44 | **9** |
| gen-dashboard | 45 | 0 |
| explainer-serve index | 46 | 0 (`body` has `margin-bottom: 48px`) |
| composed brief | 63 | 0 |

`barH` is not a constant: 44-63px at 1280px, 129px at 320x568. A literal `padding-bottom: 48px`
is wrong on phones; the robust form lets the bar report its own height.
