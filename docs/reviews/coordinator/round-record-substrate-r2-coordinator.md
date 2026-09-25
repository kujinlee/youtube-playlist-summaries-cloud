# Round 2 — `round-record-substrate` — coordinator

```yaml
round: 2
fixes_nontrivial: true
subject: round-record-substrate
halves:
  codex: ran
  claude: ran
findings:
  - {id: B1, severity: Blocking, aim: instrument, fix_induced: true, component: conversion-falsifiers, disposition: fixed}
  - {id: H1, severity: High, aim: deliverable, fix_induced: true, component: migration-cutover, disposition: fixed}
  - {id: H2, severity: High, aim: instrument, fix_induced: true, component: roundtrip-evidence, disposition: fixed}
  - {id: H3, severity: High, aim: deliverable, fix_induced: true, component: scope-entanglement, disposition: fixed}
  - {id: M1, severity: Medium, aim: instrument, fix_induced: true, component: selftest-retirement, disposition: fixed}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: true, component: header-schema, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: true, component: defect-inventory, disposition: fixed}
  - {id: B2, severity: Blocking, aim: deliverable, fix_induced: true, component: conversion-falsifiers, disposition: fixed}
  - {id: B3, severity: Blocking, aim: deliverable, fix_induced: true, component: conversion-falsifiers, disposition: fixed}
  - {id: B4, severity: Blocking, aim: deliverable, fix_induced: true, component: scope-entanglement, disposition: fixed}
  - {id: H4, severity: High, aim: deliverable, fix_induced: true, component: header-schema, disposition: fixed}
  - {id: H5, severity: High, aim: deliverable, fix_induced: true, component: conversion-falsifiers, disposition: fixed}
  - {id: H6, severity: High, aim: instrument, fix_induced: true, component: roundtrip-evidence, disposition: fixed}
  - {id: M3, severity: Medium, aim: instrument, fix_induced: true, component: migration-cutover, disposition: filed}
  - {id: M4, severity: Medium, aim: deliverable, fix_induced: true, component: header-schema, disposition: fixed}
  - {id: M5, severity: Medium, aim: instrument, fix_induced: true, component: selftest-retirement, disposition: fixed}
  - {id: M6, severity: Medium, aim: deliverable, fix_induced: true, component: defect-inventory, disposition: fixed}
  - {id: L2, severity: Low, aim: deliverable, fix_induced: true, component: conversion-falsifiers, disposition: fixed}
  - {id: L3, severity: Low, aim: deliverable, fix_induced: true, component: defect-inventory, disposition: fixed}
```

**Verdict: NOT CONVERGED.** ⛔ **4 Blocking, 6 High, 6 Medium, 3 Low — and 17 of 19 are
`fix_induced: true`.** The halves ALTERNATED: Codex ran against `bef49007`, its findings were folded
at `97bfcb8c`, and the Claude half then reviewed those fixes. That ordering is why this round found
what it found.

## ⛔ THE SAME COMPONENT FAILED THREE ROUNDS RUNNING, EACH TIME THROUGH ITS OWN FIX

`conversion-falsifiers` — the check that the migration did not silently alter the record:

| round | proposed | how it failed |
|---|---|---|
| spec | verdict invariance + finding-count parity | **could not fire** — `parse_header:243-246` already enforces parity; 0 disagreements corpus-wide |
| r1 fold | a field-level text diff | **could not be built** — distinguishing one field from two requires the parser being deleted |
| r2 fold | converter emits tables, a human reads them | **audited itself** — the *source* column was the broken reading, so it MATCHES on the exact case it exists to catch |

⭐ **`review-method.md`'s arming condition is MET.** Not convened, and the reason is recorded rather
than assumed: the method's test is *can a redesign remove it?* and here it can, **in one sentence —
the left column is raw source text.** ⛔ **Pre-committed: a fourth falsifier failing a fourth way
convenes the architecture review unconditionally.**

## The two Blockings that were one commit contradicting itself

- **B2** — §2 authorised the converter to parse *because it is deleted*; the cutover section, added in
  the **same commit**, made it **survive** so branches in flight could run it. The surviving one is
  the fact the design rests on. **Resolved by correcting the warrant, not the fact:** the converter
  survives, is never in the decision path, and therefore owes the full ratchet.
- **B4** — the new CI refusal (any coordinator document still carrying a `yaml` header fails) and the
  #187 deferral (keep `disposition` narrow) were decided in the **same fold**, each pricing its cost
  against a world the other removes. Together they make **5 committed documents permanently red** —
  unconvertible *and* refused, with no action available. ⛔ **#56's outcome.** Reversed: widen
  `REQUIRED["disposition"]` in this PR.

## What the alternating protocol bought

⭐ **The Claude half's three Blockings are all creatures of the Codex fold**, which a concurrent pair
would have missed entirely — neither half would have seen the other's fixes. This is the measured
case for `docs/plugins.md`'s *rounds 2+ ALTERNATE*.

## The coordinator's own drafts, faulted again

`_validate` has now been called *"kept, unchanged"* in **three** drafts and was wrong every time —
r1 found it **unfalsified** (gutting its missing-field refusal leaves `61/61` green), r2 found it
**mistyped** (written for a reader that could only produce `str` and `bool`; JSON hands it `int`,
`list`, `dict`, `null`). ⚠ **It is the least-examined load-bearing thing in this design**, and each
draft asserted it was fine rather than testing it.

And the population confusion returned **inside the paragraph written to fix it** — `31` restated as a
fixed fact four paragraphs after declaring counts unpinnable, when this branch's own round records are
inside the set being counted. **Replaced with a rule instead of a number.**
