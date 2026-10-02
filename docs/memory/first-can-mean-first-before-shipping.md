---
name: first-can-mean-first-before-shipping
description: "FIRES-WHEN: reading a roadmap or row that says do X FIRST — A roadmap saying \\\"close X FIRST\\\" can mean first-relative-to-shipping, not first-in-work-order — read the item's own trigger before ordering work from a pointer to it"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: dca6fb13-6aee-4a29-9254-0fa87e826497
  modified: 2026-08-23T00:01:24.082Z
---

MEASURED 2026-08-22 while ordering the blob-addressing blockers. The roadmap's unpark trigger says
**"Backlog #26 must be closed FIRST"**, and I recommended starting there. #26's own row says the
opposite: *"this must be closed BEFORE the schema ships to an environment where a worker calls
`record_artifact` … **Until then it costs nothing.**"* It is the **last** step, a ship gate — and it
is `S (decision) + S (impl)`, not a slice.

**Why:** a cross-reference states a *constraint*, not a *position*. "FIRST" in a pointer means
"before the thing this document is about", which is almost never "first in the work queue". The item
itself is the only place the trigger is written in full, and it is the only place that says what
happens if you skip it.

**How to apply:** before ordering work from a roadmap/spec cross-reference, open the referenced item
and read its own trigger and status cell. Quote *that*, not the pointer. Same shape as
[[quote-the-code-dont-characterise-it]] applied to backlog prose instead of source.

Second half, same session: reading the referenced rows also revealed that **backlog #19 is a special
case of #23(a)** — both are `persist_summary` layer-2 preserving `mdCorrectionsHash` while the body
is replaced, and #23's route needs no race at all (a plain cloud re-summarize). An investigation that
had stopped at the pointer would have filed a duplicate. See [[dual-review-what-it-catches]]
for the general form: the cheap read is the one that dissolves the expensive work.
