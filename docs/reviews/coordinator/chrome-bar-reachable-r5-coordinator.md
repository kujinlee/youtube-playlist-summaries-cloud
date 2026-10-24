# chrome-bar-reachable — round 5 coordinator note

```yaml
round: 5
fixes_nontrivial: true
subject: chrome-bar-reachable
halves:
  codex: ran
  claude: "GAP: not invoked for round 5 — the r5 Codex half: single-reviewer round BY CONSTRUCTION, under the alternation rule"
findings:
  - {id: H1, severity: High, aim: instrument, fix_induced: true, component: page_chrome, disposition: declined}
  - {id: H2, severity: High, aim: instrument, fix_induced: true, component: page_chrome, disposition: declined}
  - {id: M1, severity: Medium, aim: instrument, fix_induced: true, component: page_chrome, disposition: fixed}
  - {id: M2, severity: Medium, aim: instrument, fix_induced: true, component: page_chrome, disposition: declined}
  - {id: M3, severity: Medium, aim: instrument, fix_induced: true, component: page_chrome, disposition: fixed}
  - {id: M4, severity: Medium, aim: instrument, fix_induced: true, component: page_chrome, disposition: declined}
  - {id: M5, severity: Medium, aim: instrument, fix_induced: true, component: page_chrome, disposition: declined}
  - {id: L1, severity: Low, aim: instrument, fix_induced: true, component: page_chrome, disposition: declined}
```

## Verdict: STOP PATCHING THE PARSER. Five generations is the evidence, not a feeling.

Round 5 found **no Blocking**, 2 High, 5 Medium, 1 Low — and **every one is in the
`_Scan` parser introduced by round 4's fold**, which itself existed to fix round 3's
substring predicates, which existed to fix round 2's, which existed to fix round 1's.

| Round | Findings caused by the previous round's own fix | Component |
|---|---|---|
| r2 | 4 | `page_chrome.py` |
| r3 | 5 | `page_chrome.py` |
| r4 | 3 of 8 (the id predicates r2 left behind) | `page_chrome.py` |
| r5 | **7 of 8** | `page_chrome.py` (`_Scan`, added in r4) |

## What I folded from r5, and why only these two

Two findings are **this module's own inconsistency**, not a guess about browser behaviour,
so they are unambiguous and were folded with cases and mutations:

* the first-wins attribute fix had reached ONE of three branches; `dict(attrs)` (last-wins)
  survived in the two early-return branches written in the same commit;
* the enclosing-shield check ran AFTER the branches it was meant to gate, so
  `<template><noscript id="chrome-theme">` recorded an id Chromium never creates.

## What I did NOT fold, and that is the decision

Five findings are all one shape: **my parser disagrees with Chromium**, each in a way I did
not anticipate and would have to guess at again.

* nested `<noscript>` — Chromium parses noscript content as raw text with scripting on, so
  nesting does not apply; my counter nests. (High, fail-open)
* an unterminated `<script>` contributes its marker here and does not run there. (High)
* `<svg><template>` — in foreign content the template is an SVG element and its child stays
  live; my shield hides it. (Medium)
* `<noscript><script></noscript>` — the scanner enters script mode before the terminator and
  then refuses a complete, working page. (Medium, fail-closed)
* `/* .chrome-pinned */ .nonexistent{position:fixed}` — `[^{}]*` spans a CSS comment.
  (Medium)

⛔ **Each is one patch away, and that is exactly the trap.** Rounds 1-5 each applied the
obvious patch and produced the next generation. A sixth would be the same move with the same
expected outcome, and `dev-process.md`'s thrashing rule exists to stop precisely this.

## The actual problem, stated once

`assert_wired` is trying to decide **what a browser will do with arbitrary markup** by
reading text. That is not a predicate text can compute. Every round has confirmed it from a
new direction, and five instruments have now been tried: substring, regex, comment-stripping
regex, `html.parser`, and a caller-supplied fact. Only the LAST one — being told rather than
sniffing — has survived a round without a defect.

## The fork for the owner — THIS IS A DESIGN DECISION, NOT A DEFECT

1. **Narrow the subject.** `assert_wired` runs on pages THIS REPOSITORY generates, not on
   adversarial markup. Declare that: it protects against generator mistakes, and every r5
   finding becomes out of scope by construction rather than unfixed. Cheapest, honest, and
   it makes the guard's claim match its callers. ⚠ But some r4 findings WERE reachable from
   a hand-authored fragment (single quotes), so "generator mistakes" must be defined to
   include the skill-authored fragments, not only the five generators.
2. **Move the claim to a rendering test.** The repository has Playwright. "Three options,
   three renderings" and "the bar is reachable" are both one browser assertion, and both are
   layout facts no text predicate can reach. Costs infrastructure; kills the whole class.
3. **Keep patching.** Rejected here, on five rounds of evidence.

**The Phase 6 architecture review armed at r3 is the right venue for this, and it remains
the owner's call.** I have not convened it.

## Bounds, unchanged and still true

Reachability is a MECHANISM assertion; the consumption claim is "no at-rule" and nothing
more; pair-coverage is not claimed (r5 found the sixth masking pair, within that exclusion);
branches 1 and 2 of `chrome_for` are outside the consumer guard.

## NOT RUN

Real-device phone, physical print, exhaustive parser or mutation-pair sweeps.

## Header provenance — backfilled 2026-10-24 (backlog #306), DERIVED, not remembered

Sources: the round's Codex half (`codex/chrome-bar-reachable-r5-codex.md`), this note's own
sections, and the fold commits `cfe586fb` and `8ea57020`.

* **Ids, in the half's order:** H1 nested `<noscript>` · H2 unterminated `<script>` · M1 the
  noscript branch's last-wins attributes · M2 `<svg><template>` foreign content · M3 shielded
  elements still contributing their own ids · M4 `<noscript><script></noscript>` · M5 the pin
  regex spanning a CSS comment · L1 a sixth masking mutation pair.
* **`fix_induced`:** this note's table says **7 of 8**, all in the `_Scan` parser round 4 added,
  and the half says the same of each of H1–M5 in its own words. ⟳ **The header reads 8 of 8, and
  L1 was corrected to `true` in round 1 of this backfill's review.** The first version called L1
  *"not something r4 wrote"*, and git refutes it: both the mutation in the pair (*"the pin
  selector must touch the brace again"*) and the grouped-selector case it masks were added by the
  r4 fold `4f4e2748`. So the header disagrees with this note's own count, as r6's does with its.
* **`halves.claude`:** the field quotes the Codex half's own reason only. That alternation
  might instead mean a pair per round is backlog #339's question, and is undecided.
* **`aim: instrument` for all eight:** each is the guard's parser disagreeing with Chromium.
* **`disposition`:** M1 and M3 are the two this note folded. H1, H2, M2, M4 and M5 are the five it
  did *not*; the owner then chose option A — narrow the subject — and `8ea57020` records them as
  OUT OF SCOPE BY THE BOUND, each with a case that reddens if the scan is tightened: real, and not
  being fixed, so **declined**. ⚠ M5 was re-raised at r6 and fixed there (`38e31fc6`: *"r5 put
  `/* .chrome-pinned */` … out of scope … the bound is wrong for that one shape"*); this header
  records what r5 decided, and r6's header records the reversal. L1 is declined with the
  pair-coverage exclusion.
* **`fixes_nontrivial: true`:** a shared first-wins helper and a reordered shield check, with cases.
