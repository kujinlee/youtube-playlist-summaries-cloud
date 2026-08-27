---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up.
argument-hint: "What will the next session be used for?"
---

Write a handoff document summarising the current conversation so a fresh agent can continue the work.

**Save it to `.remember/remember.md` in the project root** (read the file before you write to it — you are replacing the previous session's note).

⚠ **LOCAL MODIFICATION — do not "restore" this to `mktemp`.** Upstream saves to `mktemp -t handoff-XXXXXX.md`. That path is unreachable on resume: the suffix is random, it lives outside the repo, and nothing indexes it. Three such files accumulated here and **none was ever read by a resuming session** — the doc was written, was good, and had no consumer.

`.remember/remember.md` is not an arbitrary choice — it is the path the `remember` plugin's SessionStart hook already reads. See `session-start-hook.sh`: `REMEMBER_HANDOFF="$REMEMBER_DIR/remember.md"` (:795), emitted as `=== LAST HANDOFF ===` and **injected before identity and memory, specifically so it survives context-preview truncation** (:809-812). Delivery is fingerprinted and non-destructive (:814-825), so a session that reads it without writing one back does not consume it.

If a session-start block *does* print `=== HANDOFF === / Write next handoff to: <path>`, use that path instead — it means external mode, where the file lives outside the project.

**Exception — a mid-task subagent handoff** (passing context to an agent inside the *current* session, not to the next session): use `mktemp` there, so it cannot clobber the session-continuity slot.

Suggest the skills to be used, if any, by the next session.

Do not duplicate content already captured in other artifacts (PRDs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.
