# chrome-bar-reachable — round 7, CLAUDE half

Branch tip reviewed: `c4a70a89` ("Round 7: all five findings folded…"). Primary subject: that
commit, on the brief's instruction to assume it did it again.

This is round 7's SECOND half. Under the alternating topology (`docs/review-method.md`, *Round
topology*) rounds 2+ alternate and the second half reviews the FIXES — so the subject is the
fold of `docs/reviews/codex/chrome-bar-reachable-r7-codex.md`, which is this commit.

Instrument: the three suites, the shipped mutation harness scoped to the two touched manifests, a
programmatic ambient-assertion scan over both suites, and Chromium (Playwright) over **five real
pages composed by `brief-compose.py` from the branch's own code**, served over `http://` with a
redirected `$HOME` so nothing reached the reader's live `~/explainers/`.

**It did it again, twice, and one of the two is the fold's own class left open one level deeper.**

---

## Blocking / High

### H1 — High. The fold's own slot fix does not close its own class: a slot with two `.chrome` rows still binds the one with nothing to press, and nothing pins at all

`scripts/page_chrome.py:1003`–`:1009`.

r7 MEDIUM 3 was *"the composer can generate two slots and the pin script chooses the stamp-only
one"*. The fix widened the search from *the first slot* to **the first slot whose FIRST `.chrome`
holds a control**. The predicate it needed was *the first `.chrome` that holds a control*. One
`.chrome` deeper and the defect is unchanged.

Concrete failing input — a fragment that brings its own chrome as a stamp row plus a control row
inside one slot (`scripts/page_chrome.py` emits both in a single `.chrome`, so splitting them into
two rows is an ordinary authoring shape, not malformed and not adversarial):

```html
<div class="chrome-slot">
  <div class="chrome"><span class="chrome-when">generated now</span></div>
  <div class="chrome">  <!-- theme_control() -->  </div>
</div>
```

`brief-compose.py` **accepts** the page (branch 1 of `chrome_for`: own wired chrome, carries
`class="chrome-when"`, so no second slot is added — one slot, two `.chrome`).

MEASURED in Chromium at 320×568 on the composed page
(`2026-10-19-brief-twochrome.html`):

| | |
|---|---|
| `.chrome-slot` count | 1 |
| `.chrome` inside it | 2 |
| `--chrome-h` after load | **`(UNSET)`** — `sync()` never ran |
| class on either `.chrome` at scrollY=2500 | `chrome`, `chrome` — **neither pinned** |
| `#chrome-theme` rect at scrollY=2500 | **top −2383.04, bottom −2358.65** |
| on screen | **no** |

Mechanism: `slots[si].querySelector('.chrome')` returns the stamp row, which has no control, so the
loop skips the slot; the fallback at `:1009` then takes `slots[0]` and *its first `.chrome`* — the
same stamp row — so `if(bar&&bar.querySelector('#chrome-theme,#schemer'))` is false and the whole
pin block, `sync()` included, is skipped. This is r7 MEDIUM 3's measurement (`theme button ending
at y=-1659`) reproduced at y=−2383 **with the fix for it in place**.

**Inside the declared subject.** The module docstring's bound covers "fragments under
`docs/explainers/*.fragment.html` … because those are hand-authored". This is valid,
non-adversarial hand-authored fragment markup that `assert_wired` and `compose` both accept.

Note on what is *not* claimed: `bar_unreachable` disclaims the layout property explicitly
(`:566`–`:575`), so this is not that guard failing its stated job. It is the runtime selector
binding a bar with nothing to press.

Fix shape (and it is the shape the module already prefers — ask the question of the thing, not of
its container): iterate `.chrome` elements, not slots, and derive the slot from the match —
`document.querySelectorAll('.chrome-slot .chrome')`, take the first whose
`querySelector('#chrome-theme,#schemer')` is non-null, and set `slot = bar.closest('.chrome-slot')`.
The existing fallback then only needs to fire when no `.chrome` holds a control yet.

---

### H2 — High. The new `_interactive` counter is lifted by end tags inside a shield, so the bar lands inside a link again — the exact r4 "one counter per mechanism" defect, and the comment recording it is the next line after the counter's own declaration

`scripts/page_chrome.py:522` (the decrement) against `:509` (the increment).

The increment at `:509` sits **after** the `if any(self._depth.values())` shields at `:457` and
`:499`, so an `<a>` inside a `<template>` or `<noscript>` correctly does not count. The decrement
at `:522`
has **no shield test at all**, so a shielded `</a>`, `</button>`, `</label>` or `</summary>`
decrements a *live* open-interactive count. The count reaches zero, `title_end` is recorded, and
`place_bar` inserts the bar after `</h1>` — inside the anchor.

This is the failure the module's own comment at `:399`–`:403` records from r4 — the line
immediately after `self._interactive = 0` at `:398`: *"ONE COUNTER PER
MECHANISM. r4 measured a single shared counter being lifted by the WRONG end tag."* The new counter
was added without the guard that comment exists to demand.

Concrete failing input:

```python
place_bar('<a href="#dest"><noscript><a href="/plain">plain</a></noscript>'
          '<h1>Title</h1></a><p>Intro</p>', "[BAR]")
```

returns

```
<a href="#dest"><noscript><a href="/plain">plain</a></noscript><h1>Title</h1>
[BAR]</a><p>Intro</p>
```

— `[BAR]` is inside the outer `<a>`. `<template>` in place of `<noscript>` behaves identically;
`<button>…<template><button>…</button></template><h1>` does too. The discriminating control passes:
the same fragment **without** the shielded `</a>` prepends correctly.

BROWSER-VERIFIED on the real composed page `2026-10-19-brief-linked.html` (composed by
`brief-compose.py`, which accepted it):

| | before press | after press |
|---|---|---|
| `#chrome-theme`'s `closest('a')` | `<a href="#dest">` | — |
| `location.hash` | `""` | **`#dest`** |
| `scrollY` | 0 | **6420** |
| `data-theme` | `null` | `dark` |

Pressing Theme changes the theme **and navigates**, jumping the reader 6420px down the page. That
is r7 MEDIUM 4's defect, verbatim, on the commit that fixed it.

**Inside the declared subject**, by the same argument r7's reviewer used for the parent finding and
the docstring accepted: a linked heading is ordinary fragment markup, and `<noscript>` /
`<template>` are precisely the two elements this scanner already exists to handle in hand-authored
fragments (r3 found a real `<template id="schemer">` in a real one).

**Honest bound on the impact: 0 of the 20 repo fragments are affected today** — I scanned all of
them and every one yields a live `</h1>`, so this is latent, not live. I grade it High rather than
Medium on r7 HIGH 2's precedent: the severity here is that a class the fold claims to have fixed
is reintroduced by the fold, in the same function, with the warning already written beside it.

Fix: `if tag in _INTERACTIVE and self._interactive and not any(self._depth.values()):`.

---

## Medium

### M3 — Medium. `--chrome-h` is one document-level value and `.chrome-slot` is a class selector, so with two slots the shorter one gains a permanent blank band. **NOT created by this fold — the control says so**

`scripts/page_chrome.py:881` (`.chrome-slot{min-height:var(--chrome-h,0)}`) against `:1097`
(`setProperty('--chrome-h', bar.getBoundingClientRect().height)`).

`sync()` measures **the one bar it selected** and writes the result to `document.documentElement`,
where the rule applies it as `min-height` to **every** `.chrome-slot`. A stamp-only slot therefore
reserves the control-bearing bar's height.

MEASURED at 320×568 on `2026-10-19-brief-twoslot2.html`, a real two-slot page `brief-compose.py`
accepted (fragment brings its own wired chrome with a theme control and a switcher but no
`chrome-when`, so the composer adds `stamp_bar()` under the title):

| slot | holds a control | its bar | slot height | blank |
|---|---|---|---|---|
| 0 (composer's stamp bar, under the title) | no | 29.89px | 65.88px | **35.98px** |
| 1 (fragment's own chrome) | yes | 65.88px | 65.88px | 0 |

35.98px of dead space between the title and the prose on a 568px viewport, in a slot that never
pins, permanently. Injecting `stamp_bar()`'s exact markup as a second slot into the real
`2026-10-06` composed page (where the bar wraps to three rows at 320px) gives **96.58px**.

⚠ **CONTROL RUN, because "fix → defect appears" is not a cause.** I rebuilt the same page with the
branch's code and **only** r7's slot selection reverted to the pre-fold two lines
(`querySelector('.chrome-slot')` / `.querySelector('.chrome')`). The blank band is still there —
18.2px, on slot 1 instead of slot 0. So this is **pre-existing and surfaced by the fold, not caused
by it**; what the fold changed is which slot pays and how much. (The same control run also
reproduces r7 MEDIUM 3 exactly: the stamp bar pinned, the switcher moved into *it*, and
`#chrome-theme` at y=−1355.95 — so the fold's selection change is a real improvement, which is why
H1 is "incomplete", not "wrong".)

**Inside the declared subject**: the reservation and its CSS rule are this module's.

### M4 — Medium. The ambient-assertion class was fixed for the five reported instances and not swept; a measured severance leaves the suite at 214/214

`scripts/page_chrome.py:1551`.

```python
case("the bar carries all three controls",
     (has_control(bar), "chrome-refresh" in bar, "chrome-when" in bar), (True, True, True))
```

`"chrome-refresh"` occurs **twice** in `chrome_bar(…)`: on the button, and on the sibling
`<span id="chrome-refresh-say">` at `:791`.

MEASURED severance — rename only the button's id, which is the id `chrome_script` binds by
(`:972`, `document.getElementById('chrome-refresh')`), so the Refresh button becomes permanently
inert on all five generated pages:

```python
#  scripts/page_chrome.py:787
-   return (f'<button id="chrome-refresh" type="button" class="chrome-btn" '
+   return (f'<button id="chrome-refresh-DEAD" type="button" class="chrome-btn" '
```

`python3 scripts/page_chrome.py --self-test` → **214/214 passed**. Restored → 214/214.

This is r7 MEDIUM 5's class. The commit message says "All five now name exact contiguous
expressions" — true, and I verified all five (plus eight more of the fold's new literals) occur
exactly once in their producer's output. What was not done is the sweep.

**Programmatic ambient-assertion scan over BOTH suites** (ast over `self_test` / `_self_test_body`,
every `LITERAL in <str expr>`, evaluated, counting occurrences): **78 assertions evaluated, 4 are
ambient** — r7 reported five, all in `page_chrome`:

| suite | literal | occurrences | assertion |
|---|---|---:|---|
| page_chrome | `chrome-refresh` | 2 | `:1551` — severance above |
| brief-compose | `:where(` | 4 | `:1477` (two of the four are inside the SHIM's own CSS comments; the conjoined regex covers only the `body` rule) |
| brief-compose | `html { --rule:` | 2 | `:1491` — light and dark blocks; severing either leaves the other |
| brief-compose | `chrome-theme` | 4 | `:1738` |

(39 further `in` assertions in the two suites are refusal-message checks inside local helpers my
scan could not evaluate; they are not severance-defences, so the 4 is a floor for the ambient
count, not a ceiling.)

### M5 — resolved by this document, recorded because the gate was RED and the reason is useful

At `c4a70a89` the branch tip failed a merge gate:

```
$ python3 scripts/check-review-rounds.py ; echo rc=$?
FAILED — 1 review round(s) with one half and no stated reason:
  ✗ chrome-bar-reachable round 7: only codex — claude neither ran nor recorded a `REVIEW GAP:` line
rc=1
```

The commit filed `docs/reviews/codex/chrome-bar-reachable-r7-codex.md` and its verdict with no
Claude half and no `REVIEW GAP:` line. **Filing this document at
`docs/reviews/claude/chrome-bar-reachable-r7-claude.md` clears it** — verified below. ⚠ Recorded
rather than dropped because the near-miss is instructive: numbering this half `r8` would have left
round 7 permanently one-sided while *looking* like extra diligence, and the guard would have stayed
red with a new round on top of it. The alternating topology does not mean a round has one half; it
means the two halves are sequential and the second reviews the first's fixes.

---

## Low

### L6 — Low. A figure in the commit message does not reproduce: `153.45px`

The commit message states, as VERIFIED at the reviewer's exact sequence, that "returning to flow
re-measured `--chrome-h` from 62.1px to **153.45px**, matching the bar exactly."

I ran that exact sequence against the same fragment (`2026-10-06-brief-dev-process-speed.fragment
.html`) composed by the branch's own `brief-compose.py`:

| step | class | `--chrome-h` | bar height | `#chrome-theme` |
|---|---|---|---|---|
| load 1280×900 | `chrome` | 62.1484375px | 62.148 | 184.70 → 214.33 |
| scroll 1800 | `chrome chrome-pinned` | 62.1484375px | 63.148 | 17.26 → 46.89 |
| resize 320×568 (pinned) | `chrome chrome-pinned` | 62.1484375px | 133.211 | 8.20 → 37.83 |
| scroll 0 (**return to flow**) | `chrome` | **132.2109375px** | 132.211 | 200.08 → 229.71 |
| scroll 231 | `chrome chrome-pinned` | 132.2109375px | 133.211 | 8.20 → 37.83 |

**The property claimed is true**: the return to flow re-measures, and the new value matches the
in-flow bar exactly (132.2109375 vs 132.211). The `62.1px` start reproduces. The `153.45px` end
does **not** — and `132.19px` is the number r7's own reviewer recorded for the in-flow bar in the
finding being fixed, which is what I measure. One of the two figures in a "VERIFIED" line is
therefore unsourced. Container width differs with the tray source `brief-compose` lifts, so I do
not claim the fold's author measured nothing; I claim the number as written is not reproducible
from the branch and should be corrected or attributed.

### L7 — Low. The pinned bar is a full pixel taller than its own reservation

`--chrome-h` is measured **in flow**, where the bar is the container's width; pinned it is
`left:0;right:0` at viewport width, so it wraps differently. Measured at 320×568: reserve
132.2109375px, pinned bar **133.211px**. The code comment at `:1089`–`:1091` makes a point of
sub-pixel fidelity ("a 43.109375px bar reserved 43px … One pixel, found only by measuring across
the transition") while the pinned bar overflows its reservation by 1.0px and overlaps one pixel of
content. `document.documentElement.scrollHeight` is unchanged across the transition (31311 both
sides), so there is no page shift — this is overlap, not reflow.

### L8 — Low, and it argues the BOUND rather than filing a defect. `_INTERACTIVE` covers markup-level swallowers only

`scripts/page_chrome.py:345`. The set `{a, button, label, summary}` is complete for standard
elements that can contain an `<h1>` and swallow a press — I checked the plausible alternatives
(`select`/`option`, `textarea`, `iframe`, `object`, `details` without `summary`, `legend`) and none
both admits an `<h1>` and swallows the press. What is **not** covered is an ancestor that swallows
by attribute: `onclick=`, `tabindex`, `role="button"`. A hand-authored fragment with a clickable
card wrapping its title is the shape, and the comment at `:396`–`:397` says the set *is* "the
elements that would swallow a press", which over-promises by one category. Either narrow the
sentence or add an attribute test; I am not filing it as a defect because no repo fragment has one.

---

## What I verified and could NOT break — the negative results, with the evidence

**The three suites reproduce exactly as claimed.**

| command | claimed | measured |
|---|---|---|
| `python3 scripts/page_chrome.py --self-test` | 214/214 | **214/214** |
| `python3 scripts/brief-compose.py --self-test` | 149/149 | **149/149** |
| `python3 scripts/check-plan-code.py --self-test` | 178/178 | **178/178** |

**The shipped mutation harness reproduces, over the whole of both manifests.** Scoped per the
brief's recipe (`rsync` every path in `check-plan-code.HARNESS_TREE` read with `ast`; delete all
`scripts/mutations/*.json` but `page_chrome.json` and `brief-compose.json`; `EXPECTED_MUTATIONS`
reduced to those two keys at 83 and 22; `--mutate .` in the copy):

```
OK — delivered scripts mutated: 2 file(s), 105 mutation(s), 105 killed,
105 attributed to the case each names, 0 survivor(s) — measured over the WHOLE manifest
```

105/105/105/0, as claimed. Every anchor in both manifests resolves (the harness refuses a
multi-match anchor, and none was refused) and every `expect` names exactly one red case (that is
what "attributed to the case each names" measures). The four derived anchors hold.

**The exact-expression assertions are genuinely unique.** All five from r7 MEDIUM 5 plus eight more
literals the fold added occur **exactly once** in their producer's output:

```
1  chrome_script: "try{var s=localStorage.getItem(K);if(s==='dark'||s==='light')R.setAttribute(A,s);}"
1  chrome_script: "try{localStorage.setItem(K,n);}catch(e){}});}"
1  theme_control: 'aria-pressed="false"'
1  chrome_script: 'if(!window.IntersectionObserver){'
1  chrome_script: 'pin(r.bottom-tailPx<=0||r.top>=(window.innerHeight||'
1  chrome_script: "window.addEventListener('scroll',fb);"
1  chrome_script: "bs[i].setAttribute('aria-pressed',String(on));"
1  chrome_script: "bar.classList.toggle('chrome-pinned',on);if(!on)sync();"
1  chrome_script: "if(bar.classList.contains('chrome-pinned')===on)return;"
1  chrome_script: "if(sb&&sb.querySelector('#chrome-theme,#schemer')){slot=slots[si];bar=sb;break;}"
1  chrome_script: "if(!slot&&slots.length){slot=slots[0];"
1  chrome_script: "document.querySelectorAll('.chrome-slot')"
1  chrome_script: "className=on?'on':''"
```

I could not find a different statement that satisfies any of them.

**The `pin`/`sync`/`arm` recursion terminates, and I tried hard to make it not.** Class-attribute
mutations counted with a `MutationObserver` on the bar of the real composed `2026-10-06` page:

| probe | result |
|---|---|
| reviewer's four-step sequence (1280×900 → 1800 → resize 320×568 → 0 → 231) | **3 flips total**, one per crossing |
| stationary, 2s, at scrollY=0 | **0 flips** |
| stationary, 2s, at scrollY=1200 (pinned) | **0 flips** |
| stationary, 600ms each, every scrollY from 210 to 250 in 2px steps (the threshold band) | **0 flips at all 21 positions**, one clean transition at y=230 |
| 40 bursts of scroll-across-threshold + forced bar reflow (`fontSize` toggle, driving `ResizeObserver` into the same frame as the IO callback), 28.3s | **19 flips = 0.7/s**, i.e. one per crossing; no runaway |

r6's defect was 60 flips/second on a stationary page. Nothing resembling it survives. The
termination argument in the comment — `pin` returns early when the class state is unchanged — is
the thing doing the work, and `--mutate` entry 98 kills its removal.

**A page that loads already scrolled past the bar is correct.** Fresh load at 320×568 with scroll
restored to 1800: `chrome chrome-pinned`, `--chrome-h` **132.2109375px** (the in-flow value, which
is scroll-invariant because `tailPx` is a *difference* of two viewport-relative bottoms), theme
button 8.20→37.83 and schemer 99.05→122.82 both on screen, **0 stationary flips in 1s**.

**`_own_id` has no fifth member — I looked for one against Chromium, not by reading.** 15 probes,
scanner `ids.count()` vs Chromium `getElementById(...).tagName` on the same markup:

| probe | Chromium | scanner agrees |
|---|---|---|
| `<svg id=X>` / `<svg><rect id=X>` / `<math id=X>` | `svg` / `rect` / `math` | ✔ ✔ ✔ |
| self-closed `<style id=X/>` / `<template id=X/>` / `<script id=X/>` | `STYLE` / `TEMPLATE` / `SCRIPT` | ✔ ✔ ✔ |
| `<style id=X id=other>` / `<style id=other id=X>` | `STYLE` / `null` (first wins) | ✔ ✔ |
| `<textarea>` / `<title>` / `<iframe>` contents | `null` / `null` / `null` | ✔ ✔ ✔ |
| `<template>` / `<noscript>` contents | `null` / `null` | ✔ ✔ |
| `<style id=X>` / `<script id=X>` own id | `STYLE` / `SCRIPT` | ✔ ✔ |

15 for 15. The four shielding branches are the whole population in this direction, and the inverse
direction (contents the scanner records that a browser makes text — `textarea`, `title`, `iframe`)
is already correct, because `html.parser` treats them as raw text too. The class fix is sound; I
could not break it.

**The `_interactive` shapes the brief named, other than H2.** An unclosed `<a>` before the title
(prepends — correct, Chromium puts the `h1` inside the anchor); a stray `</a>` with no opener
(guarded by `and self._interactive`, no underflow, prepends); `<label>` inside `<label>`;
`<a>` inside `<button>`; `<svg><a>` wrapping the title; a link that closes before the heading
(inserts after `</h1>` — the discriminating case holds); `</a>` inside a live `<script>` (never
reaches `handle_endtag`, CDATA). All correct.

**Other repo gates on the tip:** `check-selftest-counts.py` rc=0 ("53 script(s) declare a count,
every one verified by running it" — so the 214 is enforced, not asserted), `check-docs.py` rc=0,
`check-ratchet-contract.py` rc=0, `check-dashboard-entry.py` rc=0. `check-review-rounds.py` was
rc=1 at the tip and is rc=0 with this document filed (M5).

---

## Verdict

**NOT CONVERGED.**

Reason: this is the **seventh consecutive round in which the previous round's fix produced the
next finding, in `scripts/page_chrome.py`**, and both High findings are that shape exactly —
H1 is r7 MEDIUM 3's own defect surviving one `.chrome` deeper than the fix reached, H2 is r7
MEDIUM 4's own defect reachable again through a counter the same commit added without the shield
guard its own r4 comment demands. Neither required adversarial markup; both are browser-verified
on pages `brief-compose.py` accepts.

The fold's quality is not the issue — the suites, the harness, the exact-expression work and the
termination argument all hold under hostile measurement, and the `_own_id` class fix survived
fifteen probes against Chromium. The issue is structural and it is the one the r6 coordinator note
already named: **a selection rule, a reservation and a shield rule that are each one level away
from the thing they are about.** `querySelectorAll('.chrome-slot')` asks about containers when the
question is about bars; `--chrome-h` is one global for a selector that matches N slots; the
interactive counter guards its increment and not its decrement. Patching each instance is what has
produced seven rounds.

The thrashing verdict stands and strengthens. Phase 6 is armed and unconvened; convening it before
an eighth fold is, on this evidence, the cheaper path — and the question it should answer is not
"are these three bugs fixed" but "why does every rule in this file get written about the container
instead of the subject".
