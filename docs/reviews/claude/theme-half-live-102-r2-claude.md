# Adversarial review r2 — backlog #102, the r1 fold (Claude)

## PROOF OF SUBJECT

Pinned outside the repo with `git archive d4b54cfa | tar -x -C <scratch>/r2`, verified:

```
$ git cat-file -p d4b54cfa:scripts/brief-compose.py | shasum -a 256
a1d76ab41dd377bfb457b5b6258f02081ebf236302c4a34b122cd15d965d7c80  -
$ shasum -a 256 <scratch>/r2/scripts/brief-compose.py
a1d76ab41dd377bfb457b5b6258f02081ebf236302c4a34b122cd15d965d7c80
$ git log --oneline -1 d4b54cfa
d4b54cfa Fold r1: the review found 17 defects, 4 of them Blocking, in a change I called done
$ python3 scripts/brief-compose.py --self-test
62/62 passed
```

Every measurement below was executed against that pinned tree. The working tree was not reviewed.
Line numbers are `scripts/brief-compose.py` at `d4b54cfa`.

### What the fold fixed, checked by mutation rather than by reading

| r1 | Fixed? | Protected by a case? |
|---|---|---|
| F1 fallback reads | yes | **yes** — `M-c` (restore `\s*\)`) → 60/62 |
| F2 `chrome_css` in `also_read` | yes | **no** — `M-e` → 62/62 |
| F3 `SHIM` in `also_read` | yes | **no** — `M-d` → 62/62 |
| F4 `:root` in a dark media query | yes at depth 1 | **no** — `M-b` → 62/62; and **fails at depth 2** (R2-6) |
| F4b comment-carried braces | yes | yes — `M-g` → suite crashes red |
| F5 the conditional | yes | yes — `M-h` (gut the guard) → 55/62 |
| F6 corpus `head` → `content` | yes | **no** — `M-a` → 62/62; and **caused R2-4, R2-5** |
| F7 prose flips `live_control` | **no** — reintroduced through `declares_light` (R2-5) | weaker form only |
| F8 vacuous no-control fixture | yes | yes |
| F9 CI step / mutation manifest | CI yes, **manifest no** | — |
| F10 `shim_dark_tokens("")` | yes | yes |
| F11 second selector in the shim block | **no** | — (R2-11) |
| F12 refusal ordering | **yes** — verified: a button with no palettes now gets `assert_wired`'s message first | — |

---

# R2-1 — BLOCKING. `declares_light` turns the guard **off** for a page with a fully wired, working toggle whose light palette uses plain CSS properties. 11 of 11 tokens uncovered, 1.02:1. This is also the counterexample to the deleted `has_control` arm.

**file:line** — `:378-380`.

```python
    declares_light = bool(light_palette_tokens(content))
    live_control = declares_light and not page_chrome.missing_palettes(
        content + page_chrome.theme_control())
```

`light_palette_tokens` counts **custom properties only** (`re.findall(r"(--[\w-]+)\s*:")`). A page
is free to express its themes in ordinary CSS properties — that is what `data-theme` palettes are
*for*. Such a page has `declares_light == False`, so `live_control` is False and the guard returns
at `:237` without looking at anything.

**Trigger input:**

```html
<title>x</title><style>
:root[data-theme="dark"]{background:#16151a;color:#eceaf0}
:root[data-theme="light"]{background:#ffffff;color:#151b23}
.card{background:var(--card);padding:1rem}
</style>
<!-- page_chrome.theme_control() + chrome_script() -->
<div class="card">every word of the brief lives in here</div>
```

**Observed:**

```
has_control=True  declares_light=False  missing_palettes=[]  -> live_control=False
COMPOSED OK — guard skipped.  bytes: 5954
page has a wired control: True | script bound: True
assert_wired: PASSES (the toggle really works)
shim dark --card = #1d1c22  (no light override anywhere)
.card text #151b23 (page light) on --card #1d1c22 (shim dark) -> 1.02:1
shim tokens with NO light value on this page: 11 of 11
```

**Expected:** refused. This is the *maximal* half-live toggle — not "some tokens keep dark values",
**all eleven** — and the guard is silent on exactly it. `assert_wired` passes, so nothing else
catches it either.

**This answers mandate item 4.** The comment at `:362-368` says:

> *⛔ THE `has_control` ARM WAS REMOVED, NOT TESTED … It could not change an outcome: a fragment
> carrying its own control AND both palettes already satisfies the arm below…*

The premise is that "carries both palettes" implies "`declares_light`". It does not: `missing_palettes`
is a **substring** test for `:root[data-theme="light"]`, while `declares_light` requires that block to
declare at least one `--token`. The fragment above satisfies the first and fails the second. With the
`has_control` arm still present, `live_control` would be `True` and the page refused.

The arm was deleted on an argument, and `M6`'s survival in r1 was read as evidence the arm was inert.
It was evidence the **suite** could not see the arm — the recorded distinction *"mutation testing
proves load-bearing, never complete"*.

**Fix shape:** restore the `has_control` arm, or gate on `missing_palettes` alone and let
`light_palette_tokens` answer only the coverage question. The two predicates must not disagree about
what "has a light palette" means.

---

# R2-2 — BLOCKING. The `@media` stripper eats forward from **prose**. One sentence deletes the page's entire light palette from the scan and silently disables the guard.

**file:line** — `:187`.

```python
    css = re.sub(r"@media[^{]*prefers-color-scheme[^{]*\{(?:[^{}]|\{[^{}]*\})*\}", " ", css, flags=re.S)
```

`[^{]*` crosses `}`, `<`, `>` and newlines. It only has to reach `prefers-color-scheme` and then the
**next `{` anywhere in the document** — and since F6 widened the corpus to the whole `content`, that
document now contains prose. The match then consumes the following rule block and deletes it.

**Decisive control/defect pair** — identical pages, partial light palette (missing `--card`), page
reads `var(--card)`; the *only* difference is one sentence:

```
  CONTROL: no prose
     REFUSED: --card   <-- guard works
  DEFECT : + one sentence of prose
     COMPOSED  <-- the half-live page SHIPS
```

The sentence:

```html
<p>The shim sits at <code>@media (prefers-color-scheme: dark)</code>.</p>
```

Effect on the scan, same page with a **complete** 11-token palette:

```
  no prose    : light_palette_tokens sees 11/11; declares_light=True
  prose first : light_palette_tokens sees  0/11; declares_light=False
```

11 tokens → 0. Via R2-1 that also flips `declares_light` off, so the guard does not merely lose
coverage — **it stops running**.

**Live on the real production page.** Running the stripper over the actual `/backlog` fragment:

```
REAL /backlog fragment — stripper matches: 4
  [0]    345 chars  '@media (prefers-color-scheme:dark){:root{ --ink:#e7e9ee; …'
  [1]    126 chars  '@media (prefers-color-scheme:dark){ .diff del{…'
  [2] 107485 chars  '@media (prefers-color-scheme: light)</code> counted as coverage although it cann…'
       …ends: 'SendMessage</code> to a <strong>named</strong> agent, and <code>{to: &quot;main&quot;}'
  [3]     44 chars  '@media (prefers-color-scheme: dark){html{…}}'

chars deleted from the light-palette scan: 108000
```

Match [2] is **107,485 characters** — it begins inside the prose of the backlog row describing *this
very fix* and runs to an unrelated row about `SendMessage`. The guard's own documentation, rendered
onto the page it guards, blinds it over 107KB.

That page survives today only by **position**: its palette sits before the prose. Any `:root` after
it is erased. This is the recorded failure *"a measurement is only as good as its CORPUS"* — the
subject is deleted before it is measured, and the result is indistinguishable from coverage.

**Fix shape:** run the stripper over extracted `<style>` contents, not the document; and anchor it so
`[^{]*` cannot cross a `}` or a `<`.

---

# R2-3 — BLOCKING (carried from r1, unfixed). Four of the five `⛔` cases remain vacuous, and four fixes revert with the suite green.

**file:line** — `:588-591` (`_c`) and the `⛔` cases at `:594-628`.

Re-measured at `d4b54cfa`. `_c(...)` asserts *refused*; **the control `_c()` with no feature under
test is already refused, with the same six tokens in the same order**:

```
THE CONTROL NOBODY RAN — `_c()` with NO feature under test:
    --card, --good, --ink-faint, --ink-soft, --rule, --structure

   fallback          : --card, --good, --ink-faint, --ink-soft, --rule, --structure
   2nd <style>       : --card, --good, --ink-faint, --ink-soft, --rule, --structure
   inline style=     : --card, --good, --ink-faint, --ink-soft, --rule, --structure
   @media coverage   : --card, --good, --ink-faint, --ink-soft, --rule, --structure
```

Cause unchanged: `_c`'s light palette is two tokens, and `SHIM` in `also_read` reads six others on
every page, so the fixture is refused before `inner`/`tail` is consulted.

**Mutation battery** (control `62/62 passed`):

| mutation | result |
|---|---|
| `M-a` revert corpus `content` → `head` (undoes r1 F6) | **62/62 passed** |
| `M-b` media-query stripper → no-op (undoes r1 F4) | **62/62 passed** |
| `M-d` drop `SHIM` from `also_read` (undoes r1 F3) | **62/62 passed** |
| `M-e` drop `chrome_css()` from `also_read` (undoes r1 F2) | **62/62 passed** |
| `M-c` restore fallback-blind matching | 60/62 — killed |
| `M-f` `declares_light = True` | 61/62 — killed |
| `M-h` gut `assert_theme_complete` | 55/62 — killed |

The new case at `:606-611` — *"a token read ONLY by the appended chrome/shim is still required"* —
was written for r1 F2/F8 and does real work, but it **cannot distinguish its two contributors**:
`SHIM` and `chrome_css()` both supply `--ink-soft`, so deleting either leaves the case green
(`M-d`, `M-e`). Its name claims coverage of both; it covers their union only.

**Fix shape** unchanged from r1: build each fixture from a light palette covering all 11 shim tokens
**except** the one under test, assert the bare variant **composes**, then assert the feature-carrying
variant is refused **and** that `_refusal_for` names exactly that token.

---

# R2-4 — HIGH. `vars_read_anywhere` is a raw substring scan over the whole document. Six routes make a page demand a token it never reads.

**file:line** — `:194-211`, `return {m.group(1) for m in re.finditer(r"var\(\s*(--[\w-]+)", strip_css_comments(css))}`.

Isolated control/defect pairs — identical pages, light palette complete except `--defect`; only the
appended tail differs:

```
   control, plain prose             : COMPOSES
   prose in a <code> element        : REFUSED: --defect
   inside a CSS string literal      : REFUSED: --defect      content:"var(--defect)"
   inside a JS string in a <script> : REFUSED: --defect      var s = 'var(--defect)';
   inside an HTML comment           : REFUSED: --defect      <!-- .a{color:var(--defect)} -->
   in a data: URI                   : REFUSED: --defect      src="data:text/plain,var(--defect)"
   read ONLY in the page's DARK block: REFUSED: --defect     @media(prefers-color-scheme:dark){…}
```

None of these is a read the browser performs in light mode:

- a `content:` string is text, never a resolved `var()`;
- a JS string is not CSS;
- **an HTML comment is not stripped** — `strip_css_comments` handles `/* */` only, and `<!-- -->` is
  the comment syntax that actually surrounds markup;
- a `data:` URI is opaque to CSS;
- a declaration inside the page's own `prefers-color-scheme: dark` block does not apply on the
  OS-dark + page-light path this guard is about — the same reasoning `light_palette_tokens` applies
  to coverage is not applied to reads.

This is r1 F7's failure mode arriving from the other side, exactly as the mandate anticipated. On the
real `/backlog` page the prose route is currently **redundant** (the tray reads the same tokens), so
it costs nothing there today — stated so the finding is not overclaimed:

```
REAL /backlog at d4b54cfa — demanded: ['--bg', '--defect', '--rule', '--structure']
   --structure  <- fragment BODY (prose), tray, SHIM
   shim tokens contributed ONLY by body prose: []
```

**Fix shape:** scan extracted `<style>` contents plus `style="…"` attribute values, and drop the
page's own `prefers-color-scheme` blocks from the read scan as they already are from the light scan.

---

# R2-5 — HIGH. r1 F7 is reintroduced through `declares_light`: a code sample showing a palette counts as a real palette, and the new case pins only the weaker form.

**file:line** — `:378`; case at `:597-602`.

The comment at `:369-377` states the fix:

> *⚠ `declares_light` is the gate, not a substring: `missing_palettes` is a substring test, so a page
> whose PROSE discusses `:root[data-theme="light"]` satisfied it (r1 F7).*

But `light_palette_tokens` also runs over the whole `content`, so it is a substring test with extra
steps — it just additionally requires a `{…}` after the selector, which any **code sample** has.

**Trigger** — a page with no button and no real palette, whose `<pre>` shows both palettes (an
explainer about backlog #102, the exact shape F7 was fixed to protect):

```html
<title>x</title><style>.c{background:var(--card);color:var(--ink)}</style>
<pre>:root[data-theme="light"]{--card:#fff}
:root[data-theme="dark"]{--card:#111}</pre>
<p>no toggle on this page at all</p>
```

```
declares_light=True missing_palettes=[] live_control=True
REFUSED: --bg, --good, --ink, --ink-faint, --ink-soft, --rule, --structure
```

— *"this page has a WORKING theme toggle"*, on a page with no button.

**The new case cannot see this**, because its fixture is a strictly weaker input:

```
shipped fixture  <p>explains :root[data-theme="light"] and ...</p> -> declares_light = False
realistic sample <pre>:root[data-theme="light"]{--card:#fff}</pre> -> declares_light = True
```

The shipped prose has no braces, so it is filtered by the `\{([^}]*)\}` requirement before
`declares_light` is consulted. The case passes; the class it names does not hold. This is the
recorded pattern *"the fixture used an input a DIFFERENT rule filters first"*.

---

# R2-6 — HIGH. The `@media` stripper handles one level of nesting. At two, r1 F4 returns unchanged.

**file:line** — `:187`; `(?:[^{}]|\{[^{}]*\})*` admits exactly one nested block.

```
>>> light_palette_tokens('@media (prefers-color-scheme: dark){@supports (display:grid){:root{--card:#111}}}')
['--card']
>>> # survives the strip untouched:
'@media (prefers-color-scheme: dark){@supports (display:grid){:root{--card:#111}}}'
```

`--card` is declared only in an **OS-dark** block and is credited as light coverage — r1 F4 verbatim,
one nesting level deeper. `@supports`, `@layer` and `@container` wrappers all reach it.

The docstring at `:176-181` states the design intent and then misses it:

> *Those blocks are removed before the scan rather than matched-and-skipped, because the brace
> arithmetic of "which `:root` is inside which media block" is the part a regex gets wrong.*

Correct diagnosis; the replacement is still brace arithmetic in a regex, just spelled differently. A
small brace-counting scan over the extracted stylesheet is the shape that closes both this and R2-2.

---

# R2-7 — HIGH (carried, unfixed). `/backlog` still fails the guard and ships without its Ask tray, exit 0.

Re-measured at `d4b54cfa` across all three generators:

```
  gen-goals-page:   OK (tray: 1)
  gen-backlog-page: DEGRADED — tray lost
      ⚠  WITHOUT the Ask tray — brief-compose.py could not lift one:
         brief-compose: this page has a WORKING theme toggle, but its light palette does not cover…
  gen-dashboard:    OK (tray: 1)
```

Demanded: `--bg, --defect, --rule, --structure` — all genuinely read by the lifted tray, none with a
light value on that page. The finding is not that the guard is wrong; it is that the only consequence
of being right is that a real page loses the feature `brief-compose.py` exists to guarantee
(*"FAIL LOUD, NEVER SILENT … A brief that renders without its Ask tray is the failure this script
exists to prevent"*), quietly, at exit 0.

---

# R2-8 — MEDIUM. An HTML-commented-out chrome block still draws the half-live diagnosis.

**file:line** — `:330` `if page_chrome.has_control(content):` — raw `content`, no comment stripping.

**Trigger:** both palettes declared for real; the entire chrome block wrapped in `<!-- -->`.

```
has_control(content) at chrome_for:330 = True
REFUSED: brief-compose: this page has a WORKING theme toggle, but its light palette does not cover…
```

The button and its script are inside an HTML comment, so the browser renders no control at all. r1's
Medium was fixed at the `live_control` site (which no longer calls `has_control`), leaving the
remaining call site with the original defect — the instance was fixed, not the class.

---

# R2-9 — MEDIUM (carried). The refusal's token list is on line 2; the production caller prints line 1.

**file:line** — `scripts/gen-backlog-page.py:2249`, unchanged at `d4b54cfa`:

```python
        print("   " + (composed.stderr.strip() or composed.stdout.strip() or "no output").splitlines()[0])
```

Line 1 names no tokens. Observed in the live run above: the operator is told the page lost its tray
and is not told which four tokens to declare — while `_refusal_text`'s docstring asserts the message
must name them.

---

# R2-10 — MEDIUM (carried). The narrowing is 8/11 vacuous while the docstring still describes it as live.

```
unconditionally demanded 8 of 11 -> --bg --card --good --ink --ink-faint --ink-soft --rule --structure
still narrowed:            3     -> --defect --structure-bg --structure-br
```

`SHIM` + `chrome_css()` read 8 of the shim's own 11 tokens, so "only tokens the page READS" is now
nearly "all of them". The `⛔ ONLY TOKENS THE PAGE ACTUALLY READS` paragraph and its `--structure-br`
anecdote apply to 3 tokens. The case pinning the narrowing removes `--structure-bg`, one of the 3
survivors, so it cannot see the collapse.

---

# R2-11 — LOW (carried, r1 F11). A second selector inside the shim's media block is still dropped silently.

```
>>> shim_dark_tokens("@media (prefers-color-scheme: dark) {\n html { --bg:#000; }\n body { --card:#111; }\n}")
['--bg']
```

Comments are stripped and an empty parse is CANNOT RUN — both landed. A *partial* parse is still
silent, and one token short is indistinguishable from one token covered.

---

# R2-12 — LOW (carried, r1 F9 half). CI step added; still no mutation-manifest entry.

`ci.yml` now runs `brief-compose.py --self-test` (3 references). But:

```
$ grep -l "brief-compose" scripts/mutations/*.json
still NO manifest names brief-compose.py
```

A green self-test is precisely what `M-a`/`M-b`/`M-d`/`M-e` return. `--mutate .` is the mechanism
that would have caught them.

---

## Summary

| Severity | Count | Findings |
|---|---|---|
| Blocking | 3 | R2-1, R2-2, R2-3 |
| High | 4 | R2-4, R2-5, R2-6, R2-7 |
| Medium | 3 | R2-8, R2-9, R2-10 |
| Low | 2 | R2-11, R2-12 |

**The mandate's premise holds: 2 of the 3 Blockings are defects the r1 fold itself introduced.**

- **R2-1** is the deleted `has_control` arm. The deletion argument assumed `missing_palettes` and
  `declares_light` agree on "has a light palette"; they do not, and the gap is a page with a working
  toggle and **11 of 11** tokens uncovered at 1.02:1 — the original defect at maximum severity,
  through the fix for it.
- **R2-2** is the F4 stripper meeting the F6 corpus widening. Neither is wrong alone. Together, one
  sentence of prose deletes the light palette from the scan, and on the real `/backlog` page that is
  **107,485 characters** deleted in a single match, beginning inside the row that documents this fix.
- **R2-4/R2-5/R2-6** are the same composition: three regexes written for stylesheets now run over a
  whole HTML document, in both directions — reads over-match (R2-4), coverage over-matches (R2-5),
  and the one guard against that over-match fails at nesting depth 2 (R2-6).

**R2-3 is why all of this shipped.** The four `⛔` cases produce a refusal byte-identical to the
empty control, and four of the fixes revert with `62/62 passed`. Until each case has a control that
**composes**, the suite reports on nothing, and the next fold will land the same way.

The direction of travel is right — F1, F4b, F5, F10 and F12 are genuinely closed and genuinely
tested. The two mechanisms that need to change shape rather than be patched again are the **corpus**
(extract stylesheets; stop parsing prose) and the **gate** (one definition of "declares a light
palette", used by both predicates).

VERDICT: NOT CONVERGED
