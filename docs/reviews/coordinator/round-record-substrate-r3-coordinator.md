# Round 3 — `round-record-substrate` — coordinator

```yaml
round: 3
fixes_nontrivial: true
subject: round-record-substrate
halves:
  codex: ran
  claude: "GAP: superseded mid-round by the architecture review this branch pre-committed to"
findings:
  - {id: B1, severity: Blocking, aim: instrument, fix_induced: true, component: conversion-falsifiers, disposition: redesigned}
  - {id: B2, severity: Blocking, aim: deliverable, fix_induced: true, component: migration-cutover, disposition: redesigned}
  - {id: H1, severity: High, aim: deliverable, fix_induced: true, component: header-schema, disposition: fixed}
  - {id: H2, severity: High, aim: instrument, fix_induced: true, component: roundtrip-evidence, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: migration-cutover, disposition: redesigned}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: true, component: defect-inventory, disposition: filed}
```

**REVIEW GAP: claude — the pre-committed architecture review fired on the Codex half's Blocking and
was convened mid-round.** Its verdict **replaces §2 in full**, so a Claude half dispatched against
the old §2 would have reviewed a section that no longer exists. ⚠ **This is a deliberate gap with a
stated reason, not a skipped half**, and r4 reviews the narrowed spec with both halves.

⛔ **NOTE ON `disposition: redesigned`** — three findings carry a value `REQUIRED` does not admit, so
this document **will not parse** until backlog #187 widens the set. That is recorded rather than
worked around: *fixed* would be false (the mechanism was removed, not repaired) and *declined* would
be false (it was acted on). **This round is the fifth live instance of #187.**

## ⛔ THE PRE-COMMITMENT FIRED, AND THE REVIEW SAID THE PROBLEM WAS THE WRONG ONE

Four falsifier designs, four distinct failure modes, one component. The verdict is not a fifth
design: **the falsifier could not be built well because the operation it guarded was never owed.**

- **#117's WORK names three reshapings and no corpus.**
- **The corpus question is #119**, decided **2026-09-15**: *"none required if old branches simply
  drain"* — with backfilling *"rejected by the user … so it is not re-proposed as an obvious
  cleanup."* ⛔ **This spec re-proposed it under a different word and never cited the row.**

## And the record being protected has almost no reader

`rounds_for` keys on the **branch name**. Measured at `4118a592`: **32** parseable documents, **4**
reachable, **28** not. ⭐ **This branch is the proof** — `backlog-117-parser-substrate` ≠
`round-record-substrate`, so the card returns **0 rounds** for the very loop that produced these
records, and has done all along.

## What survived and what was cut

| | |
|---|---|
| **survives** | the substrate decision (fenced `json`), §1's presence/syntax/schema/values layers, the type-trap fixes, §3 |
| **cut** | the converter, the human-read artifact, `--calibrate`, the nine-key carry-through, the in-PR `disposition` widening, and **all four falsifier designs** |
| **replaced by** | a ~20-line projection comparator as a **committed fixture pair** — the only shape that survives `portable-practices` §26 |

⭐ **Every dead design asserted something about a LIVE corpus.** That is why each failed differently,
and why a fifth would have failed a fifth way.
