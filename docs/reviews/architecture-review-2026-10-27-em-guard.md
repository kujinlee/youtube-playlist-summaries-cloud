# Architecture review — 2026-10-27 — the `--em` palette guard (backlog #376)

**Convened by THRASHING** (`docs/dev-process.md`): rounds 2 and 3 of `text-style-default` both carry findings caused by
the previous round's own fix, in one component — the palette guard in `scripts/brief-compose.py`. Round 2's X1–X3 came
from round 1's scanner; round 3's false refusal (Codex X2 = Claude F4) came from round 2's per-theme-state model, and its
alias acceptance (X1 = F1) from the `var()` resolution round 2 kept.

## What thrashes — and why a redesign can remove it

Every finding in rounds 1–3 is the same attempt: **predict the RENDERED page from its source text** — selector parsing,
importance, context precedence, stylesheet order, which element paints the ground, which rule colours the bold. That is
the CSS cascade re-implemented in Python, and each round's fix to its precision produced the next round's findings, in
both directions (false accepts at 1.00:1, false refusals of pages that render 7.5–16:1).

**A redesign removes it: stop predicting.** Split the guard's two jobs:

1. **The measured trap — keep, statically, because it is decidable from text.** The 2026-10-24 defect was a page whose
   palette block simply OMITTED `--em`, so bold fell back to the shim's light value in OS-dark (1.78:1). Checking that every
   canonical palette block declares `--em` as a literal colour is exact, needs no cascade, and is what the owner's request
   (#376: the switcher on by default) actually depends on.
2. **Rendered readability — move to an instrument that renders.** Drive the composed page in headless Chromium in every
   OS-scheme × pressed-theme state and measure bold against the background it actually sits on. That catches every
   round-3 shape (aliases, other-selector grounds, bold recoloured outside `--em`, stylesheet order) by construction,
   because it reads the browser's answer instead of re-deriving it. It is its own subject (filed as the next free backlog row).

## Decision (owner's standing AFK rule — not critical)

PR #422 ships the stable half: the composer default, the own-switcher enforcement, the canonical-format lint for the
measured trap with literal-hex `--bg`/`--em`, and NO per-state model and NO rendered-readability claim. The rendered check
is filed. ⚠ **Falsifier for this decision:** if a page composed after this ships with bold below 4.5:1 that §5b browser
verification did not catch, the split left the guarantee with no owner — the rendered check is then overdue, not optional.
