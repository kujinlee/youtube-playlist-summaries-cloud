---
name: an-inference-stated-as-measured
description: "FIRES-WHEN: about to write MEASURED, or state a figure that supports your own argument — ⭐⭐ THREE times in ONE document, each caught by the NEXT round, never the author — a plausible inference written as if measured. The fix is PARAGRAPH STRUCTURE, not \\\"verify agent output\\\""
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0cfd7079-9c4f-4f89-9a59-337f426f6311
  modified: 2026-09-22T01:00:01.460Z
---

**Measured 2026-09-21** on the backlog #153 architecture review (PR #329). Four review rounds; the
three *repair* rounds each found a defect in the repair before it, and **all three were the same
class**: a plausible inference written in the grammar of a measurement.

| round | the sentence | whose inference |
|---|---|---|
| r2 | *"no guard invocation sits inside a conditional step"* — two do | a reviewer's, taken and **never re-run** |
| r3 | *"rejecting them would red-line two guards that genuinely run"* — measured cost is **0**; both have a second unconditional invocation | **mine**, inside the paragraph repairing r2's |
| r4 | the twelve mutation entries as `#26–#37` — 0-based, so the ordinal reading moves the wrong anchor and drops a needed one | **mine**, in the backlog row an implementer would follow |

**Why:** the obvious lesson — *verify agent output* — is the wrong one, and it already existed as a
rule I had quoted **at the start of that very task**. Having the rule did not help. What produced all
three is that each sentence sat in a paragraph that ran *correction → transcript → inference →
recommendation* with no seam, so **the inference was invisible to its own author** while being
perfectly visible to the next reader. r3 said this explicitly: splitting measured from inferred
"would have made R3-2 visible to its author."

**How to apply:**

- **Label the measurement and put the inference in its own sentence.** Not as style — as the only
  mechanism that worked. A fence in a document reads as captured output, so write *"(summary of a
  measurement, not a capture)"* when it is not.
- **An argument that needs a cost figure is suspect.** All three defects were *supporting* numbers
  invented for a conclusion that stood without them. The statically-false-vs-event-scoped distinction
  was right on its merits; the "two red-lined guards" was decoration that happened to be false.
- **Fixing the fact can fix a design.** #156 said *reject invocations in conditional steps*; that
  would have red-lined two live PR-only gates. The false claim was hiding a design error.
- **Correct EVERY site, and check.** r3 fixed the locator in the review and left it in the backlog
  row — r4's whole finding. Grep for the wrong string after fixing it.
- **Prefer locators that do not shift.** Line anchors over ordinal indices. Related:
  [[a-mutation-loses-its-binding]], [[a-retrospective-number-needs-provenance]],
  [[quote-the-code-dont-characterise-it]], [[concurrent-agents-go-wrong]].

⚠ **The rounds were NOT thrashing** by this repo's definition, and saying so mattered: r3-1/r3-3/r3-4
were independent new subjects, not consequences of a previous fix. The stop signal was different —
three rounds each finding another *unbudgeted implementation cost* meant review had become the wrong
instrument for the remaining question. See [[cost-is-not-the-objective-improvement-is]].
