# Round 1 — `decision-card-soundness` — coordinator

```yaml
round: 1
fixes_nontrivial: true
subject: decision-card-soundness
halves:
  codex: ran
  claude: "GAP: not dispatched — coordinator ran a single half at the Phase 1 spec gate; declared, not excused"
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: false, component: cost-evidence, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: false, component: escape-grammar, disposition: fixed}
```

REVIEW GAP: claude — not dispatched. Round 1's protocol is both halves concurrently and only Codex was run. This is a deviation by the coordinator, not a half that could not run, and it is declared here so the human can require the second half before approving the spec.

## What the review VERIFIED by reproducing — the spec's foundation holds

- ⭐ **The measured defect reproduces exactly.** Replaying the shipped `thrashing_component` over
  `velocity-doc-consistency`: `None` at r2/r3/r4 as labelled; `overclaim` at r2/r3/r4 with the three
  synonyms merged.
- **The calibration re-derives**: 7 subjects / 28 rounds / 145 findings / 11 fires / 5 would-refuse /
  3 on `velocity-doc-consistency`.
- **The registry rejection re-derives**: 83 distinct names, 56 singletons (67.5%), **0** shared
  across subjects.
- **"No architecture review was ever convened upfront" holds** — it checked every file's stated
  trigger.

## H1 — the cost evidence was materially wrong, and wrong in this spec's own signature way

The spec claimed architecture reviews run **122–386** lines against a **471**-line round, *"roughly
0.3–0.8 of one round"*.

⛔ **It excluded the 856-line `observer-family` review from the range it belongs to** — after that
review had already been established as thrashing-armed. **The largest member of a population,
dropped from its own range, in a spec about population errors.** The round median was also 471 from
`split("\n")` against 469 by `wc -l` — the same method-not-stated slip.

**Corrected:** 122–856, median 263.5 (n=12) against a median 469-line round — **~0.5 of a round,
range 0.26–1.83**. *Typically cheaper than a round* survives; *always cheap* does not.

⚠ **And the outlier is explained by SCOPE, not lateness** — `observer-family` covered a family across
two slices and says so. So *"triggered reviews are shorter"* is really *"a review's cost tracks its
scope"*, and a triggered review usually has a narrower scope because it is handed its subject. The
Q0 conclusion survives on the corrected basis; its stated reason changes.

## M1 — the escape grammar was pair-shaped while the condition is set-based

The refusal names every fix-induced component on each side, and real refusals are **not pairs**:
`velocity-177` r2 is **7-vs-1**, `peer-sites` r4 is **2-vs-3**. A pair-shaped
`COMPONENTS DISTINCT: <a>, <b>` would let an **honest but incomplete** declaration satisfy an
implementation while leaving another plausible synonym pair unjudged — **worse than the dishonest
declaration the spec already admits, because nobody involved would know it had happened.**

**Fixed by removing component names from the declaration entirely.** The refusal has already printed
both sets; the line asserts over the whole cross-product. **There is no partial form to get wrong.**
