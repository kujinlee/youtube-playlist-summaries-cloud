---
name: stranger-token-h2-done
description: "FIRES-WHEN: running the marketplace stranger experiment's skill half (plan Human step H2). The token exists at ~/.config/claude-stranger/token (owner 11-13 03:37); never print, paste or commit it."
metadata:
  type: project
---

**Plan step H2 is DONE (owner, 2026-11-13 03:37):** "token saved at ~/.config/claude-stranger/token". I checked it the same minute without printing it: mode `-rw-------`, 108 bytes, prefix `sk-ant-oat` (a `claude setup-token` OAuth token).

**How to apply:** pass it only as `CLAUDE_CODE_OAUTH_TOKEN="$(cat ~/.config/claude-stranger/token)"` inside the experiment's isolated world (plan `docs/superpowers/plans/2026-11-11-marketplace-inventory.md`, Task 14/15 skill half). Never echo it, never put it in a command line that gets logged in a review doc, never copy it into the repo (it is PUBLIC). If it stops working, the skill half is CANNOT RUN, and the owner re-runs `claude setup-token`. H7 (port 7391) is covered by [[may-free-port-7391]].
