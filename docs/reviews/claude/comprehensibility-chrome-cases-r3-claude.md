# Round 3 — `comprehensibility-chrome-cases` — Claude half (adversarial)

Subject: `git diff origin/master...HEAD` at `6fd6ae32`, worktree `wt-comp`. Mandate: refute.
Nothing was written in the worktree; scratch work is in `scratchpad/claude-r3-tmp/`.

## The bet (last row of `decision-log.jsonl`): LOST, on both of its named observations

> *"no page the route ACCEPTS whose light press fails in Chromium, and no valid CSS that makes it
> REFUSE a working palette"*

Both happened, measured end to end: fragment → `scripts/brief-compose.py --content … --out <scratch>`
→ Chromium (`colorScheme: 'dark'`) → click the real `#chrome-theme` until `data-theme="light"` →
`getComputedStyle(document.body)`. The probe palettes declare every shim token plus `--mono`, so the
half-live guard is satisfied and does not mask anything.

**Baseline (control):** `OK_baseline`, the committed shape → light press gives body
`rgb(255,255,255)` / ink `rgb(17,17,17)`. So the harness can show a working light press.

## Suites (read-only)

- `python3 scripts/page_chrome.py --self-test` → `237/237 passed`, rc=0
- `python3 scripts/brief-compose.py --self-test` → `153/153 passed`, rc=0
- `git status --short` was empty afterwards.

---

## F1 — HIGH — the "exact condition" accepts pages whose light press leaves them dark

`scripts/page_chrome.py:352-366` (`_light_by_exclusion`), and `:228-236`/`:573-662` (`css_of`, `_Scan`).

The condition looks only at **token-declaring rules** in **`@media` blocks it recognises by substring**,
in the **concatenated `<style>` text**. Anything outside that view that applies under OS dark is not
looked at, and the page is accepted. Every row below returned `missing_palettes(...) == []`, was composed
with `rc=0` and a control added (`ctl=1`), and in Chromium with light pressed:

| shape (dark rule the detector cannot see) | body bg after light press | ink |
|---|---|---|
| `A1` a non-token rule in the dark block: `body{background:#000 !important;color:#fff !important}` | `rgb(0, 0, 0)` | `rgb(255,255,255)` |
| `A1b` same, `p{background:#000;color:#fff}` | body white, **`p` bg `rgb(0,0,0)`** | `rgb(255,255,255)` |
| `A2` `@media not (prefers-color-scheme: light){:root{--bg:#000}}` | `rgb(0, 0, 0)` | `rgb(17,17,17)`: **≈1:1** |
| `N1` CSS nesting inside the default: `:root{…; @media (prefers-color-scheme:dark){--bg:#000}}` | `rgb(0, 0, 0)` | `rgb(17,17,17)` |
| `SM` `<style media="(prefers-color-scheme: dark)">:root{--bg:#000}</style>` (css_of ignores `media=`, so this reads as a second top-level *default*) | `rgb(0, 0, 0)` | `rgb(17,17,17)` |
| `A3` escaped feature name `@media (prefers-color-sch\65 me: dark){:root{--bg:#000}}` | `rgb(0, 0, 0)` | `rgb(17,17,17)` |
| `A4` escaped custom property in the dark block `:root{--\62 g:#000}` (`_DECLARES` misses it) | `rgb(0, 0, 0)` | `rgb(17,17,17)` |
| `A6` dark *default* + `@media not all and (prefers-color-scheme:dark){…exclusion…}` (the `not` is read as "dark"; nothing checks that the default is light) | `rgb(0, 0, 0)` | `rgb(238,238,238)` |
| `A8` `:root{color-scheme:dark}` in the dark block | white (`colorScheme` stays `dark`, so form controls and scrollbars stay dark) | — Low |

The raw line for `A2`:
`A2_not_light.html ctl True | osDark bg rgb(0, 0, 0) | light: ('rgb(0, 0, 0)', 'rgb(17, 17, 17)', …)`.
One shape did NOT reproduce: `@import url("data:…") (prefers-color-scheme: dark)` rendered light, so it is dropped.

**Most realistic shapes:** A1 (a plain `body`/`img`/`pre` rule in the dark block is ordinary authoring),
SM, and N1. A2, A3, A4 and A6 are contrived, but they are valid CSS, and they show the condition is a
blacklist of seen shapes, not the "exact condition" the docstring and the records claim.

**The route is what introduces this.** On `origin/master` each of these pages lacks
`:root[data-theme="light"]`, so it was refused and composed stamp-only. On this branch a live button
is added, and pressing it does nothing or leaves the text unreadable. This is the fail-silent that
`page_chrome.py` exists to prevent, and the same class as r2's Codex High.

**Caused by the r2 fold?** No. Going by the r2 coordinator's description of the r1 code (*"asked
only that an exclusion EXIST"*), the r1 predicate also accepted every row. That is UNVERIFIED against
the r1 code itself. The r2 redesign kept these shapes when it narrowed the check to
"token-declaring" rules, and that narrowing is r2 code.

**Fix (pick one):**
- **Whitelist.** Accept only when the whole applied CSS is inside a grammar the detector fully
  understands. Refuse on any `\` outside a string, any `@import`, any `{` inside a style-rule body
  (nesting), any `<style media>` or `<link rel=stylesheet>`, and any `@media` prelude that mentions
  `prefers-color-scheme` but is not exactly `(prefers-color-scheme:dark)` after whitespace removal
  (this covers `not`). Inside such a block require **every** rule, not every token-declaring rule,
  to be the exclusion. Measured: all 19 committed exclusion-style fragments have exactly one rule in
  their dark block, and it is the exclusion, so this refuses nothing in the corpus.
- **Or decide it in Chromium** (backlog #304 route C), which is the only instrument that cannot be
  fooled by any of the above.

## F2 — MEDIUM — `_skip_string` reintroduces the "a newline ends a bad string" Blocking, in both directions

`scripts/page_chrome.py:276-281`. **Caused by the r2 fold:** the tokenizer is new in c0b9cf51.

`strip_css_comments` (`:205-215`) ends an unterminated string at the newline, as CSS does, and says
why: one stray quote once blanked a whole stylesheet (r3 Blocking). `_skip_string` scans to the next
matching quote anywhere, so the same file now has two string rules that disagree. The repo has
measured this "second implementation drifts" pattern 17 times.

- **Accept direction (`S1`).** Two stray quotes (`.x{content:"oops⏎}` … `.z{content:"oops2⏎}`)
  hide an unconditional `@media (prefers-color-scheme:dark){:root{--bg:#000;--ink:#111}}` placed
  between them. The tokenizer swallows it as the body of `.x`. Result: `missing_palettes → []`,
  composed `rc=0` with a control, and in Chromium with light pressed `bodyBg rgb(0, 0, 0)`,
  `bodyInk rgb(17, 17, 17)`.
- **Refuse direction (`R18`).** One stray quote (`[data-x="abc⏎]{}`) gives `['light']`, so the
  page composes with `ctl=0`. The same CSS with control and script in Chromium: light press gives
  `rgb(255, 255, 255)`. A working control is removed.

**Fix:** stop at `\n` in `_skip_string`, and have one string scanner shared by both functions rather
than two. Add both shapes as cases.

## F3 — MEDIUM — valid CSS makes it REFUSE working palettes, so the composer drops a working control

`scripts/page_chrome.py:354` (`flat(p) == ":root"`) and `:366` (`s == _LIGHT_EXCLUDED`, an exact string).

Each row returned `['light']` and composed with **no control** (`ctl=0`). The same CSS with
`theme_control()` and `chrome_script()`, in Chromium with OS dark, gave a light press of
`('rgb(255, 255, 255)', 'rgb(17, 17, 17)')` and a dark press back to `rgb(0, 0, 0)`. In other words,
every palette works:

`:root:not([data-theme='light'])` (single quotes) · `:root:not([data-theme=light])` (unquoted) ·
`:ROOT:not(…)` · default as `html:root{…}` · default inside `@layer base{…}` ·
`:root:not([data-theme="light"]),:root[data-theme="dark"]{…}` (a common idiom) ·
`:root:not(:where([data-theme="light"]))` · nesting `:root:not(…){@media (…dark){…}}` ·
`:root,:host{…}` default.

These were also refused before the route existed, so none of them is a regression against master.
They are, however, the bet's second named failure observation, and the same harm r2's Medium M2 was
rated for. **Caused by the r2 fold?** No. That is UNVERIFIED for r1, but its presence test was
literal too.

**Fix (cheap, safe):** normalise the attribute selector (quote style, unquoted value) and match
`:root` case-insensitively. Accept a selector list whose every member is either the exclusion or
`:root[data-theme="dark"]`, because neither matches with light pressed. Leave `@layer`, `:where`
and nesting refused if F1's whitelist is adopted.

## F4 — MEDIUM — the stub page cannot see an OS-dark defect in the theme press, the one it claims to check

`scripts/page_chrome.py:2289` (`G.matchMedia=function(){return {matches:false};}`), and `:1711`.

The stub ignores the query string and always answers "OS light". I applied mutations to a **copy**
(`claude-r3-tmp/mut/scripts`) and ran `--self-test` there:

| mutation in `chrome_script()` | result | real effect |
|---|---|---|
| `matchMedia('(prefers-color-scheme:dark)')` → `'(prefers-color-scheme:light)'` | **237/237 passed** | for every OS-dark reader, `cur()` says light, so the first press sets `dark` and **nothing visibly changes**: a dead first press |
| initial `aria-pressed` → literal `'false'` | **237/237 passed** | the pressed state is wrong on load for OS-dark readers |
| text-style persisted under the wrong key | **237/237 passed** | the chosen text style does not persist |
| saved text-style never read (`var sv=null;`) | **237/237 passed** | same |
| refresh click handler throws / posts to `/regenrate` | **237/237 passed** | disclosed in backlog #305 ("the refresh button — is not covered"), so not counted as a finding |
| refresh never re-enabled after an error | killed (`236/237`) | control: the harness can kill a mutation |

The only case that names the OS fallback is a substring test, `"prefers-color-scheme" in js`
(`:1711`), and the flipped query still satisfies it. The cases claim *"one press of each control …
pressing the theme button … changes the theme"*. That is true only in the OS state where the first
mutation above is invisible.

**Caused by the r2 fold?** No; this is r1's stub.

**Fix:** make the stub's `matchMedia(q)` return `{matches: q === '(prefers-color-scheme:dark)' && OS_DARK}`,
and run it a second time with `OS_DARK=1`, expecting `pressed0 === 'true'` and
`theme1 === ['light','false']`. A storage stub that records `setItem`/`getItem` and a reload pass
would close the two persistence rows, which are Low and outside the stated claim.

## F5 — LOW — the records overstate, and they do not yet say what this round arms

- **The word "EXACT"** appears in the r2 coordinator note (*"replaced by an exact condition"*), in
  backlog #300 (*"accepts that form under an EXACT condition"*), in the dashboard tech section and in
  the `_light_by_exclusion` docstring (*"THE CONDITION IS EXACT"*, *"Anything outside that shape
  stays refused"*). F1 and F2 show it is not exact.
- **The dashboard** says the tests *"press both buttons and check that they work"*. F4 shows a theme
  press that is dead for OS-dark readers passes them.
- **Checked and accurate:**
  - Backlog #305's ✅ states its bound honestly: refresh and the scroll fallback are not covered.
  - Backlog #304's task-0 note is accurate.
  - Backlog #105's comment change is present at `brief-compose.py:124-134`.
  - Two of the recomposed pages (`2026-09-20-…-324`, `2026-09-08-…-state`) re-derive identical
    apart from `<title>` (my missing `--title`) and the stamp.
  - Visible text, old vs new, in Chromium at 320×568 with OS dark: 6 of 7 pages identical. On
    `2026-10-06` the only difference is "Text style: colour / headings only / plain", which I
    stripped with the bar because the script moves `#schemer` into it. That is the intended change.
- **Thrashing.** F2 is fix-induced by r2's fold, in `palette-detection`, and r2's findings were all
  fix-induced in the same component. By the r2 coordinator's own note and `dev-process.md` Phase 6,
  that is two consecutive rounds, so the architecture review arms. The decision-log row's `outcome`
  should record the lost bet: named failure observation hit on both halves.

**Fix:** remove "exact" or make it true (F1). Set the bet's outcome. Record that the
architecture-review trigger fired.

## F6 — LOW — the compose half-live guard hard-fails on a page that will get no control

`scripts/brief-compose.py:872-876`. Pre-existing; **not caused by the r2 fold**.

`composer_adds_control` is still a substring test, `'[data-theme="light"]' in scoped`, and
`:root:not([data-theme="light"])` satisfies it. `missing_palettes` now uses a stricter rule. For the
`:root,:host{…}` default (F3), `missing_palettes` says the composer will add no control. The
half-live guard still runs as if it will, and exits `rc=1`: *"this page has a WORKING theme toggle,
but its light palette does not cover every token…"*. That message is false: the page would have been
composed stamp-only. The two predicates for one question have drifted.

**Fix:** `composer_adds_control = not page_chrome.missing_palettes(content + page_chrome.theme_control())`,
which is the predicate `chrome_for` actually branches on (`:773`).

---

VERDICT: NOT CONVERGED
