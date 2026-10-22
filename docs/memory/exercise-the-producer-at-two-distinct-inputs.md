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

---

## ⟳ 2026-10-21 — THE FIX FOR A FINDING REINTRODUCED THAT FINDING, **inside its own replacement**, and survived 179/179

A review half found trigger 7 computing an accuracy bound over *scored rows* when the population
should be *ranker predictions* — it reported a sample of 10 where 8 predictions existed. I fixed it
by introducing a `sample` list and pinning the whole message with an identity case.

⛔ **Two mutations then survived the fixed suite**, found by the OTHER half:

| mutation | printed | why no case saw it |
|---|---|---|
| `len(sample)` → `len(rows)` in the message | `13 ranker predictions` over 10 — **the original defect, verbatim** | every t7 fixture had `len(rows) == len(sample)` AT THE MESSAGE SITE |
| `hits` over `rows` with `.get()` | `8 ranker hits` where 6 existed | same — and it restored the string-coercion defect too |

⭐ **The identity case was pinning the whole 100-character message and still could not tell the two
populations apart, because no fixture made them differ where the message is built.** A fixture that
cannot distinguish the old mechanism from the new one makes the fix **unfalsifiable** — and an
unfalsifiable fix lets the exact defect it repaired walk back in.

**How to apply — when a fix REPLACES a population, a producer or a mechanism:**
- Build one fixture in which the OLD and NEW things **differ at every site that reads them**. Here:
  10 eligible predictions PLUS ineligible extras (one with no field, one coerced `"yes"`, one
  retroactive) — so `rows` is 13 where `sample` is 10, and the message can only be right one way.
- ⛔ **Then sever the fix and check it reddens.** "The case passes" is not the claim; "the case
  fails when the fix is removed" is. I verified this only after a reviewer showed me the survivors.
- ⚠ **The old mechanism is still available to mutate** — `rows` did not stop existing when `sample`
  arrived. Ask: *could the old expression be substituted back in, and would anything notice?*
- Same session, same shape at a different scale: a parameter (`baseline_median`) passed `4` at all
  four call sites, so no case could tell the comparator from a literal — caught by
  `check-fixture-variation`, not by me. See [[a-sever-substitutes-todays-value]] and
  [[a-case-can-pass-for-an-ambient-reason]].
