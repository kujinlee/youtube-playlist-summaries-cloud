# Adversarial review r3 — backlog #102, the r2 fold (Claude)

## PROOF OF SUBJECT

Pinned outside the repo with `git archive e4d88eb0 | tar -x -C <scratch>/r3`, both files verified:

```
scripts/brief-compose.py
  git : be211bb86e73ace849066467c6ce6355672e02117f05f698de7d5b807dd4783b
  disk: be211bb86e73ace849066467c6ce6355672e02117f05f698de7d5b807dd4783b
scripts/gen-backlog-page.py
  git : d98bfb33a27c9adf0f008cd90f0fb7e5594402161ca2abc3e812a06dcc9ed825
  disk: d98bfb33a27c9adf0f008cd90f0fb7e5594402161ca2abc3e812a06dcc9ed825

$ git log --oneline -1 e4d88eb0
e4d88eb0 Fold r2: two of its Blockings were caused by r1's fixes, and /backlog lost its Ask tray
$ python3 scripts/brief-compose.py --self-test
72/72 passed
```

Scope: the fold only. The working tree was not reviewed. Line numbers are at `e4d88eb0`.

## What the fold closed — measured, not taken on report

| r2 | Probe | Result |
|---|---|---|
| R2-1 empty `:root[data-theme="light"]{}` + real control | composed at `d4b54cfa` | **REFUSED** (8 tokens named) |
| R2-1 plain-property light palette + real control | composed at `d4b54cfa` | **REFUSED** |
| R2-2 the "eater" — prose `@media`+`prefers-color-scheme` before the palette | composed at `d4b54cfa` | **REFUSED: --card** |
| R2-5 code sample counted as a declared palette | refused at `d4b54cfa` | **COMPOSES** |
| R2-6 `:root` two levels deep inside `@media(scheme)` | credited at `d4b54cfa` | **REFUSED: --card** |
| R2-7 `/backlog` lost its Ask tray | degraded at `d4b54cfa` | **all three generators OK, tray: 1** |
| R2-3 vacuous cases | 4 cases = the control | **the four prose cases now have a control that COMPOSES** |

Mutation battery, control `72/72 passed` — **8 of 9 killed**, where r2 had four survivors:

| mutation | result |
|---|---|
| `P1` `css_of` → whole document | 69/72 killed |
| `P2` `css_of` → drop `style=` attributes | 71/72 killed |
| `P3` `strip_css_comments` → identity | suite red |
| `P4` blank all strings (drop `[...]` preservation) | 63/72 killed |
| `P5` keep all strings (never blank) | 71/72 killed |
| `P6` `strip_scheme_media` → identity | 71/72 killed |
| `P7` `markup_of` → identity | 71/72 killed |
| `P8` delete the `has_control` arm again | 71/72 killed |
| **`P9` brace depth `+= 1` → `+= 0`** | **72/72 passed** — R3-5 |

This is a real change in the quality of the suite. The findings below are what remains.

---

# R3-1 — HIGH. `strip_css_comments` runs strings across newlines; CSS ends them there. One newline-closed string erases the entire light palette and silently disables the guard.

**file:line** — `scripts/brief-compose.py:184-192`, the string branch:

```python
        if ch in "\"'":
            quote, keep = ch, brackets > 0
            out.append(ch); i += 1
            while i < n and css[i] != quote:
                if css[i] == "\\" and i + 1 < n:
                    out.append(css[i:i + 2] if keep else "  "); i += 2; continue
                out.append(css[i] if keep else " "); i += 1
```

The inner loop's only terminator is the matching quote or end of input. **CSS Syntax §4.3.5 makes a
newline inside a string a parse error**: the string token ends at the newline, the declaration is
dropped, and the parser recovers — every browser applies the rules that follow. This scanner
consumes straight through the newline to the next quote anywhere in the sheet, blanking everything
between.

**Control/defect pair** — identical pages, partial light palette (no `--card`), page reads
`var(--card)`; the defect adds one line, `.h::after{content:"unclosed` followed by a newline:

```
  CONTROL: clean
     light_palette_tokens = 10/11   -> REFUSED: --card
  DEFECT : one string closed by a NEWLINE
     light_palette_tokens =  0/11   -> COMPOSED
     composed page has a WORKING toggle: True
```

11 tokens → 0. `declares_light` goes False, and since this fragment has no button of its own the
`has_control` arm cannot save it, so `live_control` is False and `assert_theme_complete` returns at
`:337`. `chrome_for` then still adds a full control bar — `missing_palettes` is a substring test and
finds both selectors in the raw text — so **the reader gets a working toggle over a page the guard
never checked.** That is the R2-1 fail-open shape, reached through the new scanner.

**`css_of` amplifies it across blocks.** The extracted CSS is `"\n".join(...)`, so an unterminated
string in one `<style>` reaches into the next:

```
doc = '<style>.a{font-family:"Unclosed}</style><style>:root[data-theme="light"]{--card:#fff;--ink:#111;--bg:#fff}</style>'
light_palette_tokens(css_of(doc)) -> []
```

Each block is independently well-formed to the extent the browser cares; the concatenation is not.

**Fix shape:** end the string at `\n` (and at `\r`) as the CSS tokenizer does. Two characters in the
loop condition. A second, cheaper guard: scan each `css_of` fragment separately rather than one
joined string, so a defect in one block cannot reach another.

---

# R3-2 — MEDIUM. `css_of`'s `style=` rule is a regex over the document, so text that merely *looks* like an attribute is read as CSS. R2-4's class, through the narrower door.

**file:line** — `:146-148`:

```python
    out = re.findall(r"<style[^>]*>(.*?)</style>", document, re.S | re.I)
    out += re.findall(r'\sstyle\s*=\s*"([^"]*)"', document, re.I)
    out += re.findall(r"\sstyle\s*=\s*'([^']*)'", document, re.I)
```

The `<style>` half is element-scoped and correct — including the subtle case, which I checked:
`<style>.a{content:"</style>"}` ends at the first `</style>` for this regex *and* for the HTML
parser, so they agree. The attribute half has no element scoping at all: any whitespace followed by
`style="…"` anywhere in the document matches, including inside the `<pre>`/`<code>` samples
`markup_of` is careful to strip.

**Control/defect pairs**, light palette complete except `--defect`:

```
   control, no tail                               : COMPOSES
   <pre> text: 'use style="…"' (a space before)   : REFUSED: --defect
   <code> text, same                              : REFUSED: --defect
   properly ESCAPED sample (&quot;)               : COMPOSES

   css_of('<pre>use style="background:var(--defect)" on the div</pre>')
     -> 'background:var(--defect)'
```

The browser renders that as text; nothing reads `--defect`. An explainer page showing an inline-style
example — the page type this whole line of fixes exists to keep publishable — is refused again.

Note the asymmetry the fold introduced: **`markup_of` strips `<pre>`/`<code>`; `css_of` does not.**
The two corpora now disagree about whether a code sample is part of the page.

**Fix shape:** run the attribute scan over `markup_of(document)`, not `document`. That reuses the
existing complement and makes the two corpora agree by construction.

---

# R3-3 — MEDIUM. The two `has_control` call sites now disagree, and a page can lose its theme control entirely with nothing reporting it.

**file:line** — `:430` (`chrome_for`) and `:487` (`live_control`):

```
   line 430: has_control(content)                 # raw document
   line 487: has_control(markup_of(content))      # markup only
```

`markup_of` was added for r2's R2-8 and applied at one site. **Trigger:** a fragment with real
palettes whose whole chrome block is inside an HTML comment — a plausible "turn the toggle off for
now" edit.

```
   chrome_for   (430) has_control(content)            = True
   live_control (487) has_control(markup_of(content)) = False

composed OK. What the reader gets:
   a theme button in the LIVE markup?  False
   a chrome bar at all?                True
   a generated-at stamp?               True
```

`chrome_for` believes the fragment brought its own control, so it adds none; the fragment's control
is commented out, so there is none. The page ships with a stamp and **no theme button**, silently —
the fail-silent `page_chrome`'s own module docstring says it exists to prevent, reached through the
composer. `assert_wired` does not catch it: `_scripts()` finds the script inside the comment too.

This is the third time in this branch a fix has landed at the instance rather than the class
(r2 R2-6 CSS-vs-HTML comments, r2 R2-7 one arm of `live_control`, now this). One helper, both sites.

---

# R3-4 — MEDIUM. The comment justifying the four new tokens asserts a cascade fact that is the opposite of the truth.

**file:line** — `scripts/gen-backlog-page.py:1130-1136`:

> *⚠ THE SHIM'S OWN VOCABULARY. `SHIM` is appended AFTER this stylesheet and paints
> `body{background:var(--bg)}`, so it **WINS** over this page's `body{background:var(--ground)}`.
> Without a light `--bg` the body kept the shim's DARK value…*

The shim's paint rule is `brief-compose.py:104`:

```css
  :where(html, body) { background: var(--bg); color: var(--fg); }
```

`:where()` contributes **zero** specificity, and `brief-compose.py:101-103` says so in terms:

> *`:where()` contributes ZERO specificity, which is the whole reason this is safe to add — SHIM is
> concatenated AFTER the fragment's CSS, so a normal `body{…}` rule here would override every page
> that already paints itself. **This one is always losable.***

`gen-backlog-page.py:1163` is `body{margin:0;background:var(--ground);…}` — specificity (0,0,1),
which beats (0,0,0) regardless of source order. The page's body was never painted from `--bg`, so it
never "kept the shim's DARK value". (`--bg` does reach `html`, whose background propagates to the
canvas, so it is visible in overscroll and gutters — a real but different effect.)

**The change itself is correct** — all four tokens are genuinely read, which I checked:

```
   --bg         read by: tray, SHIM
   --rule       read by: tray, chrome_css, SHIM
   --structure  read by: tray, SHIM
   --defect     read by: tray
```

The lifted tray reads all four with no fallback; that is the real reason they are needed, and the
comment does not mention it. Written in this project's measured register, next to the code, a future
reader will trust it — which is precisely the failure `page_chrome.py:12-16` records against this
same file (*"a guard was told otherwise"*).

---

# R3-5 — MEDIUM. The nesting case cannot observe the brace-counting it names. `P9` survives 72/72.

**file:line** — `strip_scheme_media` `:242-247`; case *"⛔ a :root two levels deep inside
@media(scheme) is not coverage"*.

Mutating `depth += 1` → `depth += 0` (the strip ends at the *first* `}` — i.e. exactly the one-level
regex the fold replaced) leaves the suite at **72/72 passed**.

The fixture places the nested `:root` where any truncation removes it too:

```
  SHIPPED fixture   @media(…light){@supports(…){:root{--structure-bg:#fff}}}
     correct brace counting -> []
     mutation  depth+=0     -> []
     mutation observable?    False

  DISCRIMINATING    @media(…light){@supports(…){.a{color:red}} :root{--structure-bg:#fff}}
     correct brace counting -> []
     mutation  depth+=0     -> ['--structure-bg']
     mutation observable?    True
```

The case proves the inner `:root` is stripped; it does not prove *depth counting*, which is the
property the docstring claims and the reason the regex was replaced. Moving the `:root` after a
sibling nested block — one line — makes it load-bearing.

---

# R3-6 — LOW. Bracket depth never resets, so one unmatched `[` stops value-string blanking for the rest of the stylesheet.

**file:line** — `:176-181`. `brackets` is incremented at `[`, decremented at `]` (floored at 0), and
never reset at a rule boundary.

```
  css  = '.a{background:url(a[b.png)}.n::before{content:"var(--defect)"}'
  strip-> '.a{background:url(a[b.png)}.n::before{content:"var(--defect)"}'   # string NOT blanked
  vars_read_anywhere -> ['--defect']
```

The balanced control blanks it correctly (`content:"             "`). So an unmatched `[` anywhere
re-enables r2's R2-4 false positive for everything after it. An unquoted `url()` containing `[` is
the only realistic source I found, so the trigger is thin — but the state machine has no reason to
carry bracket depth across a `}`, and resetting it there costs one line.

---

# R3-7 — LOW. `css_of` misses unquoted `style=` attributes.

```
  css_of('<div style=background:var(--defect)>x</div>') -> ''
```

Unquoted attribute values are valid HTML5 and the browser applies them. Every generator in this repo
quotes, so this is latent; it is listed because `css_of`'s stated contract is *"the CSS a browser
will apply"*.

---

# R3-8 — LOW. `markup_of` fails open on an unclosed `<pre>`/`<code>` and fails closed on an unescaped `<!--`.

`:265-268` strips each element with a non-greedy `<tag…>.*?</tag>`, which requires the closing tag.

```
  unclosed <pre> containing the button   -> has_control(markup_of(...)) = True   (fails OPEN)
  unescaped '<!--' before a real '-->'
  with the real button between them      -> has_control(markup_of(...)) = False  (fails CLOSED)
```

The first refuses a page that has no control; the second hides one that does. Both need malformed
markup, so neither is reachable from the current generators.

---

## Carried, not re-reported

r2's R2-10 (the narrowing is 8/11 unconditional while the docstring describes it as live), R2-11
(a second selector in the shim's media block is dropped silently) and R2-12 (no
`scripts/mutations/*.json` entry, so `--mutate .` still cannot see any of this) are unchanged by the
fold and remain open. R2-12 is why `P9` survived unnoticed.

---

## Summary

| Severity | Count | Findings |
|---|---|---|
| Blocking | 0 | — |
| High | 1 | R3-1 |
| Medium | 4 | R3-2, R3-3, R3-4, R3-5 |
| Low | 3 | R3-6, R3-7, R3-8 |

**This fold is the first one that did not introduce a Blocking.** All seven r2 findings I probed are
genuinely dissolved, `/backlog` has its tray back, and the suite went from four surviving revert
mutations to one. The `css_of` / `markup_of` split is the right shape — the corpus question that
produced r1 F6, r2 R2-2, R2-4 and R2-5 is now answered structurally rather than patched.

What remains is smaller and of one kind: **three hand-written scanners that are each right about the
case they were written for and diverge from the real parser at an edge.**

- **R3-1** is the one that still costs a reader: the CSS tokenizer ends a string at a newline and this
  one does not, and the consequence is the guard silently switching itself off over a page that gets
  a working toggle. It is a two-character fix.
- **R3-2**, **R3-3** and **R3-6** are all the same shape — a scan whose scope is not the thing it
  claims to scan (`style=` outside any element, `has_control` on two different corpora, bracket depth
  across a rule boundary). Each is one line.
- **R3-5** is why R3-1-class defects keep arriving: the case for the newest mechanism does not
  discriminate it, and with no mutation manifest (R2-12) nothing else will.

The `--bg` comment (**R3-4**) is worth fixing even though the code is right, because this repository
treats a confidently wrong comment beside a guard as a defect in its own right, and has the receipts.

VERDICT: NOT CONVERGED
