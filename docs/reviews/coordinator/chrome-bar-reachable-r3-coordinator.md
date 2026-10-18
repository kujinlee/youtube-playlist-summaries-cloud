# chrome-bar-reachable — round 3 coordinator note

## THRASHING OR PROSE FLOOR? — **THRASHING.** The condition in `dev-process.md` is met.

> fires when **two consecutive rounds carry findings caused by the previous round's own fix,
> in one component**

Per-finding evidence, component `scripts/page_chrome.py`:

| Round | Finding | Introduced by |
|---|---|---|
| r2 High | the consumer refusal blocks a working page | r1 fold |
| r2 Med | consumer substring accepts `ex-bodyguard`, rejects `class='ex-body'` | r1 fold |
| r2 Med | duplicate-id substring accepts mixed quoting, refuses a script literal | r1 fold |
| r2 Med | `_live()` regex strips LIVE markup between two script strings | r1 fold |
| r3 **Blocking** | `TEXT_CSS_SIGNATURE` sniff defeated by whitespace — **fail-open** | r2 fold |
| r3 Med | `<template>`'s own id hidden by the shielding | r2 fold |
| r3 Med | `dict(attrs)` last-wins vs Chromium first-wins | r2 fold |
| r3 Med | `<noscript>` contents counted as live | r2 fold |
| r3 Med | consumption cases accept `@media not all{…}` | r2 fold |

Two consecutive rounds, one component. **Not a prose floor** — these are code defects with
browser-verified failure scenarios, not wording.

## The test the doc prescribes: *can a redesign remove it?* — YES, and that is decisive

Every instance is ONE mistake: **deciding a runtime or layout property by matching text**.
`position:sticky` decided from an assumed document shape; a consumer decided by substring;
duplicate controls decided by `count()`; comments decided by regex; "my stylesheet is on this
page" decided by an exact-spelling signature. Each fix replaced one text predicate with
another and the class survived.

⛔ THE SIGNATURE PAIR IS THE PROOF THAT PATCHING CANNOT WIN. The escape existed so the guard
would not refuse a page shipping its own CSS (r2 High). Any TEXTUAL signature is defeated by
equivalent CSS (r3 Blocking). Tightening re-creates the cry-wolf; loosening re-creates the
fail-open. Two rounds were spent oscillating between them.

## What this fold did instead of patching a third time

**The guard stopped guessing and started being told.** `missing_text_consumer` /
`assert_wired` take `scoped_css_emitted` from the CALLER — the generator that just built the
page already knows whether it called `text_style_css()`. Spelling becomes irrelevant, and
BOTH failure modes dissolve at once: whitespace-equivalent CSS with no consumer is refused,
and a page shipping its own scheme CSS is not this guard's business. Verified both ways.

The parser findings are folded on Chromium's actual semantics, each measured, not reasoned:
first-wins duplicate attributes, the template's own id live while its contents are not,
`<noscript>` contents not live while scripting is on.

## Bounds, stated rather than implied

* **The consumption claim is narrowed to the EMITTER.** Deciding whether an arbitrary page's
  CSS is ACTIVE needs a CSS parser, and reaching for one would be the fourth round of the
  same mistake. "My own output contains no at-rule" IS decidable, so that is all that is
  claimed. A page that imports this stylesheet and then deactivates it is NOT covered.
* **r3 Low — a mutation PAIR masks a named case.** `--mutate` applies one edit at a time, so
  the harness cannot see combined mutants. All 38 individual entries are killed via their own
  case; pair-coverage is NOT claimed. Fifth masking pair found on this branch.
* **Reachability remains a MECHANISM assertion.** Layout facts are not in page text.

## NOT RUN by the coordinator

Real-device phone; physical print (print was verified by CSS-media emulation, with the bar
measured `position:static`, `padding-bottom:0`, and 0 overlapping elements); runtime-injected
markup; malformed-nesting and foreign-content parser variants.

## Verdict

**NOT CONVERGED.** Round 4 is warranted, and the thrashing arming condition for a Phase 6
architecture review is MET and recorded here for the owner's call.
