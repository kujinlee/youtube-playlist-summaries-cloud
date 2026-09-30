---
name: feedback-agree-before-filing
description: "FIRES-WHEN: about to file or amend a backlog row, or correct something you found wrong — ⟳ REVERSED 2026-09-28 — ALIGNMENT is the gate, not approval. File and amend backlog rows WITHOUT asking; wait only when the goal itself is in question"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 18820d36-e0cd-46c7-945b-e5f3417ebb5f
  modified: 2026-09-28T19:03:40.099Z
---

⛔ **THE RULE WAS REVERSED BY THE USER ON 2026-09-28, in writing, in an explainer page comment.**
The filename is kept because two memory files and `docs/process-checklists.md` cite it; a rename
would dangle them for no gain.

**What they said, verbatim:** *"if you find something incorrect, why wait for approval? The human
gate should not become a barrier to correct something. I prefer you to create backlog or amend
backlog without my approval as I cannot read all your chat log and I don't want to accumulate
necessary actions to be delayed because of my inaction. Important thing is whether you and me are
aligned to the same goal. if that is in question, then wait for me. If we are aligned to the same
goal (or intention) then act first then let me know later so that if I think your action is not
aligned to my overall intention, I can ask to revert some of your action."*

**THE GATE IS ALIGNMENT, NOT PERMISSION:**

| situation | do |
|---|---|
| Aligned on the goal — a correction, a filing, an amendment that serves an intent already settled | **ACT, then report.** Reversibility is the safety net: they can ask for a revert |
| The goal itself is in question — you do not know what they want, or the *nature* of the issue is still being established | **WAIT.** This is the only case left |

⚠ **THIS DOES NOT ERASE THE 2026-07-31 INCIDENT — IT RE-KEYS IT.** That day I traced three defects
(D5–D7) *while we were still establishing the nature of the issue*, filed them to a review doc and
the roadmap, and several framings then needed correction during the discussion that followed (blast
radius overstated, finding #2 graded down from one writer out of five). The user: *"we were
discussing the nature of the issue and you just file the ticket."* **That was filing while alignment
was genuinely in question, which the new rule still forbids.** The error was never "filed without
approval"; it was "filed before we agreed what the thing WAS". Filing early also meant filing wrong.

**How to apply.** Default to acting. Before filing or amending, ask yourself the one question:
*do I know what they want here?* A factual correction to something already agreed, a backlog row
for work already discussed, a row whose premise I just measured to be false — all aligned, all act.
A finding whose **nature** is still being argued, or a decision that would **move the goal** — wait.

⛔ **WHAT THIS DOES NOT COVER, stated so it is not over-read.** They authorised filing and amending.
It is NOT a blanket authority over every human gate: `docs/dev-process.md` makes **merging** a human
gate for its own reasons (blast radius), and outward-facing or irreversible actions — deploy, delete,
spend, push to a shared branch — were not what they were answering. Merging a **docs-only backlog
filing** is covered, because in this repo a backlog row cannot exist without a PR, so refusing that
merge would re-create exactly the delay they are removing. Anything wider needs its own ruling.

⚠ **The reason they gave matters as much as the rule:** *"I cannot read all your chat log."* Acting
and reporting is not a convenience — **their attention is the scarce resource**, and a question is a
withdrawal from it. Batch what you report; never route a decision they did not need to make.

Related: [[putting-a-choice-to-the-user]], [[print-selection-cards-in-chat]],
[[the-user-does-not-follow-in-real-time]], [[defaults-i-decide-myself]]
