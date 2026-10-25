# comprehensibility-chrome-cases — round 1, Claude half (adversarial)

Subject: `git diff origin/master...HEAD` at `a38bb55b`, worktree `scratchpad/wt-comp`. Node v20.18.2, Python 3.14,
Chromium via the main repo's `node_modules/playwright`. All experiments ran in
`scratchpad/claude-r1-tmp/` (a pruned copy of every `HARNESS_TREE` path). Nothing in the worktree or repo was written.

## What I reproduced (claims that held)

- `python3 scripts/page_chrome.py --self-test` → `227/227 passed`; `check-plan-code.py --self-test` → `215/215 passed` (sum 2007).
- Scoped mutation run (copy of all 7 `HARNESS_TREE` paths, only `page_chrome.json`, `EXPECTED_MUTATIONS` reduced to that key):
  `OK — delivered scripts mutated: 1 file(s), 93 mutation(s), 93 killed, 93 attributed to the case each names, 0 survivor(s)`.
  So the four new entries run inside the staged tree under the redirected HOME, and each is killed by the case it names.
- The anchors are unique in the source. `"var ctls=…;"` (with its quotes) appears once, at `page_chrome.py:1113`. The self-test's `:2227` is a shorter substring and does not collide.
- Fail-closed: with `PATH=/usr/bin:/bin` (no node), all six node cases go red and none is skipped (`221/227`). A timeout or non-JSON output is caught by the `except Exception` and turned into a string, so it reds too. I did not run the hang case; this is reasoned from `timeout=30`.
- Real-defect mutations that the stub kills: inverting `pin(!es[0].isIntersecting)`, observing `bar` instead of `slot`, dropping `io.disconnect()`, a zero slot reserve, a schemer move that never happens or is inverted, dropping `if(!on)sync()`, dropping `--chrome-h`.
- #300 population, re-derived. 88 tracked `.html` files; 11 carry `chrome-theme`. On this branch 4 have `.chrome-pinned{position:fixed` (3 before plus the recomposed page) and 7 do not. One of the 7 (`2026-09-03-…slice-state`) has no fragment. These match the claim.
- The recomposed `2026-10-06-brief-dev-process-speed.html`: the `<body>` is identical to master's except for the chrome lines. The `<head>` also picks up today's shim (`--accent`/`--em`, the scheme CSS). I rendered old against new in Chromium across OS {light, dark} × data-theme {none, light, dark} × data-scheme {3, 1, 2}. All 18 states gave the same computed colours for h2, p, strong, b and body background. At 320×568 the theme button sits at top=200 at scrollY 0 and at top=8.2 at 900, 2000 and the end (31332), with 0 page errors. The claim holds.

## Findings

### 1. HIGH — the 7 "half-live" pages have a FULLY live toggle. `missing_palettes == ['light']` is a detector false positive, and the owner decision is built on it
`docs/backlog.md` row 300 (the 2026-10-24 "later" note); `docs/dashboard-entries.md` (new `[needs-you]` entry); the detector is `scripts/page_chrome.py:103` `_PALETTE_RE = ':root[{attr}="{theme}"]'` together with `:269`.

**What happens (measured).** All 7 pages, and their fragments, use the three-state idiom:
- light values as the plain `:root` default;
- `@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){…}}`;
- `:root[data-theme="dark"]{…}`.

The substring `:root[data-theme="light"]` does not occur in `:root:not([data-theme="light"])`, so `missing_palettes` reports `['light']`. But the light palette is declared, and declared whole. The token sets I extracted show every one of the 31 dark tokens with a `:root` default on all 7 pages (`dark-not-in-root [] notl-not-in-root []`).

Rendered in Chromium, OS-dark plus `data-theme="light"` gives exactly the OS-light rendering on every sampled element, e.g. `2026-09-20-brief-session-status-324`:
```
light/light: body=9.52 p=6.10 h1=14.24 h2=14.24 td=9.52 .chrome=6.10 .chrome-btn=6.10 code=7.15 li=3.37
dark/light:  body=9.52 p=6.10 h1=14.24 h2=14.24 td=9.52 .chrome=6.10 .chrome-btn=6.10 code=7.15 li=3.37
```
The background flips `rgb(25,24,23)` → `rgb(247,245,241)`. The same holds on `…slice-state`, `…six-rounds-four-rules` and `…comprehensibility-state`. It also holds after I recomposed three of the fragments with today's `brief-compose.py` (to `claude-r1-tmp/out/`, HOME redirected). That recompose did drop the toggle (`grep -c 'id="chrome-theme"'` → `0`), so the "composer drops it" half of the claim is true. The reason given for it is not.

**Why it matters.** The `[needs-you]` entry tells the owner *"their theme button only half-works (no light colours were ever written for them)"*. It offers only (a) remove a working control or (b) have light colours written per fragment. Both are wrong. The colours exist and the button works. The real defect is that `missing_palettes` and the compose refusal are blind to a valid idiom. That makes a third option, cheaper than either: teach the detector the `:root` + `:not([data-theme="light"])` form, or have the fragment add an explicit `:root[data-theme="light"]` alias of its `:root` values. Neither invents a colour. This is also backlog #299's regression in the making: following option (a) removes 7 working buttons.

**Fix.** Withdraw "half-live" and "no light colours were ever written" from row 300 and from the dashboard entry. Re-pose the decision with the detector false positive as its premise. File the detector gap. If anything ships from it, it needs a positive case: a fragment in the three-state idiom must report `[]`.

### 2. MEDIUM — #305 is closed, but a runtime fault in any click handler still passes all 227 cases. The stub silently discards handlers despite its "STRICT" comment
`scripts/page_chrome.py` `_STUB` (`addEventListener:function(){}`, `G.ResizeObserver=function(){this.observe=function(){};}`); row 305's closure text; the dashboard's "A crash fails the tests".

**What happens (each run on a copy, line-scoped edit, full self-test):**
```
:992 var n=nope();                        (theme CLICK handler throws)  -> rc 0, 227/227 passed
:992 R.setAttribute(A,'dark')             (theme button can never go light) -> rc 0, 227/227 passed
:1012 nope();var b=e.target…              (schemer CLICK handler throws) -> rc 0, 227/227 passed
:990  String(cur()==='light')             (initial aria-pressed inverted) -> rc 0, 227/227 passed
new ResizeObserver(sync);                 (re-measure on resize never observed) -> rc 0, 227/227 passed
```
Row 305's headline is *"a runtime fault is syntactically valid, so every text and parse case stays green while every control is dead."* A fault that fires on click is exactly that, and the theme button is just as dead, yet the closure is unbounded. The closure caveat names only layout.

The stub comment claims *"a selector or method it does not model THROWS, so an unmodelled call is a loud red, never a permissive Proxy's quiet pass."* For the handler surface that is false: `addEventListener` and `ResizeObserver.observe` are modelled as silent no-ops. That is the permissive pass, applied to precisely the code that makes the controls work. The row's own recorded lesson ("closed the INSTANCE only") repeats here: the load-time member is closed, the click-time member is not.

**Fix.** Make the stub's `addEventListener` record `(type, handler)` per element. Then, in a case, invoke the theme element's `click` handler and assert positive effects: `root.getAttribute('data-theme')` flips and `aria-pressed` follows. Do the same for the schemer (with one modelled `button[data-s]`, giving `e.target.closest`). Record `ResizeObserver.observe` targets and assert `bar` is observed. Alternatively, state that bound in row 305 and in the dashboard and leave the click half open. Either way, "a crash fails the tests" should say "a crash on load".

### 3. LOW — the `ctls` value case expects the same constant from both layouts, so a constant survives it
`scripts/page_chrome.py`, case "the observer's margin is cut at the TOPMOST control…": both layouts expect `["-150px 0px 0px 0px"]`.

**What happens.** I appended `tailPx=150;` after the `Math.max(0,sb-m)` assignment at `:1163`. Result: `rc 0, 227/227 passed`. Each realistic mutation I tried (max instead of min, first or last control only, a dropped selector, sign flip) does change one margin and reds. But the case is satisfied by the constant its own fixture produces. This is the repo's "two distinct inputs in one case" rule.

**Fix.** Make the two layouts' expected tails differ, e.g. layout 2 = theme 30 / schemer 100, so the expected margins are `-150px` and `-170px`.

### 4. LOW — the falsifier cases lose the CANNOT RUN text
`_effect(...)[0]` and `[1:3]` slice a string when `_runs` returns `CANNOT RUN: …`. With node absent the output reads `got 'C' want 'Error: dead'` and `got 'AN' want (False, None)`. It is still red, so it fails closed, but the reason is mangled. **Fix:** return `rep` unchanged when it is not a dict before indexing, e.g. `(lambda r: r if isinstance(r, str) else r[0])(...)`.

## Other checks — no finding
- The dashboard's numbers match what I measured: 223→227, 89→93, 2003→2007, 11/3/8 and the 0/900/2000/end pinning.
- The `brief-compose.py` comment describes the per-token mechanism correctly. Its "compose already refuses the half-live toggle" is true but also over-broad, because it refuses full-live ones too (Finding 1).
- The real-defect mutations in "What I reproduced" are killed, so the stub is not ambient for the pin block.

VERDICT: NOT CONVERGED
