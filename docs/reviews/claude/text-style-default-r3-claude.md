# Round 3 — `text-style-default` (backlog #376, PR #422) — Claude half — NOT CONVERGED

Reviewed at `201aa640` (scope `3fb3fb2d..201aa640`, read against `origin/master...HEAD`). Mandate: refute
the bet in the last `text-style-default` row of `docs/reviews/decision-scheme/decision-log.jsonl`:
(1) no fragment the guard ACCEPTS renders bold below 4.5:1 in any palette or theme state; (2) no
fragment in the canonical format is refused.

**Method.** Everything ran in `mktemp` copies with a temporary `HOME`; no tracked file was touched
except this one. The fixture is the committed `2026-10-26-brief-2026-10-26-topic-progress-and-plan.fragment.html`.
Each attack is that fragment with CSS appended to its first `<style>` (or placed in a second one),
composed by the real CLI (`brief-compose.py --content … --out <tmp> --source <the committed page>`).
Accepted pages were opened in headless Chromium (Playwright 1223) in all six states, OS
light/dark × `data-theme` none/light/dark. Every `.ex-body strong, .ex-body b` was measured:
computed `color` against the first non-transparent `background-color` up its ancestor chain, using WCAG 2.x.
Baseline: 36 bold elements, minimum **8.01** (light) and **7.79** (dark), in every state.

Both clauses of the bet are refuted. One false accept sits **inside** the canonical format and inside
what the code says it computes exactly (F1). One is the r2 X4 ground rule, bypassed by spelling the
selector differently (F2).

---

## F1 — Major — a `var()` chain resolved "within the block" is overridden by the cascade: false accept at 1.00:1, inside the format

`scripts/brief-compose.py:627` (`_resolve_colour`), `:590` (rules declaring no palette token are skipped),
and the claim at `:419-420` and `:692`: *"Inside that format the cascade is small enough to compute
exactly"* / *"The format makes this exact"*.

`_resolve_colour` follows `--em: var(--c)` to the `--c` declared **in the same block**. The browser
resolves `var(--c)` against the **winning** `--c` on `:root`. Any later rule with a canonical
selector, or a more specific one, can redeclare `--c`. That rule declares no `--bg`/`--em`, so `:590`
skips it, and so do the format rules. Nothing in the format restricts tokens that are not palette tokens.

Reproduction 1 (OS-dark path). Append:
```css
:root[data-theme="dark"]{--bg:#16151a;--x:#9db8e8;--em:var(--x)}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#16151a;--x:#9db8e8;--em:var(--x)}}
:root[data-theme="dark"]{--x:#16151a}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--x:#16151a}}
```
Compose **ACCEPTED**. Chromium, OS dark / nothing pressed: bold `rgb(22,21,26)` on `rgb(22,21,26)`, **1.00:1**.
In the pressed states the shim's pressed `--em` happens to mask it, at 7.79.

Reproduction 2 (the `--bg` side, pressed dark). Append:
```css
:root[data-theme="dark"]{--panel0:#16151a;--bg:var(--panel0);--em:#9db8e8}
:root[data-theme="dark"]{--panel0:#9db8e8}
```
Compose **ACCEPTED**. Chromium, OS light and OS dark with dark pressed: bold `rgb(157,184,232)` on
`rgb(157,184,232)`, **1.00:1**.

These are real house idioms (`--bg: var(--panel)`-style aliasing), not exotic CSS. The guard is wrong
here about its own subject, the format, and not only about what it disclaims.

**Fix.** Pick one of two, and the second keeps the "exact" claim true:
(a) require `--bg`/`--em` to be literal `#hex` in a palette block, with no `var()`. That drops the
var-chain support, and it costs nothing today: `grep -E -- '--(em|bg)\s*:\s*var\('` over all 26
`docs/explainers/*.fragment.html` returns **zero** hits. Or (b) refuse any declaration, in any rule, of a custom property
that a palette block's `--bg`/`--em` chain passes through, unless it is in that same block. Add the
two reproductions above as cases. Correct `:419-420` and `:692` either way.

## F2 — Major — the page-ground rule (r2 X4's fix) keys on three exact selector strings, so `html body` reopens X4 verbatim

`scripts/brief-compose.py:583`: `if any(s in GROUND_SELECTORS for s in sel.split(","))`. Only the
whitespace-free selectors `body`, `html` and `:root` are checked.

Reproduction: append `html body{background:#9db8e8}`. Compose **ACCEPTED**. Chromium: OS light
**4.39:1**, and OS dark / dark pressed **1.00:1** (`rgb(157,184,232)` on `rgb(157,184,232)`). This is
the same rendering r2 X4 measured. `body{background-image:linear-gradient(#9db8e8,#9db8e8)}` is also
accepted, because only `background`/`background-color` are read. I did not measure that one
(my instrument reads `background-color`), so treat it as a lead.

The wrapper the composer itself adds is the same failure one level down: `.ex-body{background:#9db8e8}`
is **ACCEPTED** and measures **1.00:1** in OS dark, dark pressed and both. `explainer-delivery.md:133`
disclaims "a wrapper with its own background", but the bet does not.

**Fix.** Either refuse any `background*` declaration on any rule whose selector's subject could be
`html`, `body` or `.ex-body` (a strict lint can say "only `body{background:var(--bg)}`, nothing else
may set the page or the wrapper ground"), or narrow the bet to the claim the docstring makes. The
current state, a rule that names X4's fix and is bypassed by a descendant combinator, is the worst
of both.

## F3 — Major (against the bet, not the docstring) — bold not coloured by `--em` is accepted at 1.00:1

`scripts/brief-compose.py:1306-1308` runs the check, and nothing constrains what bold actually reads.
`page_chrome.text_style_css()` routes bold through `--emph`: `:root{--emph:var(--em)}` and then
`.ex-body strong,.ex-body b{color:var(--emph)}`. `--emph` is not a palette token, so a fragment may set it freely.

| Appended to the fragment | Compose | Chromium, worst state |
|---|---|---|
| `.ex-body{--emph:#16151a}` | ACCEPTED | **1.00:1** (OS dark; dark pressed) |
| `html:root{--emph:#16151a}` (0,1,1 beats the scheme's `:root`) | ACCEPTED | **1.00:1** |
| `body .ex-body strong,body .ex-body b{color:#16151a}` | ACCEPTED | **1.00:1** |
| `<link rel="stylesheet" href="data:text/css,.ex-body{--emph:%2316151a}">` in the body (`css_of` never reads `<link>`) | ACCEPTED | **1.00:1** |
| `.ex-body strong,.ex-body b{color:#16151a}` (equal specificity, the chrome CSS is later) | ACCEPTED | 7.79, harmless |

The redesign's prose disclaims this ("bold that does not read `--em` is outside it",
`explainer-delivery.md:133`, the `assert_em_in_every_palette` docstring). The **bet** has no such
qualifier: *"no fragment that the guard ACCEPTS whose rendered bold is below 4.5:1 in any palette"*.
So clause (1) is lost on the bet's own wording, even if F1 and F2 are fixed.

**Fix.** The cheap, honest part: refuse any fragment declaration of `--emph`/`--head`/`--prose`,
which are the scheme's own role tokens and have no legitimate per-page override. Then either refuse
`color` on `strong`/`b` inside the scope or record the bet's scope as the docstring's. Whichever is
chosen, the decision-log `observed` field for this row should say the bet was lost on (1). It should
not be re-worded after the fact.

## F4 — Minor — the per-state model assumes the shim is the LAST stylesheet, but a second fragment `<style>` comes after it: a false refusal of a page that renders 7.53:1

`scripts/brief-compose.py:728` (`layers = resolved + _shim_palette()` puts the shim after every
fragment block) against `:1264`. `styled = head + SHIM + …` splices the shim into the fragment's
**first** `<style>`, so a second `<style>` in the fragment body follows the shim in document order.

Reproduction: put `:root[data-theme="dark"]{--bg:#4a5568;--em:#ffffff}` in a second `<style>`. Compose
**REFUSED**: *"in OS light, dark pressed: the format resolves --em to #9db8e8 on --bg #4a5568, 3.75:1"*.
With only the guard bypassed (same `compose`, `assert_em_in_every_palette` stubbed), Chromium
measures **7.53:1** (`#ffffff` on `#4a5568`) in both dark-pressed states. Clause (2) is refuted. The
block is canonical and the format does not forbid a second `<style>`. The same CSS in the first
`<style>` is refused correctly: it renders 3.75:1 there, because the shim's pressed `--em` wins.

I found no false ACCEPT through this ordering. Every fragment block declares both tokens, so when a
late block wins it wins both tokens, and that pair was verified per block.

**Fix.** Either order `layers` by real document position (the shim sits at the end of the first
style element), or refuse palette blocks outside the first `<style>`, which is the simpler lint.

## F5 — Minor — the refusal tells the author to do something that cannot help

`scripts/brief-compose.py:744-751`. When the per-state check fails because the **shim's** pressed
`--em` (`#9db8e8`/`#2d4a7c`, at (0,2,0), after the fragment) beats the fragment's own pressed `--em`,
the message says *"Declare `--em` in EVERY palette block"*. The fragment in F4's first-style variant
already does, and nothing it declares in a canonical block can win. The real remedy is a `--bg` that
the family `--em` clears. This is also a design fact worth one line in §2: **a fragment's
`:root[data-theme=…]{--em}` is dead CSS. The shim's pressed pair always wins.**

## F6 — Minor — stale counts after the merge

The merge brought in `2026-10-27-topic-tag-vocabulary-survey.fragment.html`, so HEAD has **26**
fragments. "the 25 repo fragments" (`scripts/brief-compose.py:430`), "24 of 25 real fragments"
(`:2372`), "the 25 fragments" (`docs/backlog.md:358`, `docs/dashboard-entries.md:17998`). The 26th
composes and fits the five blocks, so this is only the counts going stale.

---

## Held (executed)

- **Self-test:** `193/193 passed` at HEAD.
- **All real fragments:** 26 of 26 compose through `compose`, 0 refused. The `--em` check runs on 10.
  Nine are themed. One, `2026-10-05-topic-why-x-not-y`, is `themed=False`.
- **Rendered, all six states, every bold:** the 9 themed pages measure 7.57 to 8.45. The unthemed
  page measures 7.90 (OS light) and 7.45 (OS dark) unpressed. It does reach **1.80 / 1.70** with
  `data-theme` set by hand, but it carries no theme control. Its only script reads
  `localStorage.getItem('explainer-scheme')`, and `page_chrome.chrome_script`, which restores
  `data-theme` from storage even without a button, is not on the page. So the pressed states are
  unreachable there, and skipping them is correct. ⚠ That correctness depends on this page never
  receiving `chrome_script`, which restores the theme regardless of the button. If a future change
  ships the script without the button, the omitted states become live at 1.70.
- **Format edges accepted correctly:** uppercase hex; 3-digit hex (`#000`/`#ABC`); comments inside the
  selector and the values; a canonical block repeated; the same block in a second `<style>`;
  `@MEDIA (PREFERS-COLOR-SCHEME: DARK)`. Refused by name, as the strict format intends: `:ROOT[…]`,
  single-quoted `[data-theme='dark']`, `@media screen and (prefers-color-scheme: dark)`.
- **`color-scheme: dark`, `forced-colors: active`, `prefers-contrast: more`:** no regression
  (forced-colors 21:1; the others match baseline). `@import url("data:…")` is accepted but loses to
  the later blocks, so it is harmless.
- **Red on `f88f10d0`:** HEAD's suite spliced onto f88f10d0's production code gives **17 red** (a
  `themed=` signature shim was needed, because the unshimmed run crashed at that kwarg after 16
  reds). That is at least the 15 claimed.
- **Mutations:** `check-plan-code.py --mutate . --only scripts/brief-compose.py`: **49/49 killed, 49
  attributed**, 0 survivors (a diagnostic slice). `EXPECTED_MUTATIONS` sums to **2354**, equal to the
  manifests summed independently.

## Prose vs code

`explainer-delivery.md:126-137` and the #376 row describe the lint's rules accurately. They overclaim
in two places. "Inside that format it also checks `--em` against `--bg`… in each theme state" is false
under F1 and F4. "A `body`/`html`/`:root` background is only `var(--bg)`" is true only of those exact
selector strings (F2). The decision-log bet is broader than both (F3).

VERDICT: NOT CONVERGED
