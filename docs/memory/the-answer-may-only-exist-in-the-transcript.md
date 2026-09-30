---
name: the-answer-may-only-exist-in-the-transcript
description: "FIRES-WHEN: asked what was decided, what the conclusion was, or why something is the way it is"
metadata:
  type: feedback
---

⛔ **Search the CONVERSATION, not only the artifacts it produced.** Docs, memory files, backlog rows
and pages are where a decision is *supposed* to land. When it never landed, the only copy is the
transcript — and reporting *"no conclusion was recorded"* from a doc search is then **wrong in the
more damaging direction**, because it invites rebuilding a decision that was already made.

⭐ **Measured 2026-09-30.** Asked *"what was the conclusion about sharing MEMORY.md?"* I searched
five places — repo `docs/`, `docs/portable-practices.md`, `.remember/`, the corpus itself, the design
page — found nothing, and filed a backlog row saying no conclusion existed, with **four candidate
directions I invented**. The user said *"it was yesterday"*. One grep over the raw transcripts found
a measured, considered answer from 2026-09-29 14:50 — including a counted 86%/14% split and a named
destination that was already this project's deliverable #2. My row had buried it.

**How to search:** transcripts are `~/.claude/projects/<slug>/*.jsonl`, one JSON object per line;
filter `o["type"] == "user"` and match on the topic, then read the assistant turns that follow.
`<slug>` is the absolute repo path with every non-alphanumeric replaced by `-`. There were 750 files
and the grep took seconds.

⚠ **And the corollary, which is the actual lesson:** a measured answer that lives only in a
transcript **is not recorded**. It survived only because the human remembered asking. Whenever an
answer is worth the work of deriving, file it where a reader would look before the turn ends —
see [[an-escalation-has-no-closer]], [[feedback-agree-before-filing]].
