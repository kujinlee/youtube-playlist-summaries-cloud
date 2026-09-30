---
name: detached-dig-retention-decision
description: "FIRES-WHEN: needing the retention rule for a detached dig — A detached dig is NOT kept forever — §8's 90-day clock wins over §6.2's 'never deleted'; retiring the rule dissolved a review High with no code change"
metadata: 
  node_type: memory
  type: project
  originSessionId: 562085d6-32ed-48ac-9814-b2f5e07b1cfe
  modified: 2026-08-07T01:14:59.169Z
---

**Decided 2026-08-06 (user).** When a summary is regenerated and its sections restructure, digs that
no longer map to a section become `detached`. **Detached artifacts are cleared periodically** — they
run §8's ordinary 90-day paid-retention clock, starting from `detached_at`, not from
"stopped being current" (a dig can be detached while its generation is still current, so a
not-current clock would never start).

**Why it mattered more than it looks.** The spec said both things at once: §6.2 promised a detached
dig is *"never a sweep candidate"*, while §8's retention rule — decided one day earlier — collects a
paid blob 90 days after it stops being current. A detached dig is never current *by construction*.
Whichever mechanism shipped first would have won.

**Retiring §6.2's promise dissolved round-6 finding H1's `P9` with no code change.** `P9` ("collecting
a generation whose dig row is detached succeeds") was reported as a defect *only* because that
sentence claimed otherwise. It was correct behaviour all along.

**How it was reached:** third finding in that section in three rounds ⇒ `dev-process.md`'s recurrence
trigger ⇒ ask which rule is a choice wearing the costume of a constraint. See
[[blob-addressing-spec-state]] and the same pattern in [[position-column-is-not-vestigial]].

**Accepted cost, written into the spec** (a rule whose cost is unwritten cannot be re-evaluated): a
user who restores an original section boundary after 90 days finds the dig gone and pays to re-dig it.

**Terminology that keeps biting — `dig` ≠ `digDeeper`.** `dig:<sectionId>` is the paid per-section
Gemini call; `digDeeper` is the **per-video document that accumulates** them. Local stores only the
accumulator (`<base>-dig-deeper.md`); cloud stores only the per-section blobs and assembles the
document at serve time. So only `dig` is section-scoped and only `dig` can be detached. Reasoning from
the slot *name* has now produced a wrong answer three times.
