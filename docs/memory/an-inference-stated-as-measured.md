---
name: an-inference-stated-as-measured
description: "FIRES-WHEN: about to write MEASURED, state a figure that supports your own argument, say an agent did NOT see something, or brief a fold on a cost trade-off — ⭐⭐ a plausible inference written as if measured, caught by the NEXT round, never the author. The fix is PARAGRAPH STRUCTURE, not \\\"verify agent output\\\""
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0cfd7079-9c4f-4f89-9a59-337f426f6311
  modified: 2026-10-19T19:52:11.279Z
---

**RULE: label the measurement, and put the inference in its own sentence.** Not as style — it is the only
mechanism that has worked. A paragraph that runs *correction → transcript → inference → recommendation*
with no seam hides the inference from its own author while the next reader sees it at once.

**How to apply:**
- **Separate measured from inferred.** A fence reads as captured output, so write *"(summary of a
  measurement, not a capture)"* when it is not.
- **An argument that needs a cost figure is suspect.** The defects below were *supporting* numbers
  invented for a conclusion that stood without them. Fixing the fact can fix a design (#156's
  "reject invocations in conditional steps" would have red-lined two live PR-only gates).
- **When a disposition trades correctness for COST, put a number on the cost before briefing** — and
  keep a STOP clause in fold briefs.
- **An agent's FILE is not a record of what it RECEIVED.** Before saying an agent *did not* see or
  address something, ask it (`SendMessage`) or check it is finished, or write *"not in its filed
  document as of HH:MM, and it may still be working"*. *"It addressed X"* is checkable from the file;
  *"it did not address X"* is not.
- **Correct EVERY site, and check.** Grep for the wrong string after fixing it.
- **Prefer locators that do not shift** — line anchors over ordinal indices.

**Why:** the obvious lesson — *verify agent output* — already existed as a rule I had quoted at the start
of the task that failed. Having the rule did not help; the paragraph structure did.

## History
- **2026-09-21, backlog #153 architecture review (PR #329):** the three repair rounds each found a defect
  in the repair before it, all this class. r2: *"no guard invocation sits inside a conditional step"* —
  two do (a reviewer's claim, never re-run). r3: *"rejecting them would red-line two guards that genuinely
  run"* — measured cost **0** (mine). r4: twelve mutation entries as `#26–#37` — 0-based, so the ordinal
  reading moves the wrong anchor (mine, in the backlog row). r3 itself said splitting measured from
  inferred "would have made R3-2 visible to its author." The rounds were NOT thrashing (independent new
  subjects); three rounds each finding another unbudgeted cost meant review had become the wrong
  instrument — see [[cost-is-not-the-objective-improvement-is]].
- **2026-10-19:** I read a running review half's filed review, found two findings I had sent it absent,
  and published "this finding has been reviewed by nobody". Within six minutes it filed a 195-line
  addendum, confirmed one finding with better evidence, and refuted two of my conclusions.
- **2026-11-10, plan-586 r5:** I wrote "removing `settled` costs calls, not correctness" and briefed a
  fold on it. Unmeasured: ~50,000 calls/day vs 1,000/hour, so the report never finishes. Caught only
  because the brief said STOP if removal breaks something.

Related: [[a-mutation-loses-its-binding]], [[a-retrospective-number-needs-provenance]],
[[quote-the-code-dont-characterise-it]], [[concurrent-agents-go-wrong]],
[[ask-an-agent-to-refute-not-confirm]], [[a-harness-cannot-read-a-cause-from-a-childs-text]].
