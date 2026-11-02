# text-style-default — round 1, Claude half (adversarial)

Subject: branch `text-style-default` (backlog #376, PR #422) at HEAD `9aa3b909`, diffed against
`origin/master` with `git diff origin/master...HEAD`. Mandate: refute the four claims in the brief.
Everything was executed in a mktemp dir with a temp `HOME`. Nothing was written to `~/explainers`.

## What I tried to refute and could not

- **Claim (3), recompose.** Re-ran it myself: all 24 tracked fragments that have a page beside them,
  composed with master's `scripts/` (from `git archive origin/master`) and HEAD's, each using its own
  committed page as the tray source and a fixed stamp. **23 of 24 are byte-identical** between the
  two composers on HEAD's fragments. The one that differs is `2026-10-26-…progress-and-plan` (6 diff
  lines: the wrapper, the switcher and the scoped CSS). The skills page is identical because its
  fragment already opts in. Neither composer refused any of the 24. Both committed pages equal HEAD's
  composition once the `<time>` stamp is masked. The extra CSS comment in the progress page is SHIM
  drift from master. It is not this branch's change, and the brief says so.
- **Claim (4), browser.** Re-measured in headless Chromium (Playwright, `file://` copies). On BOTH
  pages, OS-dark with nothing pressed: `.ex-body b` is `rgb(157,184,232)` at **9.04:1** and `h2` is
  `rgb(203,154,104)` at **7.23:1**. OS-light: 8.45:1 and 5.62:1. All three `#schemer` buttons are
  `elementFromPoint`-topmost at their centres. Pressing *plain* changes the `h2` from the accent to
  `--fg`. There is no nested `.ex-body`. Reproduced exactly.
- **Claim (1), wrap/nesting.** A hand-placed `class="wrap ex-body"` (4 real fragments) is not
  wrapped. A fragment that brings its own `#schemer` gets one `#schemer` and no wrapper. An
  `ex-body` that appears only inside an HTML comment is not taken as an opt-in, so the page is
  wrapped. That is correct.
- **Mutations.** `check-plan-code.py --mutate . --only scripts/brief-compose.py` printed
  `35 mutation(s), 35 killed, 35 attributed to the case each names, 0 survivor(s)` in 22s. The
  manifests sum to **2340**, which matches `EXPECTED_MUTATIONS` and the self-test pin. The
  `--self-test` result is 164/164.
- **Palette parser probes that held:** `html,:root` lists, `@supports`, `@layer`, doubly nested
  `@media`, `@media (prefers-color-scheme: dark) and (…)`, `!important`, a palette in a second
  `<style>` inside the body (refused correctly), and `--bg` inside a comment or a string (ignored
  correctly). A `}` inside a string does not truncate the rule, because strings are blanked first.

## Findings

### MAJOR 1 — the `--em` refusal guards only the composer's OWN switcher, but §2 says the composer refuses every page that gets one

`scripts/brief-compose.py:900-903` (`want_switcher = not own_switcher; if want_switcher:
assert_em_in_every_palette(...)`) against `.agents/skills/shared/explainer-delivery.md:123-124`
(*"A page that gets the switcher DECLARES `--em` IN EVERY PALETTE BLOCK … and since backlog #376
the composer REFUSES to compose one that does not"*). Claim (2) in the brief also says *"refuses
any compose"*.

A fragment that brings its own `#schemer` is never checked, yet it ships `text_style_css()` and
the same `var(--em)` consumer (`chrome_for` emits the scoped CSS for `want_switcher or
own_switcher`). Reproduction: I took the progress-and-plan fragment, deleted ` --em:#9db8e8` from
both dark blocks, changed `<div class="wrap">` to `<div class="wrap ex-body">`, and put
`page_chrome.text_style_control()` after it. The result is **COMPOSED, schemer=1**. That is the
1.78:1 page the 2026-10-24 review measured, reached through the branch the guard skips. No
committed page is in this state today. The only own-switcher fragment, `2026-10-05-topic-why-x-not-y`,
declares `--em` in both of its blocks. The gap is a docs contract that is wrong in the direction
that sounds safer.

**Fix:** call `assert_em_in_every_palette` when `want_switcher or own_switcher`, which is the same
condition that emits the scoped CSS. I checked that this keeps `2026-10-05-topic-why-x-not-y`
composing: `palette_blocks` finds its two blocks, both have `--em`, and it PASSES. Add a case built
from an own-`#schemer` fragment whose dark block lacks `--em`, plus a mutation that restores
`if want_switcher:`. If the narrower scope is intended, §2 and the backlog #376 row must say
"when the composer adds the switcher" instead.

### MINOR 2 — the check is for presence only, so a dark block that declares the LIGHT `--em` composes at the trap's contrast

`scripts/brief-compose.py:476` (`"--em" not in decls`). Reproduction: in the progress-and-plan
fragment, replace `--em:#9db8e8` with `--em:#2d4a7c`. This is the copy-the-light-block-and-forget
edit, which is how these palettes get written. The result is **COMPOSED**. That renders the exact
colour pair the review measured. `--em:initial`, `--em:;` and `--em:var(--undefined)` also pass,
but those fall back to the inherited prose colour and stay readable. The docstring says the guard
is about the shim's light value, and the claim is only about presence, so this is a limitation of
scope, not a false claim. **Fix (optional):** when a block's `--em` and `--bg` are both literal
colours, refuse below 4.5:1. `gen-dashboard.py:contrast_ratio` already exists. Otherwise, write
the presence-only bound into the docstring and §2.

### MINOR 3 — a statement at-rule before a palette makes the scanner read that palette as an at-rule, and the check fails OPEN

`scripts/brief-compose.py:437-441`. `prelude` runs from the last `{`/`}`, so in
`@import url(…); :root[data-theme="dark"]{…}` the prelude starts with `@` and is pushed onto the
at-rule stack. The rule's declarations are never read. Reproduction: insert
`@import url("https://fonts.googleapis.com/css2?family=Inter");` and then
`:root[data-theme="dark"]{--bg:#16151a;--fg:#ece9e3}` (no `--em`) at the top of the progress
fragment's `<style>`. The result is **COMPOSED**. The control, the same block without the
`@import`, is **REFUSED**. `@charset`, `@namespace` and `@layer a, b;` take the same path. A Google
Fonts `@import` is a plausible thing for a fragment to carry. **Fix:** when a `;` appears at depth 0
outside a block, reset `start` past it. Equivalently, take the prelude from the last `;`, `{` or
`}`. Add a case for it.

### MINOR 4 — CSS nesting fails OPEN, and the docstring's next sentence reads as if it fails closed

`scripts/brief-compose.py:426-430`. The bound ("a rule body is read to its first `}`") is stated.
The sentence after it, "the refusal below fails CLOSED on an empty result rather than passing it",
is true only when the result is EMPTY. A nested dark block inside a palette that does declare
`--em` leaves the result non-empty and passes. Reproduction: append
`:root{--bg:#fbfaf7;--em:#2d4a7c;@media (prefers-color-scheme: dark){&:not([data-theme="light"]){--bg:#000;--fg:#eee}}}`
to the progress fragment. The result is **COMPOSED**, and the nested dark block is never asked for
`--em`. Native nesting ships in every current browser. **Fix:** say "fails OPEN on nesting" in so
many words. Better, refuse when a `{` appears inside a palette rule's body before its `}`, so the
bound fails closed the way the docstring implies.

### MINOR 5 — three false refusals (loud, so cheap, but each is a correct page)

`scripts/brief-compose.py:443-446`. Each one reproduced through `assert_em_in_every_palette` and,
for the first two, through a full `compose` of the progress fragment:
- `:root{--bg:#fff}` and `:root{--em:#2d4a7c}` as two rules in the same context are **REFUSED**.
  Each rule is judged alone.
- `:root .card{--bg:#eee}` is **REFUSED**. `re.match(r"(:root|html)\b")` accepts any selector that
  merely STARTS with `:root`, so a component that re-grounds a card is asked for `--em`. `html body`
  is accepted the same way.
- `:where(:root){--bg:…}` with no other block gives **CANNOT VERIFY**.

**Fix:** key the blocks on `(at-rule stack, selector)` and merge their declarations before testing.
Match the whole compound selector (`^(:root|html)(\[[^\]]*\]|:not\([^)]*\))*$`) so descendants are
excluded.

### MINOR 6 — the dashboard entry still says browser verification is to do

`docs/dashboard-entries.md:17969`: *"Browser verification is still to do."* Commit `9aa3b909`
closed backlog #376 as *"browser-verified 2026-10-27 by the coordinator"*, and the browser check
reproduces (above), so the entry is now false. The rest of the entry's numbers hold: 7 of 7 pages
with a Theme button get the switcher, 16 of 24 get no Theme bar, 66 tracked pages minus 24 with
fragments leaves 42 without one, and 8.45:1 / 9.04:1. **Fix:** replace that sentence with the
verification result, or append a correction entry.

### Note (not a finding) — the default wrap changes body text colour on every page it reaches

`.ex-body{color:var(--prose)}` (from `text_style_css`) now covers the whole body. On the progress
page, prose moves from `--fg` to `--fg2` (5.32:1 dark, 5.50:1 light), and the `<b>` inside
`.horizon`, `.reading` and `.howto` (8 elements) changes from the inherited muted colour to `--em`.
This is the scheme working as designed. I mention it because claim (3) ("the only differences are
the wrapper…") is true of the TEXT while the rendering of every prose line changes. A future
fragment that writes `<p class="warn"><b>…</b></p>` and lets the `<b>` inherit the warning colour
will see it turned `--em` by `.ex-body b` (0,1,1, emitted later). §2 forbids spending semantic
colour on bold, so this matches the contract.

VERDICT: NOT CONVERGED
