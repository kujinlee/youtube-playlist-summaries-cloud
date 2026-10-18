# chrome-bar-reachable — round 4, Claude half

**REVIEW GAP:** codex — not invoked for round 4. Rounds 2+ ALTERNATE per `docs/plugins.md`;
rounds 2, 3 and 5 are the Codex side, round 4 is the Claude side. Single-reviewer by
construction.

Reviewed `git diff master...HEAD` at `03b78e94`. Worktree unmodified. Browser measurements
via Playwright/Chromium served over http.

## BLOCKING — `brief-compose.py:941` — the `scoped_css_emitted` flag reads the TRAY css parameter, so round 3's entire consumer arm is dead on every path

`compose(content, title, css, markup, script, …)` — `css` is the extracted Ask-tray CSS. The
scoped stylesheet is the LOCAL `chrome_css`, assigned at `:915` from `chrome_for` and written
into the page at `:917-918`. `css` is never reassigned. `TRAY_SELECTOR` (`:594`) is
`#tray|\.askbtn|#qbox|#qt\b|#sentnote|#modechip`, so `.ex-body` can never be lifted into the
tray — the expression cannot be True for any input.

Failure scenario: a fragment with its own `id="schemer"`, both palettes, `--accent`/`--em`
declared and NO `ex-body` consumer takes `chrome_for`'s third branch, where `own_switcher`
makes it emit `text_style_css()`. The page ships three buttons that flip `data-scheme`,
persist a choice and restyle nothing — the r3 Blocking, verbatim.

    text_style_css() in tray css ? False
    has_text_control(frag): True   has_text_consumer(frag): False
    COMPOSED OK  -> len 11054
      text_style_css in doc: True   'ex-body' as a live class: False

Instrumenting `assert_wired` across the suite: **0 of 41 calls ever receive True.**

    suite rc 0 133/133 passed
    total assert_wired calls: 41        calls with scoped_css_emitted=True: 0

And there is no falsifier: severing `:941` to the literal `scoped_css_emitted=False` leaves
page_chrome **140/140** and brief-compose **133/133**. Replacing it with the correct
`page_chrome.text_style_css() in chrome_css` ALSO leaves 133/133 — no case distinguishes the
right expression from the wrong one. Round 3's "verified both ways" was verified at the UNIT;
the call site passes a constant.

Not currently live on committed fragments: of the 20 in `docs/explainers/`, the two reaching
branch 3 both carry `ex-body`.

## BLOCKING — `scripts/mutations/page_chrome.json` — 24 of 38 entries are unattributable, and `check-plan-code.py --mutate .` is RED on this branch

Attribution is `w == f` (equality), `check-plan-code.py:2083`. 24 entries give `expect` as a
SUBSTRING of the case name (`'a LOW positive z'`, `'THE DEFECT'`, `'FIRST-wins'`, …).

    $ python3 scripts/check-plan-code.py --mutate . --shard 1327/1483
      ✗ mutation 'the bar is raised into the floater band': `expect` 'a LOW positive z'
        matched 0 red case(s)
    FAILED — 1 mutation(s), 1 killed, 0 attributed to the case each names
    real rc = 1

Full scoped sweep over all 38: `38 killed, 14 attributed, 0 survivors`, rc=1. Independently
derived by harvesting all 140 case names and comparing: 14 attributable, 24 not — the same
split, so the tally is not an artefact of pruning. `git show master:…` has 11 entries, every
`expect` a full case name: master is green and this branch breaks the gate.

### The exact predicate (requested by the coordinator)

`parse_fail_names` is the whole contract:

    return [l.strip()[7:].rsplit(": got ", 1)[0].strip()
            for l in out.split("\n") if l.strip().startswith("[FAIL] ")]

and attribution requires `expect` to EQUAL exactly one parsed name. No normalisation: one
trailing space breaks it (measured). Truncation applies to the case NAME at the LAST
`": got "`. `expect` may be a list — every element must match exactly one red case. Two
entries MAY share an `expect`; what is refused is a duplicate `name` or duplicate anchors.

## HIGH — `page_chrome.py:119` / `:309` — `has_control` / `has_text_control` are still substring tests for `id="…"` with double quotes

    has_control(single-quoted): False      _scan ids: ['chrome-theme']
    missing_palettes: []   bar_unreachable: False
    assert_wired: PASSED (no palettes, no pin, no bound script check)
    double-quoted equivalent: REFUSED

A valid single-quoted live control disables EVERY arm. The same hole takes `ID="schemer"`
and `id = "schemer"`. This is r2's `class='ex-body'` finding, fixed for the class predicate
and left in both id predicates by a fold that was editing `_Scan.ids` in the same commit.

## HIGH — `page_chrome.py:194-200` — the fold recorded `<template>`'s own id and dropped `<noscript>`'s

    getElementById_schemer: "NOSCRIPT"     noscript_child_elements: 0
    getElementById_tmplid:  "TEMPLATE"     inside_template_findable: false

A page with `<noscript id="chrome-theme">` and `<noscript id="schemer">` before the real
controls: `_scan(page).ids == ['chrome-theme','schemer']`, the duplicate refusal counts 1
each, and `assert_wired` PASSED. Rendered: both visible controls completely inert.

## MEDIUM — `page_chrome.py:786` — `_scripts()` is a regex that does not strip comments

A control whose handler is entirely commented out satisfies the binding assertion — the arm
this module calls "asserting the MECHANISM". `_Scan` has a case for exactly this shape.

## MEDIUM — `page_chrome.py:1081-1082` — the at-rule case does not bound the claim it is written to bound

Two emitter-only changes with ZERO at-rules collapse three renderings to one, both suites
green. Mutation A: three same-specificity `.ex-body` overrides. Mutation B: a second bare
`:root,:root[data-scheme]` role block.

    scheme 3/2/1 all: h2 rgb(136,136,136)  p rgb(136,136,136)  strong rgb(136,136,136)
    distinct_renderings: 1     (known-positive control, unmutated: 3)

## MEDIUM — `page_chrome.py:184`, `:194-210`, `:226-228` — one counter shields two mechanisms

    noscript closed by </template>: _scan classes=['ex-body']  Chromium: 0 ex-body elements
    template closed by </noscript>: _scan ids=['chrome-theme'] Chromium: getElementById null

Wrong in both directions: a fail-open, and a false duplicate-id refusal.

## MEDIUM — `page_chrome.py:119` — `has_control` sees a control inside an HTML comment

    has_control(commented): True   _scan ids: []
    assert_wired REFUSED a page with NO live control

## MEDIUM — `page_chrome.py:777` — the reachability refusal names `.chrome` while the predicate requires `.chrome-pinned{`

The suite has an identity case proving `.chrome{position:fixed}` does NOT satisfy the check.
An author who acts on the sentence gets a page the guard still refuses.

## LOW — `page_chrome.py:152` — the pin regex requires `{` immediately after the class

    .chrome-pinned,.x{position:fixed;left:0;right:0}   bar_unreachable=True  <- valid, refused
    .x,.chrome-pinned{position:fixed;left:0;right:0}   bar_unreachable=False
    ".chrome-pinned\n{position:fixed}"                 bar_unreachable=True  <- valid, refused

## LOW — `page_chrome.py:756` — the "no scheme CSS at all" arm is near-vacuous

`TEXT_ATTR in chrome_script()` is True and every page with the theme control must ship that
script, so the arm only fires for a page with the switcher and no theme control, which no
producer emits.

## Nothing found at any severity on

`provenance`, stamp/slug escaping, the z-index band, print-media behaviour as asserted from
text, `missing_palettes`' token logic, first-wins duplicate attributes (browser-confirmed),
`<template>` contents shielding (browser-confirmed), ids inside `<svg>`.

## NOT RUN

Exhaustive revalidation of every prior finding; remaining malformed-nesting, foreign-content
and runtime-injection variants; exhaustive mutation-pair sweep; real-device and physical
print checks.
