---
name: project-has-two-deliverables
description: "FIRES-WHEN: needing the project's scope — the product AND the reusable harness — Stated by the user 2026-08-11: this project must produce a battle-tested harness + reproducible framework for NEW projects, not only the shipped product — index is docs/portable-practices.md"
metadata:
  node_type: memory
  type: project
  originSessionId: eebd3332-cf66-40d2-9e14-9cb83552f20e
  modified: 2026-09-07T19:10:06.246Z
---

**User, 2026-08-11, verbatim intent:** *"The objective of this project is not only deliver the product
that we are building, but have a battle tested harness and supporting document (or frameworks) for
new projects."*

This is **not derivable from the code or the roadmap**, both of which describe only the product. It
reframes work that would otherwise look like overhead — the ratchets, the review method, the process
docs — as a **first-class deliverable** rather than scaffolding around one.

**Practical consequences:**
- **Index: [`docs/portable-practices.md`](../../../../code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/portable-practices.md)**
  — started 2026-08-11 with 7 measured entries; the rest of the corpus is unmined (task #55).
- Entries must pass TWO filters: **measured** (files/numbers/output, not a confident belief) and
  **project-independent** (would hold with no Supabase, no Gemini, no Fly). Most of this project's
  best lessons fail the second, and that is the correct outcome — do not dilute the file.
- **What travels is the question a tool asks, never the tool.** Two sentences went into the global
  `~/.claude/CLAUDE.md`; the 350-line checker did not. Same relationship for everything else.
- When a lesson is learned here, ask a second question beyond "how do we prevent this again?" —
  **"does this survive leaving the repo?"**

**⟳ 2026-09-07 — DELIVERABLE 2 NOW HAS A NAMED COMPONENT, AND IT IS MEANT TO SHIP.** The user had
twice said the **comprehensibility suite** is a main deliverable and that they planned to publish it
to a marketplace; neither was written anywhere until now (PR #248, `portable-practices.md` opening).
**The consequence that changes how to work:** for that suite's 9 files, *project-independent* stops
being an entry-quality filter and becomes a **release blocker** — coupling is a defect, not untidiness.
Measured coupling: `shared/explainer-delivery.md` **0** project-specific refs, `explain-topic` and
`explain-findings` **1** each, `brief/SKILL.md` **9**, all in one ground-truth command list.

⛔ **Still owed, and easy to mis-close:** the four page-producing skills have **no anchor** for the
PRESENT human — `status-visibility` is scoped to *"a person who was AWAY"*. Do **not** fix this by
widening that anchor (one name, two readers). A new anchor needs a claiming document or
`check-anchors` R4 goes red, so it lands with backlog #89's design pass.

**The method's own trap, learned the same day:** write these by ENUMERATING, not recalling. Three
descriptions-from-memory were wrong that day — [[a-test-that-cannot-fail]] has
the count. A summary composed at the end of a long session is the highest-risk artifact in the repo.

See [[quote-the-code-dont-characterise-it]] (same discipline, applied to code claims) and
[[gates-detect-defects-not-design]].
