---
name: exercise-the-producer-at-two-distinct-inputs
description: "FIRES-WHEN: writing a case that asserts a derived value — ⭐⭐ A case asserting a derived value is satisfied by the CONSTANT its own fixture supplies — 3 rounds, 9 survivors, and a case literally named \\\"catches a hardcoded message\\\" was satisfied by a hardcoded message"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e8d4fa1c-667d-4d08-bd64-55931cd5a12f
  modified: 2026-09-22T21:21:36.020Z
---

Measured over rounds 3–5 of the `unheralded` banner-guard review (branch
`banner-work-without-banner`, 2026-09-22). **Eleven** freezable derived-value sites in one delivered
file; **nine single-edit constant-freezes survived** a 150-case suite. For three consecutive rounds a
case named *"catches a hardcoded message"* was satisfied by a hardcoded message.

**Why:** a case that calls its producer ONCE and asserts the literal that call supplies is satisfied
by the constant equal to that literal. Every repair that targets the *value* rather than the
*property* just changes **which** constant survives:

| Round | Repair attempted | What actually happened |
|---|---|---|
| r4 | moved the fixture off the threshold (`_BIG` → `LARGE_TURN + 3`) | `LARGE_TURN + 3` became the surviving constant — **the fix created the survivor** |
| r4 | made asserted values pairwise-DISTINCT across cases | a property of *having two call sites that disagree*; held for 2 of 11 sites, by coincidence |
| r4 | added one manifest entry per value found | an entry pins the constant that was **tried**, not the class |

⭐ **THE PROPERTY THAT ENDS IT — one rule, not more probes:**

> **a case asserting a derived value must exercise its producer at two DISTINCT inputs.**

No constant satisfies an assertion evaluated at two different inputs. Crucially it also holds
**COMPONENT-WISE**, which pairwise-distinct fixtures do not: both cases reading `STEP {i} of {N}`
used step 2 (`STEP 2 of 5`, `STEP 2 of 3`), so all the distinctness lived in the total and freezing
**only the step half** survived — every log entry would have said step 2 forever.

**How to apply:**
- ⛔ **Both drives go in ONE case.** Two cases with different fixtures is the weaker property that
  already failed. A composite value needs both components varying *inside the assertion*.
- **Enumerate the population MECHANICALLY** (grep/`ast` every interpolation of a derived quantity),
  never by eye. r4 swept "7 probes over every derived value" and had reached 3 of 11 — see
  [[a-measurement-is-only-as-good-as-its-corpus]].
- For an **integration-only** producer, find the cheapest knob that moves its inputs without moving
  the verdict (here: padding a turn with banner-free prose moved 1/2/1 → 3/6/3).
- ⚠ **`check-fixture-variation.py` is NOT this rule and does not subsume it** — measured. It asks
  *do two CASES pass different values for a PARAMETER?*; this asks *does ONE CASE exercise a producer
  at two inputs?* Filed as backlog **#164** to decide whether to mechanise it.
- This class firing three rounds running is what tripped the pre-committed thrashing condition.

See [[a-case-can-pass-for-an-ambient-reason]] (the *environment* sibling of this),
[[a-test-that-cannot-fail]], [[assert-the-property-not-the-mechanism]],
[[a-filed-finding-s-proposed-fix-is-a-hypothesis]], [[after-fixing-search-for-the-class]].
