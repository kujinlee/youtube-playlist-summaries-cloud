---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up.
argument-hint: "What will the next session be used for?"
---

Write a handoff document summarising the current conversation so a fresh agent can continue the work.

**Save it to `.remember/remember.md` in the project root** (read the file before you write to it — you are replacing the previous session's note).

⚠ **LOCAL MODIFICATION — do not "restore" this to `mktemp`.** Upstream saves to `mktemp -t handoff-XXXXXX.md`. That path is unreachable on resume: the suffix is random, it lives outside the repo, and nothing indexes it. Three such files accumulated here and **none was ever read by a resuming session** — the doc was written, was good, and had no consumer.

`.remember/remember.md` is not an arbitrary choice — it is the path the `remember` plugin's SessionStart hook already reads. See `session-start-hook.sh`: `REMEMBER_HANDOFF="$REMEMBER_DIR/remember.md"`, emitted as `=== LAST HANDOFF ===` and **injected before identity and memory, specifically so it survives context-preview truncation**. Delivery is fingerprinted on the handoff's CONTENT, so a session that reads it without writing one back does not consume it.

⟳ **2026-10-13 — THE THREE LINE NUMBERS THAT STOOD HERE (`:795`, `:809-812`, `:814-825`) ARE GONE, and this file was the FIFTH site carrying them.** The other four were corrected earlier the same day and this one was missed; `grep -r` does not follow the symlink at `.claude/skills/handoff`, and `-R` does. ⛔ A line number in a VENDORED file has no owner in this repo — no guard can watch it, and a plugin update invalidates it silently. `grep -RSn 'REMEMBER_HANDOFF=' "$CLAUDE_PLUGIN_ROOT"` instead — ⛔ **`-RS`, not `-R`**: BSD grep (what macOS ships) treats `-R` exactly like `-r` and skips symlinks, so `-R` alone finds NOTHING here. Measured both binaries on this machine.

If a session-start block *does* print `Write next handoff to: <path>`, **use that path** — it is always the right one. ⟳ **Corrected 2026-10-13: THREE things print it, not one.** External mode (the store is outside the project); `per_session` mode, where the path is `remember.<session-id>.md`; and a DEGRADED `per_session` request — one with no resolvable session id — where the hook prints the **shared** `remember.md` path plus a second line saying the mode you asked for did not apply. In all three the printed path is the one to obey; only the reason differs.

**Exception — a mid-task subagent handoff** (passing context to an agent inside the *current* session, not to the next session): use `mktemp` there, so it cannot clobber the session-continuity slot.

Suggest the skills to be used, if any, by the next session.

Do not duplicate content already captured in other artifacts (PRDs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.
