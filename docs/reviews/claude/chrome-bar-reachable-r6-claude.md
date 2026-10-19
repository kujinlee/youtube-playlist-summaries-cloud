# chrome-bar-reachable — round 6, CLAUDE half

Subject: the four commits on `chrome-bar-reachable`, with the attack concentrated on
`38e31fc6` ("Round 6, Codex half: fold the threshold defect and widen the bound"), which
Codex did not see. Reviewed in the worktree, no file modified.

## Reproduction of the branch's own numbers

| Claim | Reproduced |
|---|---|
| `page_chrome.py --self-test` 184/184 | ✅ 184/184 |
| `brief-compose.py --self-test` 143/143 | ✅ 143/143 |
| `check-plan-code.py --self-test` 178/178 | ✅ 178/178 |
| shipped harness, both whole manifests: 84 mutations, 84 killed, 84 attributed, 0 survivors | ✅ `OK — delivered scripts mutated: 2 file(s), 84 mutation(s), 84 killed, 84 attributed to the case each names, 0 survivor(s)` |

Scoped per the brief: `HARNESS_TREE` read with `ast` (7 paths), rsynced, all manifests but
`page_chrome.json` / `brief-compose.json` deleted, `EXPECTED_MUTATIONS` reduced to those two
keys (64 + 20 = 84), `--mutate .` inside the copy.

Browser measurements below were taken with the repository's own Playwright/Chromium
(`node_modules/playwright`), on pages produced by the branch's own code.

---

## BLOCKING — `sync`'s unpinned guard does not cover `arm()`, so the observer re-arms from a PINNED bar and the page flips forever. Codex finding 2 is reinstated by its own fix.

**`scripts/page_chrome.py:852-861`.** In scope — this is the pin mechanism, the branch's subject.

The delivered JavaScript is:

```js
var sync=function(){
  if(!bar.classList.contains('chrome-pinned'))
    document.documentElement.style.setProperty('--chrome-h',bar.getBoundingClientRect().height+'px');
  if(typeof arm==='function')arm();          // <-- OUTSIDE the guard
};
```

The `if` has no braces, so it governs exactly one statement: the `setProperty` call. `arm()`
runs in **both** states. The commit message and the comment at `:888-890` both assert the
opposite — *"`sync` runs only while UNPINNED, so the margin is always the one measured from
the bar in flow — and the rebuild terminates, because a rebuild can pin, pinning resizes the
bar, and the resulting `sync` returns early."* The delivered `sync` does not return early, and
that sentence is the whole termination argument.

What follows is a two-cycle. `tail()` (`:878-880`) is `slot.bottom − max(control.bottom)`,
clamped by `Math.max(0, …)`. While the bar is **pinned** it is `position:fixed;top:0`, so the
controls sit at the viewport top (~37px) while the slot is above the fold — `sb − m` is
negative and the clamp returns **0**. So:

* armed while **unpinned** → `rootMargin: -tail()` → inside the band the slot misses the
  shrunk root → `pin(true)`;
* pinning changes the bar's box → `ResizeObserver` → `sync` → `arm()` armed while **pinned**
  → `rootMargin: -0px` → the slot intersects the full viewport → `pin(false)`;
* unpinning changes the box back → `sync` → `arm()` → …

### Measured on a real generated page

`python3 scripts/gen-dashboard.py --out dash.html` (313 entries), Chromium 1280×900:

```
 y=170   slotBottom=-0.19  pinned=true   themeButtonBottom=37.56   classFlips/s=0
 y=165   slotBottom= 4.81  pinned=false  themeButtonBottom=-2.38   classFlips/s=60   <-- BUTTON OFF SCREEN
 y=160   slotBottom= 9.81  pinned=false  themeButtonBottom= 2.63   classFlips/s=0
```

At y=165, on a stationary page with no input, the `.chrome` element's class attribute changes
**60 times per second, indefinitely** — and the state it was sampled in is the unpinned one,
with the theme button at y=−2.38, i.e. **Codex finding 2's exact defect reproduced after the
fix for it**.

### Mechanism, instrumented

On a page built from `chrome_bar(textstyle=True)` + `chrome_css()` + `chrome_script()` at
320×568, wrapping `window.IntersectionObserver` to record every construction, scrolled to
y=150 and then left alone for one second:

```
total: 61 observers constructed in 1s
margins: "0px 0px 0px 0px"         (pinnedAtArm: true)
         "-41.15625px 0px 0px 0px" (pinnedAtArm: false)
         "0px 0px 0px 0px"         (pinnedAtArm: true)   … alternating
final:   pinned=false, themeBottom=-37.56, slotBottom=+34.19
```

The band is `0 < slot.bottom < tail`. Measured width: **~41px** at 320×568 (the bar wraps, so
`tail` spans the refresh control and the stamp, not just the padding), **~7px** at 1280×900.
Six identical runs at y=170 on the same page: 4 ended pinned, **2 ended with both controls
entirely off screen** (`themeBottom=-57.56`, `schemerBottom=-26.97`). The resting state is
whatever the last toggle of a non-terminating loop happens to leave.

### Which pages reach it, measured rather than assumed

The `ResizeObserver` only fires when the bar's **content-box** width differs between flow and
pinned — i.e. when the page's side gutter ≠ the bar's own `padding-inline:1rem`. Sweeping the
gutter on an otherwise identical page, 320×568, 15 scroll positions each:

```
gutter  0px: max flips/0.7s = 42  | button off screen 1/15
gutter  8px: max flips/0.7s = 42  | 1/15
gutter 12px: max flips/0.7s = 43  | 2/15
gutter 16px: max flips/0.7s =  0  | 0/15      <-- the ONLY silent value
gutter 20px: max flips/0.7s = 43  | 1/15
gutter 24px: max flips/0.7s = 42  | 1/15
gutter 32px: max flips/0.7s = 43  | 0/15
```

16px is silent because `320−32 = 288` on both sides of the transition, so the observer never
fires. That is why the real `2026-10-06` composed explainer is quiet — I swept it at 1px
granularity over a 60px range and found nothing — and it is a property of **that page's
container padding**, not of the mechanism. `gen-dashboard.py:1229` declares
`.shell{padding:32px 20px 80px}` and `gen-backlog-page` declares `padding:2.5rem 1.25rem 6rem`;
both are 20px, both in the oscillating set, and the dashboard measurement above is the direct
confirmation.

### Second manifestation, same root cause, NOT fixed by bracing `arm()`

**`scripts/page_chrome.py:897-898`** — the no-`IntersectionObserver` fallback calls `tail()`
on every scroll event regardless of pin state, so it reads the clamped-to-0 tail whenever the
bar is pinned. With `IntersectionObserver` deleted, 320×568:

```
 y=150  after scrolling there: pinned=true  schemerB=63.16 | after ONE more scroll event: pinned=false schemerB= -6.97
 y=160                         pinned=true  schemerB=63.16 |                              pinned=false schemerB=-16.97
 y=170                         pinned=true  schemerB=63.16 |                              pinned=false schemerB=-26.97
 y=180                         pinned=true  schemerB=63.16 |                              pinned=false schemerB=-36.97
```

Deterministic, alternating with each event — and browsers emit many scroll events per gesture.

I verified the obvious one-line repair (braces around the guard so `arm()` is unpinned-only):
it takes the gutter-20px page from 60 flips/s to **0** and holds the bar pinned with the
control on screen across the whole band — **and leaves the fallback above completely
unchanged**. So the root cause is not the missing braces as such: it is that `tail()` is only
meaningful while the bar is in flow, and two call sites evaluate it while pinned. Any fix that
does not state and enforce that precondition will leave one of the two.

### What the verification missed, and why

The commit records *"VERIFIED at the reviewer's exact repro: at y=231 the bar is now pinned
with the theme button at top 8.2 / bottom 37.83."* y=231 is deep inside the stable-pinned
region. The fix was verified at the one scroll position the defect it introduced cannot reach.

---

## HIGH — the comment strip was applied to the LAST arm of `assert_wired`; the arms the module calls load-bearing still read commented-out CSS as live

**`scripts/page_chrome.py:445` (fixed) vs `:1024` / `missing_palettes` at `:144-153`
(unfixed).** In scope by the fold's own widening argument.

The fold's justification is that *"a fragment author commenting out a selector while editing
CSS is an ordinary mistake inside this subject."* That argument does not stop at the pin rule.
`missing_palettes`, `missing_text_tokens`, `TEXT_ATTR not in page` and `missing_text_consumer`
are all substring tests over the **raw** page, and `bar_unreachable` is the only one that now
strips. The module's own ordering comment at `:1079-1082` says the pin arm asks whether the
control can be *found* and deliberately runs **last**, below the arms that ask whether it
*works*; the docstring at `:24-29` says `missing_palettes()` "is the load-bearing part of this
file, not the button".

Measured, same authoring mistake, one line up in the same stylesheet:

```
A  pin rule commented out              -> REFUSED      (the fold's own case)
B  dark palette commented out          -> ACCEPTED
C  BOTH palettes commented out         -> ACCEPTED     <-- ships a button that styles nothing
D  the whole stylesheet commented out  -> REFUSED      (only because arm A fires)
```

Input for C (a finished document; `LIGHT`/`DARK` are the suite's own palette literals):

```python
'<html><body><button id="chrome-theme">t</button>'
f'<style>/*{LIGHT}{DARK}*/.chrome-pinned{{position:fixed}}</style>'
f'<script>/*{CHROME_SCRIPT_MARK}*/</script></body></html>'
```

`assert_wired` returns cleanly. The page renders a theme button that sets `data-theme` and
nothing styles it — which is, verbatim, "the fail-silent this module must prevent" from the
module docstring. The r6 fold widened the bound to cover commented-out CSS and then fixed one
of five arms, the one it had itself ranked least severe.

---

## HIGH — `_strip_css_comments` is a second implementation of a rule this repo already owns, and it is specifically the implementation the owning module records as defective. It introduced a fail-open regression on the fragment path.

**`scripts/page_chrome.py:392-405`** vs **`scripts/brief-compose.py:250-303`**. In scope.

`brief-compose.strip_css_comments` is a one-pass scanner whose docstring says, in full:

> ⛔ ONE PASS, NOT THREE REGEXES — r2 found three separate defects that all reduce to "a regex
> over CSS does not know what a string is": … `--open:"/*"` … `--close:"*/"` let the naive
> `/\*.*?\*/` erase a REAL declaration between them, so a complete light palette was refused
> as incomplete (r2 Medium); comments carrying a `}` truncated the shim scan (r1 Low).

`page_chrome._strip_css_comments` is `re.sub(r"/\*.*?\*/", " ", page, flags=re.S)` — the naive
regex that sentence names, on the same corpus, 400 lines away, with the correct implementation
already imported into the same composition path. Its own docstring presents the bound as a
fresh, accepted trade-off ("a literal `/*` inside a quoted string or a script survives as a
comment start … A case below pins the one shape where it misreads") without mentioning that
the repository measured that bound as a defect two rounds ago and built the fix.

The module docstring at `:39-41` also lists *"comment-stripping regex"* as one of the five
instruments rounds 1-5 already superseded — three paragraphs above the paragraph announcing
its reintroduction.

### The measured regression

Fragment (seven of nine callers pass a fragment, per `:449-451`):

```python
'<button id="chrome-theme">t</button><style>'
'.a{content:"/*"}' + LIGHT + DARK + '.chrome-pinned{position:static}' + '/* note */'
f'</style><script>/*{CHROME_SCRIPT_MARK}*/</script>'
```

This is backlog #300's exact shape — a `.chrome-pinned` rule that exists and does not pin.

```
BEFORE the fold (38e31fc6^): bar_unreachable = True  -> REFUSED
AFTER  the fold (38e31fc6) : bar_unreachable = False -> ACCEPTED
```

The stray `/*` in a CSS value string pairs with the trailing `*/`, the naive strip erases the
real rule, `rules` becomes empty, and the fragment branch's `if not rules: return False`
exemption fires. `brief-compose.strip_css_comments` handles the same input correctly (I ran
both over it). The fold made the guard strictly weaker on its dominant caller.

### Corpus

12 of 81 live explainer pages under `docs/explainers/` carry unbalanced `/*` / `*/`. On the
real composed `2026-10-07-topic-retrieval-fixed-gap-open` page the naive strip deletes
**12,451 of 40,476 characters** before the pin match. **No live page's verdict flips today** —
the shim's own comments happen to close first, so the chrome rules survive by position. That is
an accident of ordering, not a property, and it is the same kind of accident as the 16px gutter
in the Blocking above.

---

## HIGH — the three cases written for the threshold fix assert substrings something else in the file supplies, so the fix has no falsifier. This is the fold's own reported defect, re-created in the cases written for the same fix.

**`scripts/page_chrome.py:1540-1551`.** In scope.

Severance A — make `tail()` identically zero, which is the pre-fix behaviour exactly:

```
"for(var i=0;i<ctls.length;i++){var b=ctls[i].getBoundingClientRect().bottom;"
→ "for(var i=0;i<ctls.length;i++){var b=slot.getBoundingClientRect().bottom;"
```

`python3 scripts/page_chrome.py --self-test` → **184/184 passed**. Browser-verified that the
severed build reproduces Codex finding 2 in full, at 320×568:

```
 y=150 pinned=false schemerB= -6.97     y=170 pinned=false schemerB=-26.97
 y=160 pinned=false schemerB=-16.97     y=180 pinned=false schemerB=-36.97
```

The surviving assertion is `"getBoundingClientRect().bottom" in chrome_script()` at `:1547`,
and that substring now occurs **twice** — the severance leaves the slot's copy in place. The
case's name is *"the tail is MEASURED from the live control boxes"*; the control measurement is
exactly what the severance deletes, and the case cannot see it.

Severance B — `"if(b>m)m=b;…"` → `"m=b;…"`, i.e. the **last** control rather than the lowest,
which is the property the case name states ("the controls may end on different lines"):
**184/184 passed**.

This is the shape the commit message reports catching and fixing in `a bar with NO control is
never pinned`. The same fix re-created it two cases later. Programmatic check of every
`"literal" in <producer>()` assertion in `page_chrome.py` against the producer's actual output
finds 5 whose occurrence count is not 1; `:1547` is the one where the duplicate is load-bearing
(the `:1517-1519` pair is still defended by its unique `addEventListener('scroll'` half).

Two manifest entries compound it:

* `the tail is derived from one control instead of the lowest` edits `ctls` to `[]`. That
  exercises the `m===-Infinity?0:` branch — which is unreachable on the delivered path, since
  the enclosing block is guarded by `bar.querySelector('#chrome-theme,#schemer')` — and never
  tests "one instead of the lowest". It is killed purely by the disappearance of a substring.
* `the height is re-measured while PINNED, so the reserve and the observer chase each other`
  claims coverage for precisely the feedback loop that the Blocking above measures as live.

---

## MEDIUM — the r1 premise the composer's decline rests on is stale, and the open High is being costed against it

**`scripts/brief-compose.py:818-820`.** In scope.

> `chrome_script` binds `getElementById('schemer')`, which returns the FIRST match: the
> fragment's own inline copy. The one appended here would therefore be the DEAD one.

That was true while the bar was appended to the end of `<body>`. The resting place moved to
under the `<h1>` at `de48f095` (2026-10-18). Measured on the real composed page
(`brief-compose.py --content docs/explainers/2026-10-06-brief-dev-process-speed.fragment.html`):

```
<h1> at 16327 | class="chrome-slot" at 16388 | the fragment's id="schemer" at 17041
```

The composer's copy would now be **first**, i.e. the live one; the hand-authored copy would be
the dead one. The duplicate-id refusal in `assert_wired` is unaffected and still correct, but
the comment's stated reason is now backwards.

**On the fork's honesty (brief item 5):** I think the framing is honest. The four options are a
fair enumeration, `#schemer` on these fragments is hand-authored and hand-styled so a runtime
DOM move really does change rendering and reading order, and I found no mechanical fix being
declined. But "markup surgery on hand-authored fragments" is costed against the stale premise
above, and should be re-costed: with the bar now first in document order, letting the composer
emit the switcher and removing the fragment's own copy no longer has the "the new one is dead"
objection it had at r1.

---

## LOW — the strip's space is argued in one direction and measured in neither other

**`scripts/page_chrome.py:1859-1863`** pins that a comment becomes a space so the strip "cannot
weld a selector into existence". The inverse is not pinned, and it defeats the identity case at
`:1611`:

```
.chrome-pinned/*x*/-host{position:fixed}   -> rules=['position:fixed']  bar_unreachable=False  (ACCEPTED)
.chrome-pinned-host{position:fixed}        -> rules=[]                  bar_unreachable=True   (refused, correct)
```

The space satisfies `(?![\w-])`, so the strip *un-welds* `-host` into a matching selector that
does not pin the bar in a browser. Adversarial rather than an editing mistake, so Low — but the
space is now load-bearing in two directions and only one has a case.

---

## Bound and scope notes

* Everything above is inside the subject declared in the module docstring (`:31-46`) and
  restated at `assert_wired` (`:1008-1016`). Nothing here is a claim about adversarial markup.
  The two strip findings are inside the subject **by the fold's own widening argument**, which
  is the argument that commented-out authored CSS is an ordinary mistake.
* Codex finding 1 is not re-reported.
* NOT RUN: real device, print, zoom, font-load reflow, late images, runtime DOM injection. The
  `tail`-while-pinned class is likely to have more members than the two call sites I found;
  I enumerated by reading `chrome_script` rather than by instrumenting every entry into `tail`.
* The mutation harness reproduces 84/84/84/0 and is working correctly. It cannot see any of the
  Blocking: no case in either suite runs a browser, and the three cases that name the threshold
  behaviour are the ones severance A and B show are lexical.

---

## NOT CONVERGED

The round-6 fold introduced a non-terminating render loop on a production generator's page and
reinstated, in the same band, the defect it was written to fix. It fixed the comment-stripping
class at one of five arms and, in doing so, shipped a known-defective second implementation of
a rule the repository already owns, which made the guard strictly weaker on seven of its nine
callers. And the three cases written to defend the fix are lexical: the pre-fix behaviour can
be restored with the suite at 184/184.

This is round 6 with findings caused by round 5's and round 6's own fixes, in
`scripts/page_chrome.py`, for the sixth consecutive round. The r5 coordinator note's arming
condition — two consecutive rounds whose findings came from the previous round's fix, in one
component — is met several times over. ⛔ The evidence this half adds is that the thrashing is
no longer confined to the text-level scan: `chrome_script` is now producing its own generation
of fix-caused defects, in a layer where no case in either suite can observe behaviour at all.
The architecture review armed at r3 should be convened before a seventh patch, and the question
put to it should be the one the r5 note already framed — whether the reachability claim belongs
in a rendering test — now with the measurement that the script half has the same problem as the
scan half.
