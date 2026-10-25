# Architecture review — light-palette detection from text (backlog #300 → #349)

> **Anchor:** `explanation-on-demand`

**Armed by THRASHING**, per `docs/dev-process.md` Phase 6: *two consecutive rounds whose findings came
from the previous round's own fix, in one component*. On `comprehensibility-chrome-cases`, the
component `palette-detection` carried fix-induced findings in round 2 (Codex H1, M2: r1's route) and
round 3 (Claude F2: r2's tokenizer). Convened by the coordinator at `6fd6ae32`, the same evening,
while the owner was away. ⚠ **Coordinator-authored, not a separate reviewer** — it is the decision
record for a retreat, and its one load-bearing claim (below) is checkable by anyone from the three
round documents.

## The question

`missing_palettes` reports `['light']` for six committed pages whose theme button WORKS (both r1
halves, Chromium, OS-dark: one press gives `rgb(247, 245, 241)`), because their light palette is the
bare `:root` default with the OS-dark block gated by `:root:not([data-theme="light"])`. The composer
therefore composes them stamp-only, and recomposing removes a working control. **Can a text predicate
decide that such a page's light press works?**

## What three rounds measured

| Round | Rule | Accepted but dark when light is pressed | Refused though it works |
|---|---|---|---|
| r1 (literal, `master`) | `:root[data-theme="light"]` present | — | the six pages |
| r1 fold | exclusion present + top-level default present | r2 Codex: plain `:root` beside an unrelated exclusion | r2 Codex: `@layer base;`, a quoted `{` |
| r2 fold | every token-declaring dark rule is exactly the exclusion, over a tokenizer | r3 Claude: 7 shapes (non-token dark rule, `@media not (…light)`, nested `@media`, `<style media>`, escapes, `not all and`, an unterminated string) | r3 Claude: 9 shapes (unquoted/single-quoted attribute, `:ROOT`, `html:root`, `@layer` default, selector lists, `:where`, nesting, `:root,:host`) |

Each fold closed the shapes named and opened or exposed others in **both** directions. Every row in that
table is a shape somebody constructed and rendered in Chromium; none is reasoned.

## Finding

**The predicate is evaluating a cascade.** Whether pressing light changes the rendering depends on
media-query evaluation, specificity, nesting, at-rule layering and `<style media>` — exactly what a
browser computes and a string rule approximates. That is the same verdict the 2026-10-19 review
reached for *reachability* (`architecture-review-2026-10-19-chrome-reachability-instrument.md`,
route C), arrived at independently from a second property. **A redesign inside text cannot remove
it; it can only move the boundary.** So the next rung is SPLIT, not another fold.

## Decision

- **SPLIT.** The text route is reverted; `missing_palettes` is byte-identical to `master`. The six
  pages are restored to `master` (working, unpinned) rather than recomposed. The unit is filed as
  **backlog #349**, with two admissible resolutions: decide liveness in Chromium (backlog #304
  route C), or a deliberately narrow WHITELIST grammar that accepts one exact authored shape and
  refuses the rest. Choosing between them is design work for a spec, not a fold.
- **What ships** is independent of it: the stub-page execution cases (backlog #305), the `ctls`
  case (backlog #304 task 0), the one page whose palettes are literal, and the comment (backlog #105).
- **What this review did not do:** it did not choose between the two resolutions, and it did not
  re-review the stub page, whose findings in rounds 1–3 were in a different component and are folded.

## What did we decide that isn't written down?

That a composer's *"will I add a control?"* decision and `missing_palettes` should agree. They do not
(r3 F6: `brief-compose.py`'s substring test vs the CSS-reading predicate). Now written, on backlog #349.
