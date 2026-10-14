---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up.
argument-hint: "What will the next session be used for?"
---

Write a handoff document summarising the current conversation so a fresh agent can continue the work.

**Save it to `.remember/remember.md` in the project root** (read the file before you write to it — you are replacing the previous session's note).

⚠ **LOCAL MODIFICATION — do not "restore" this to `mktemp`.** Upstream saves to `mktemp -t handoff-XXXXXX.md`. That path is unreachable on resume: the suffix is random, it lives outside the repo, and nothing indexes it. Three such files accumulated here and **none was ever read by a resuming session** — the doc was written, was good, and had no consumer.

`.remember/remember.md` is not an arbitrary choice — it is the path the `remember` plugin's SessionStart hook already reads. See `session-start-hook.sh`: `REMEMBER_HANDOFF="$REMEMBER_DIR/remember.md"`, emitted as `=== LAST HANDOFF ===` and **injected before identity and memory, specifically so it survives context-preview truncation**. Delivery is fingerprinted on the handoff's CONTENT, so a session that reads it without writing one back does not consume it.

⛔ **Why no line number is quoted here, how to discover the installed hook, and how to inventory where a string appears in this repo — all in ONE place: [`../shared/corpus-search.md`](../shared/corpus-search.md).** A line number in a VENDORED file has no owner in this repo: no guard can watch it and a plugin bump invalidates it silently, so name the SYMBOL (`REMEMBER_HANDOFF`, two assignments) and the path. ⚠ Do not restate the search instruction here — it is not a bare `grep -rl`, and not a bare `rg`, and five rounds of drift between copies of that sentence are why it lives in one file now.

If a session-start block *does* print `Write next handoff to: <path>`, **use that path** — it is always the right one. ⛔ **THREE things print it, and the mechanism behind the first is described ONCE, in [`../shared/handoff-path.md`](../shared/handoff-path.md). Do not restate it here.** Three labels for that trigger were each measured false, and a round-5 correction that reached this file and never reached `.claude/hooks/enforce-handoff-path.sh` — leaving the hook printing a claim and its own withdrawal in one refusal — is what made a single source necessary.

**Exception — a mid-task subagent handoff** (passing context to an agent inside the *current* session, not to the next session): use `mktemp` there, so it cannot clobber the session-continuity slot.

Suggest the skills to be used, if any, by the next session.

Do not duplicate content already captured in other artifacts (PRDs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.
