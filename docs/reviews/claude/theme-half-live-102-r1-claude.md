# Adversarial review — backlog #102, "refuse a half-live theme toggle at compose time" (r1, Claude)

## PROOF OF SUBJECT

The working tree changed **during** this review (`scripts/brief-compose.py` mtime `2026-09-10
06:08:36`, while I was mid-run), so every finding below was re-measured against the **committed**
subject extracted with `git archive 0670e2f8` into a scratch directory outside the repo:

```
$ git cat-file -p 0670e2f8:scripts/brief-compose.py | shasum -a 256
0bd8da390cc461efc0e2bd1cc10b7a8715d47bce3ada28d793257061730df398  -
$ shasum -a 256 <scratch>/subject/scripts/brief-compose.py
0bd8da390cc461efc0e2bd1cc10b7a8715d47bce3ada28d793257061730df398
```

All line numbers are `scripts/brief-compose.py` **at 0670e2f8**.

> **Note on the concurrent edit, which I did NOT review.** The dirty working tree adds
> `strip_css_comments()`, `vars_read_anywhere()`, `_refusal_for()`, `_raises_exit()` (+125/−7). By
> inspection of names alone it appears to address F4b (comments) and F1/F2/F3 (fallback reads). It
> does **not** appear to touch F5 (untested conditional), F6 (`head` vs `content` corpus), F9 (no
> CI step / no mutation entry), or F11. Those findings should be checked against whatever is
> finally committed. This review's verdict is on `0670e2f8`.

Method: every claim below was produced by **executing** the functions on a constructed input, not
by reading the regex.

---

## F1 — BLOCKING. `referenced_vars` ignores `var(--x, fallback)`, which is exactly how the measured defect read its token. The guard composes its own 1.02:1 page.

**file:line** — `scripts/brief-compose.py:125-127` (the helper), `:236` (the use).

```python
def referenced_vars(css: str) -> set[str]:
    """Custom properties the CSS reads with NO inline fallback — `var(--x)`, not `var(--x, y)`."""
    return {m.group(1) for m in re.finditer(r"var\(\s*(--[\w-]+)\s*\)", css)}
```

`assert_theme_complete:236` narrows to "tokens the page READS" with this helper:

```python
    read = referenced_vars(fragment_css + "\n" + also_read)
```

That semantic is **correct for `assert_shimmed`** (a `var()` with a fallback still resolves, so it
is not an orphan) and **inverted for this rule**. The question here is not *does the name resolve*
but *does the token get a LIGHT value*. A fallback makes no difference to that, and `page_chrome`
already says so in its own comment at `scripts/page_chrome.py:130-137`:

> `A var(--card, transparent) fallback could never have saved it: the shim DEFINES --card, so the
> fallback never fires.`

The shim defines all 11 tokens in the dark media query, so for every one of them the fallback is
dead code — and the guard treats the token as unread.

**Trigger input** (the exact shape of backlog #79/#80: light ink on the shim's dark `--card`):

```html
<title>x</title><style>
:root[data-theme="dark"]{--ink:#eceaf0;--bg:#16151a}
:root[data-theme="light"]{--ink:#151b23;--bg:#ffffff}
body{color:var(--ink);background:var(--bg)}
.card{background:var(--card,#ffffff);color:var(--ink)}
</style><!-- + page_chrome.theme_control() + chrome_script() -->
<div class="card">every word of the brief lives in here</div>
```

**Observed:**

```
COMPOSED OK — guard did NOT fire
shim dark --card = #1d1c22
light-mode .card text #151b23 on shim-dark --card #1d1c22 -> 1.02:1
```

**Expected:** refused. `--card` is supplied DARK by the shim, is READ by the page, and has no light
value — all three conditions the docstring names are met. The docstring's own worked example is
`.c{background:var(--card)}`; add four characters of fallback and the rule goes blind.

**What the reader sees:** the 1.03:1 page the row was filed for, one hundredth of a ratio away,
past a green guard.

---

## F2 — BLOCKING. `page_chrome.chrome_css()` contributes **zero** tokens to `also_read`. The chrome bar's own tokens can never be required.

**file:line** — `scripts/brief-compose.py:361` (`compose`), `scripts/page_chrome.py:114-152`.

```python
    assert_theme_complete(head, live_control, css + "\n" + page_chrome.chrome_css())
```

Every single `var()` in `chrome_css()` carries a fallback, by that module's deliberate design
(`page_chrome.py:120-122`: *"Every fallback is `currentColor` or `transparent`, never a hex"*):

```
var(--ink-soft,currentColor)   var(--rule,currentColor)
var(--ink,inherit)             var(--structural,currentColor)
```

**Observed:**

```
>>> referenced_vars(page_chrome.chrome_css())
set()
```

The chrome half of the third argument is a **no-op**. This is not a corner case — the chrome bar is
the component backlog #79/#80 was filed about, and `--ink-soft` is the token #80 retuned.

**Trigger input:** a fragment with both `data-theme` palettes whose light palette omits
`--ink-soft` (a very ordinary omission — the shim defines it, most fragments do not).

**Observed:**

```
page with NO light --ink-soft: COMPOSED OK; chrome bar present: True
light mode: chrome label = shim dark --ink-soft #c8c5cf on page --bg #ffffff -> 1.70:1 (AA needs 4.5)
```

**Expected:** refused. The composer knowingly appends a bar that reads `--ink-soft`; the guard is
handed that bar's CSS precisely so those tokens count; it extracts nothing from it.

**Mutation confirmation** — the argument is not merely weak, it is dead in the self-test too:

| mutation | result |
|---|---|
| M1 `assert_theme_complete(head, live_control, "")` — drop the whole third argument | **53/53 passed** |
| M4 `read = referenced_vars(fragment_css)` — stop using `also_read` at all | **53/53 passed** |

(The tray half of `also_read` *does* carry weight on a live run — the real tray in
`~/explainers/dashboard.html` reads `--bg --card --defect --ink --rule --structure` with no
fallback. But the self-test's `css` fixture is `#tray{a:1}` etc., which reads nothing, so neither
half is exercised by any case.)

---

## F3 — HIGH. `SHIM`'s own no-fallback reads are absent from `also_read`, so `--bg` is required only when the fragment happens to name it — although every composed page reads it.

**file:line** — `scripts/brief-compose.py:104` (in `SHIM`), `:361` (the call).

```css
  :where(html, body) { background: var(--bg); color: var(--fg); }
```

`SHIM` is concatenated into every page, so **every** composed page reads `var(--bg)` with no
fallback. `also_read` is `css + "\n" + page_chrome.chrome_css()` — `SHIM` is not in it.

**Observed:**

```
SHIM's own no-fallback reads: ['--bg', '--fg']   ...not passed to assert_theme_complete
```

**Trigger input:** a fragment that relies on the shim's paint rule (the documented, intended way —
see the 2026-08-24 note at `:98-104`) and whose light palette omits `--bg`:

```html
<style>:root[data-theme="dark"]{--ink:#eee;--card:#111}
:root[data-theme="light"]{--ink:#111;--card:#fff}
.c{background:var(--card);color:var(--ink)}</style> + control
```

**Observed:**

```
page relying on SHIM's paint rule, light palette MISSING --bg: COMPOSED OK
   shim paint rule present in doc: True
   body text #111 on #16151a -> 1.04:1
```

**Expected:** refused — this is the headline defect (`--bg`, body text, ~1.03:1) reproduced through
the shim's own rule.

---

## F4 — HIGH. `light_palette_tokens` credits a `:root` nested inside `@media (prefers-color-scheme: dark)` as **light** coverage. Every generator in this repo writes exactly that block.

**file:line** — `scripts/brief-compose.py:176-179`.

```python
    for m in re.finditer(r':root(\[data-theme="light"\])?\s*\{([^}]*)\}', fragment_css):
```

The pattern is unanchored and has no notion of enclosing context, so a `:root` inside a dark media
query matches the optional-group-absent arm — the arm the docstring justifies as *"plain `:root`
counts too — (0,1,0) also beats the shim's `html` (0,0,1)"*. That reasoning is sound for a
top-level `:root` and **false** for one wrapped in `@media (prefers-color-scheme: dark)`, which is
not in force in light mode at all.

**Observed:**

```
>>> light_palette_tokens('@media (prefers-color-scheme:dark){:root{--card:#111;--ink:#eee}}')
['--card', '--ink']
```

This is not hypothetical shaping — it is the literal house style of every page that composes
through this file:

- `scripts/gen-goals-page.py:234` — `@media (prefers-color-scheme:dark){:root{--bg:#14151a;--card:#1c1e25;…}}`
- `scripts/gen-backlog-page.py:1137` — same
- `scripts/gen-dashboard.py:1104` — same

**Trigger input** — `--card` declared *only* in the dark media query, so no light value exists
anywhere:

```html
<style>@media (prefers-color-scheme:dark){:root{--card:#1c1e25}}
:root[data-theme="dark"]{--ink:#eee;--bg:#111;--card:#1c1e25}
:root[data-theme="light"]{--ink:#151b23;--bg:#fff}
body{color:var(--ink);background:var(--bg)}.card{background:var(--card);color:var(--ink)}</style> + control
```

**Observed:** `light_palette_tokens credits --card? True` → `COMPOSED OK — guard did NOT fire`.

**Expected:** refused. On the three real generators this is currently **latent** (each also emits a
`:root[data-theme="light"]` covering the same names), so no page is broken today — but the guard is
crediting the wrong block, and the moment one generator adds a token to its OS-dark block without
adding it to the light one, the guard stays green on the exact defect it was written for.

### F4b — same regex, same severity class: a `:root` inside a **CSS comment** is credited.

```
>>> light_palette_tokens('/* :root{--card:#fff} */')
['--card']
```

`check-theme-token-coverage.py`'s own self-test already pins *"a bare mention of a token name does
not count as a declaration"*; this new implementation of the neighbouring rule does not hold that
line. A commented-out palette — the normal way an author parks one — reads as coverage.

---

## F5 — HIGH. The `live_control` conditional, the half the docstring calls "CONDITIONAL ON A LIVE CONTROL, deliberately", has **no test coverage at all**. Five mutations survive.

**file:line** — `scripts/brief-compose.py:234-235` and `:358-360`.

Control: `python3 scripts/brief-compose.py --self-test` → `53/53 passed`.

| # | mutation | result |
|---|---|---|
| M0 | **delete `if not live_control: return` entirely** (`:234-235`) | **53/53 passed** |
| M1 | `assert_theme_complete(head, live_control, "")` | **53/53 passed** |
| M4 | `read = referenced_vars(fragment_css)` | **53/53 passed** |
| M6 | `live_control = False or not page_chrome.missing_palettes(…)` — drop the `has_control` route | **53/53 passed** |
| M7 | `live_control = page_chrome.has_control(content) or False and …` — drop the `missing_palettes` route | **53/53 passed** |
| — | M2 (drop the unscoped `:root` arm) | 52/53 — killed |
| — | M3 (credit any `data-theme` palette) | 52/53 — killed |
| — | M5 (refusal stops naming the tokens) | 52/53 — killed |

M0 is the significant one: **the entire conditional can be deleted and the suite stays green.** The
`compose()` comment at `:358-360` claims *"Both routes reach the same reader, so both are checked"* —
M6 and M7 show neither route is checked, because every `_frag_with_control` fixture satisfies both
simultaneously and the one control-less fixture satisfies neither.

There is no fixture at all for the route the comment says the composer actually takes (case 2 of
`chrome_for`: **palettes present, no button**, composer adds one). I constructed it by hand and it
behaves correctly — but nothing in the suite would notice if it stopped.

---

## F6 — HIGH. `live_control` reads `content`; the coverage check reads `head`. The two corpora disagree, producing both a false positive and false negatives.

**file:line** — `scripts/brief-compose.py:353` (`head, body = content.split("</style>", 1)`), `:358-361`.

```python
    live_control = page_chrome.has_control(content) or not page_chrome.missing_palettes(
        content + page_chrome.theme_control())
    assert_theme_complete(head, live_control, css + "\n" + page_chrome.chrome_css())
```

`live_control` is decided over the **whole fragment**; `fragment_css` is only what precedes the
**first** `</style>`.

**F6a — FALSE POSITIVE. A complete light palette in a second `<style>` block is refused, with a
message naming tokens that are declared.**

Trigger:

```html
<title>x</title><style>:root[data-theme="dark"]{--ink:#eee;--bg:#111;--card:#111}
body{color:var(--ink);background:var(--bg)}.c{background:var(--card)}</style>
<style>:root[data-theme="light"]{--ink:#111;--bg:#fff;--card:#fff}</style> + control
```

Observed: `REFUSED -> --bg, --card, --ink`. The identical palette in **one** block composes fine.

What the author sees: *"Declare them in the fragment's `:root[data-theme="light"]` (or `:root`)"* —
which they have already done, for all three named tokens. This is the failure mode the docstring
itself warns against (*"a guard asking to be satisfied rather than a guard describing a defect"*),
pointed the other way: the author's only route to green is to restructure correct CSS.

**F6b — FALSE NEGATIVE. A token read after the first `</style>` is invisible.**

- read from a second `<style>` block: `.c{background:var(--card)}` → `COMPOSED OK`
- read from an inline attribute: `<div style="background:var(--card)">` → `COMPOSED OK`

Both are CSS the browser applies and the guard never sees. Answering the brief's question directly:
`referenced_vars` is **not** run over the CSS the browser receives.

---

## F7 — MEDIUM. Prose that mentions both palette selectors flips `live_control` to true, and refuses a page that has no toggle with a message asserting it has a working one.

**file:line** — `scripts/brief-compose.py:358-359`; `scripts/page_chrome.py:60-68` (`missing_palettes` is a substring test).

**Trigger input** — a fragment with **no** control whose body discusses the selectors, i.e. exactly
a `/brief` or `/explain-diff` page *about backlog #102*:

```html
<title>x</title><style>body{color:var(--ink);background:var(--bg)}
.c{background:var(--card)}</style>
<p>this page explains :root[data-theme="light"] and :root[data-theme="dark"]</p>
```

**Observed:** `live_control = True` → `REFUSED -> --bg, --card, --ink`.

**Expected:** skipped. Per the docstring, a page that declares nothing gets an inert toggle and
stays readable; that is the page this rule *must not break*. `page_chrome.has_control` is
deliberately keyed on the button id rather than the word "theme" for precisely this reason
(`page_chrome.py:71-77`); the second arm of the predicate reintroduces the substring problem the
first arm was written to avoid.

---

## F8 — MEDIUM. The self-test case for the conditional passes for a reason other than the property it names — its fixture contains no `var()` at all.

**file:line** — `scripts/brief-compose.py:540-541`.

```python
    case("...but a partial palette on a page that gets NO control still composes",
         _composes('<title>x</title><style>:root{--ink:#111;--bg:#fff}</style><div>hi</div>'))
```

```
>>> referenced_vars('<title>x</title><style>:root{--ink:#111;--bg:#fff}')
set()
```

Direct check of what the case discriminates:

```
live_control=False: PASSES
live_control=True:  PASSES
```

It cannot distinguish the branch it names. This is the identical trap the author flagged eleven
lines earlier at `:526-528` — *"a fragment that declares a palette and reads nothing is correctly
ignored — and a fixture like that would pass while proving the guard cannot fire"* — and then built
into this case. It is also the mechanism behind M0 in F5: this is the only case that touches the
conditional, and it is vacuous.

**Fix shape:** give the fixture the same `_reads` block the other fixtures use, so that removing
the conditional makes it fail.

---

## F9 — MEDIUM. A new guard shipped with no CI step, no mutation-manifest entry, and outside `check-ratchet-contract.py`'s population.

- `.github/workflows/ci.yml` runs `python3 scripts/page_chrome.py --self-test` (`:311-312`) and
  **nothing** for `brief-compose.py`. Grep for `brief-compose` in `ci.yml`: no match.
- No file in `scripts/mutations/*.json` (34 manifests, 30 files covered) names
  `scripts/brief-compose.py`. `check-plan-code.py --mutate .` therefore cannot see any of this.
- `check-ratchet-contract.py` discovers 30 guards by the `check-*.py` filename convention;
  `brief-compose.py` now carries a real guard and is not among them.

That is why the five mutations in F5 survive silently: this file is outside every mechanism the
project uses to keep a guard load-bearing. `AGENTS.md`/`dev-process.md`'s ratchet row for
`check-ratchet-contract.py` records the same class of miss ("the population is the FILESYSTEM;
CI-step discovery saw 14 of 24").

---

## F10 — LOW. `shim_dark_tokens("")` answers confidently about a **different** subject instead of reporting CANNOT RUN.

**file:line** — `scripts/brief-compose.py:149`.

```python
    src = shim or SHIM
```

```
>>> shim_dark_tokens("")            # an empty shim
['--bg','--card','--defect','--good','--ink','--ink-faint','--ink-soft','--rule',
 '--structure','--structure-bg','--structure-br']     # 11 tokens, from the real SHIM
>>> shim_dark_tokens(":root{--a:1}")  # a non-empty shim with no dark block
CANNOT RUN — the OS-dark shim block was not found in SHIM
```

A caller handing this an empty shim — a stripped fixture, an unread file, a failed extraction —
gets a green, specific, wrong answer. The function has a CANNOT-RUN path and routes the emptiest
input away from it. `""` is a *falsy subject*, not *no subject supplied*; use a `None` default.

No self-test case exercises either branch of `:150-154`.

---

## F11 — LOW. `shim_dark_tokens`'s `(.*?)\}` silently shrinks its subject if the media query ever gains a second selector.

**file:line** — `scripts/brief-compose.py:151`.

Answering the brief's question directly: on the **current** `SHIM` the non-greedy `(.*?)\}` stops at
the correct brace — the one closing `html { … }` — so it reads the whole block and returns 11
tokens. It is right today. The failure is on edit:

```
>>> shim_dark_tokens("@media (prefers-color-scheme: dark) {\n"
...                  "  html { --bg:#000; --ink:#fff; }\n  body { --card:#111; }\n}")
['--bg', '--ink']          # --card silently dropped, no CANNOT RUN
>>> shim_dark_tokens("@media (prefers-color-scheme: dark) {\n html { --a:1; background:url(x{y}); --b:2; }\n}")
['--a']                    # --b silently dropped
```

The docstring's stated design goal is *"Read, never listed… the shim is edited far more often than
a guard is re-read"* — but the read narrows silently under exactly the edit it anticipates. The
guard would keep passing over a token it no longer knows about, which is indistinguishable from the
token being covered.

---

## F12 — LOW. `assert_theme_complete` runs before `assert_wired`, so an unwired control gets a message asserting the toggle works.

**file:line** — `scripts/brief-compose.py:361` runs before `:362` → `chrome_for` → `page_chrome.assert_wired`.

**Trigger:** a fragment with the button and **no** palettes at all — `assert_wired`'s exact subject.

**Observed first line of the refusal:**

```
brief-compose: this page has a WORKING theme toggle, but its light palette does not cover
every token the OS-dark shim supplies:
```

**Expected:** `assert_wired`'s message — *"the theme control is on the page but
`:root[data-theme="dark"]`, `:root[data-theme="light"]` is not defined, so pressing it would change
an attribute nothing styles."* The page's toggle is not working; it is unwired, which is a different
defect with a different fix. Moving the `assert_theme_complete` call after `chrome_for` resolves it.

---

## Summary

| Severity | Count | Findings |
|---|---|---|
| Blocking | 2 | F1, F2 |
| High | 4 | F3, F4 (+F4b), F5, F6 |
| Medium | 3 | F7, F8, F9 |
| Low | 3 | F10, F11, F12 |

The central problem is F1/F2/F3: **the "tokens the page READS" narrowing is implemented with a
helper whose definition of "reads" is the inverse of what this rule needs.** A fallback is
irrelevant to whether a token gets a light value — `page_chrome.py:130-137` already establishes
that in writing — yet `referenced_vars` treats a fallback as sufficient. The consequence is not
theoretical: I composed the 1.02:1 page (F1), the 1.04:1 page (F3) and the 1.70:1 chrome label (F2)
straight through a green guard, all three being the exact defect class the row was filed for.

F5 explains why none of this was caught: the conditional and the `also_read` argument survive
deletion with 53/53 green, the one case covering the conditional is vacuous (F8), and the file sits
outside CI, the mutation manifest, and the ratchet contract (F9).

The rule's shape is right and its narrowing is well-argued. Its implementation reads a smaller CSS
corpus than the browser does (F6), credits blocks that are not in force in light mode (F4/F4b), and
misses the reads that matter most (F1/F2/F3).

VERDICT: NOT CONVERGED
