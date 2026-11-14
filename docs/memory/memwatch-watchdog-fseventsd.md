---
name: memwatch-watchdog-fseventsd
description: "Mac slow, processes killed, Codex dying, or a \"fseventsd\"/swap notification? A launchd watchdog exists (~/.claude/memwatch); the 11-09 lock-up was fseventsd at 44 GB"
metadata:
  node_type: memory
  type: reference
  originSessionId: f7c144b8-1b6c-4db3-8ef1-932d4e701b12
  modified: 2026-11-09T17:55:00.706Z
---

**2026-11-09: the Mac (16 GB) froze overnight** — 5 JetsamEvent kill reports 11-08 22:26 → 11-09 03:48, every one naming
`fseventsd` largest at 43.9 → 44.7 GB (almost all compressed/swapped), after 46 days of uptime. It grew slowly; this
is also why Codex and gate runs kept getting killed that night. The slow event reader was NOT identified (kill reports
don't record stream clients); Cursor watching 67 worktrees was the likely load (inferred).

**Done with the owner's OK (11-09 09:50, option A):**
- Pruned `.claude/worktrees` 67 → 5 (11 GB → 876 MB); log at the session scratchpad `pruned-worktrees.txt`.
- Cursor `files.watcherExclude` for worktrees, node_modules, .git/objects, .next, .remember
  (`~/Library/Application Support/Cursor/User/settings.json`, backup `.bak-1109`).
- **Watchdog:** `~/.claude/memwatch/memwatch.py`, run every 900 s by `~/Library/LaunchAgents/com.kujinlee.memwatch.plist`
  (survives reboot; independent of Claude sessions). Notifies at fseventsd > 2 GB, swap > 8 GB, or a new kill report;
  re-notifies per kind every 2 h; CANNOT RUN is notified, never silent. Trend: `~/.claude/memwatch/log.jsonl`.
  `--test` forces every notification. Check it is loaded: `launchctl print gui/$(id -u)/com.kujinlee.memwatch`.
- The remedy needs sudo, so it is the owner's: `sudo killall fseventsd` or a reboot.

Pending at write time: auto-prune merged worktrees from the session-start hook (repo PR, side job).
