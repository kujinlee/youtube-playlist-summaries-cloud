# chrome-bar-reachable — round 3 coordinator note

```yaml
round: 3
fixes_nontrivial: true
subject: chrome-bar-reachable
halves:
  codex: ran
  claude: "GAP: not invoked for round 3 — the r3 Codex half: single-reviewer round BY CONSTRUCTION, under the alternation rule"
findings:
  - {id: B1, severity: Blocking, aim: instrument, fix_induced: true, component: page_chrome, disposition: fixed}
  - {id: M1, severity: Medium, aim: instrument, fix_induced: true, component: page_chrome, disposition: fixed}
  - {id: M2, severity: Medium, aim: instrument, fix_induced: true, component: page_chrome, disposition: fixed}
  - {id: M3, severity: Medium, aim: instrument, fix_induced: true, component: page_chrome, disposition: fixed}
  - {id: M4, severity: Medium, aim: instrument, fix_induced: true, component: page_chrome, disposition: fixed}
  - {id: L1, severity: Low, aim: instrument, fix_induced: true, component: page_chrome, disposition: declined}
```

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

* ⟳ **CORRECTED BY r4 — this bound was understated.** It said the claim is narrowed to the
  emitter without saying that TWO OF THREE `chrome_for` branches fall outside it. Only
  branch 3 emits the scoped stylesheet; on branches 1 and 2 the composer emits none, so the
  caller fact is correctly False and the guard does not reach those pages at all. A switcher
  the composer did not dress is the FRAGMENT AUTHOR'S contract. That is not hypothetical:
  `2026-10-05-topic-why-x-not-y.fragment.html` is branch 2 today, with its own schemer, ZERO
  `ex-body`, and a correct consumption layer written as bare `body` / `h1,h2,h3,h4` /
  `b,strong` — so any content-side test for the class refuses a working page. An
  `or … in content` disjunct was tried and REMOVED: a spaced copy defeats an exact match, so
  it bought no coverage while re-entering the r2/r3 oscillation.
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

## Header provenance — backfilled 2026-10-24 (backlog #306), DERIVED, not remembered

This header was absent for five days and is written from three sources, none of them recall: the
round's Codex half (`codex/chrome-bar-reachable-r3-codex.md`, the findings and severities), this
note's own *Introduced by* table (`fix_induced`), and the fold commit `03b78e94` (dispositions).

* **Ids, in the half's order:** B1 equivalent CSS defeats the consumer guard · M1 the template's
  own id hidden · M2 `dict(attrs)` last-wins · M3 `<noscript>` contents counted live · M4
  `@media not all{…}` accepted · L1 a fifth masking mutation pair.
* **`fix_induced`:** the table above marks B1 and M1–M4 *r2 fold*. ⟳ **L1 corrected to `true`
  in round 1 of this backfill's review**: it had been set `false` because L1 is absent from the
  table, which is an inference from absence. Git says otherwise — half of L1's masking pair,
  *"a finished document is exempted like a fragment"*, was added by the r1 fold `d2e5db17` with
  the `_is_document(page)` branch it mutates. Under the template's wording (*a fix written after a
  previous round*) that is `true`; under the narrower thrashing reading (the PREVIOUS round's fix
  only) it would not be, so it is a judgement, made here by the template's wording. The header now
  reads **6 of 6** against this note's table, which counts 5.
* **`aim: instrument` for all six:** every finding is in `assert_wired` / `missing_text_consumer`
  or the cases and mutations that defend them — a guard over the page, not the page.
* **`disposition`:** `03b78e94` folds B1 (the caller supplies `scoped_css_emitted`) and M1–M3 on
  Chromium's semantics, and narrows M4's claim to the emitter, where the r3 attack now reddens.
  L1 is **declined**: *"pair-coverage NOT claimed"* — real, and not being fixed.
* **`fixes_nontrivial: true`:** the fold changed the guard's contract (a new caller-supplied fact).
* **`halves.claude`:** no Claude half exists for r3, and the Codex half says why in its own words.
  The field quotes that reason only. The later reading — that alternation means a pair per
  round, which would make this round incomplete — is backlog #339's, and is undecided.
