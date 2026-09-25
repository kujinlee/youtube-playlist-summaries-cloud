# Round 1 — `round-record-substrate` — coordinator

```yaml
round: 1
fixes_nontrivial: true
subject: round-record-substrate
halves:
  codex: ran
  claude: ran
findings:
  - {id: B1, severity: Blocking, aim: deliverable, fix_induced: false, component: header-schema, disposition: fixed}
  - {id: B2, severity: Blocking, aim: instrument, fix_induced: false, component: conversion-falsifiers, disposition: fixed}
  - {id: H1, severity: High, aim: deliverable, fix_induced: false, component: roundtrip-evidence, disposition: fixed}
  - {id: H2, severity: High, aim: deliverable, fix_induced: false, component: roundtrip-evidence, disposition: fixed}
  - {id: H3, severity: High, aim: deliverable, fix_induced: false, component: scope-entanglement, disposition: fixed}
  - {id: H4, severity: High, aim: instrument, fix_induced: false, component: validate-unfalsified, disposition: fixed}
  - {id: H5, severity: High, aim: deliverable, fix_induced: false, component: no-fallback-migration, disposition: fixed}
  - {id: M1, severity: Medium, aim: instrument, fix_induced: false, component: selftest-retirement, disposition: fixed}
  - {id: M2, severity: Medium, aim: instrument, fix_induced: false, component: manifest-retirement, disposition: fixed}
  - {id: M3, severity: Medium, aim: deliverable, fix_induced: false, component: authoring-cost, disposition: fixed}
  - {id: M4, severity: Medium, aim: deliverable, fix_induced: false, component: prior-art-evidence, disposition: fixed}
  - {id: M5, severity: Medium, aim: deliverable, fix_induced: false, component: migration-cutover, disposition: fixed}
  - {id: M6, severity: Medium, aim: instrument, fix_induced: false, component: defect-inventory, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: false, component: deletion-size, disposition: fixed}
  - {id: L2, severity: Low, aim: deliverable, fix_induced: false, component: defect-inventory, disposition: fixed}
  - {id: L3, severity: Low, aim: instrument, fix_induced: false, component: authoring-cost, disposition: fixed}
```

**Verdict: NOT CONVERGED.** Both halves ran concurrently, which is round 1's measured-safe topology.

## ⭐ Both halves found the SAME Blocking independently, and it is the spec's central claim

The draft split the world two ways — `json.loads` handles *structure*, `_validate` handles *values* —
and asserted the six recorded defects land cleanly on those two sides. **There is a third layer, and
everything in it lives inside the region marked for deletion:** the `round:` presence/int check
(`:203-205`), the refusal of an absent `findings:` key (`:232` — the explicit repair for r3's
Blocking), and the `ROUND_REQUIRED` enforcement loop (`:245-251`; the constant at `:263` enforces
nothing). `_validate` is **per-finding only** and never sees a top-level key.

```
{"round": 1, "fixes_nontrivial": false}   ->  decide() = STOP
{"round": 1, "findings": []}              ->  decide() = STOP
```

⛔ **The design as written fired its own falsifier** — the spec's own *"How we would know it failed"*
names exactly this. Folded: §1 now names **three** layers and schema validation is **built**, not kept.

## ⭐ The second Blocking is a TEST THAT CANNOT FAIL, in the paragraph being careful about that

Both pre-committed falsifiers were unable to fire on the hazard §2 calls *"the one real hazard"*.
The parity check is vacuous by construction — `parse_header:243-246` already enforces it, **0
disagreements across 30** — and making it independent reintroduces r2's fixed Medium. Verdict
invariance collapses a record to one of five strings, of which the corpus produces **two**. A comma
inside a quoted `component` is silently truncated by `_scalarise`, and **both falsifiers pass**.
Replaced with a **field-level text diff** of source header against converted JSON.

## The halves did NOT split the way round 1 of the previous spec did

| Half | Found |
|---|---|
| **Codex** | 2 Blocking, 2 High, 3 Medium, 2 Low — including the schema Blocking, by construction |
| **Claude** | 2 Blocking, 4 High, 5 Medium, 2 Low — the same two Blockings, plus the #187 entanglement and the unfalsified `_validate` |

⭐ **Overlap on both Blockings, disjoint below.** The previous spec's r1 produced a clean numeric /
structural split; this one did not, and one round is not a trend. What did repeat: **a High from each
half faulted a measurement the coordinator had stated as measured.**

## ⛔ Three coordinator measurements were wrong, and two failed the same way

| claimed | true | cause |
|---|---|---|
| 0 headers use a YAML comment | **1** does | the pattern was `^\s*#` — line-start only; the real one is inline |
| `check-review-rounds.py` has no reference to `halves` | it defines **`HALVES`** and uses it twice | the grep was case-sensitive and lowercase |
| 121 lines deleted | **109** for the named set | the measurement included `_validate`, which the spec keeps |

**The first two are one failure: the pattern did not match what the claim was about.** The third is a
set-vs-set error. ⭐ *Measure the population the code actually sees* — three instances, one round.

## What survived

The substrate choice. Both halves independently confirmed that `pyyaml` and vendoring are correctly
rejected, that `json.loads` is the right answer to #117, and the corpus counts 30/42/39 and the
block-scalar count of 0 reproduce exactly. **The decision is intact; the reasoning around it was not.**

## ⛔ A LIVE INSTANCE OF THIS ROUND'S OWN M5, FOUND BY USING THE TOOL

```
$ python3 scripts/check-review-decision.py
ROUND_OWED — no round recorded; a one-round change needs at least one
  branch=backlog-117-parser-substrate  scope=one-round  rounds=0
```

**The card cannot see this round.** `rounds_for()` globs `docs/reviews/coordinator/<subject>-r*-…`
where `<subject>` is the **current branch name** — `backlog-117-parser-substrate` — while these
documents use the subject stem `round-record-substrate`. `check-review-rounds.py` pairs them fine
(rc=0), because it keys on the basename; the decision card is blind.

⭐ **This is M5/H5 (`migration-cutover`, *`rounds_for` reads the branch name*) reproduced by accident
on the branch that filed it**, and it is a second reason the no-fallback cutover needs a stated
mechanism rather than a principle.

⚠ **Deliberately NOT fixed by renaming.** The Codex half's verdict file
(`docs/reviews/verdicts/round-record-substrate-r1-codex.verdict.json`) stamps the review id that CI
joins on — backlog #176's lesson — so a rename to satisfy one reader would break the other. Recorded
as evidence instead of papered over; the fix belongs with M5.
