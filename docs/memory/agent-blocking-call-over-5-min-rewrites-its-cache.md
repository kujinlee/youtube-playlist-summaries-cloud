---
name: agent-blocking-call-over-5-min-rewrites-its-cache
description: "Briefing an agent that waits on a long job (sweep, CI, sleep loop)? No single tool call over ~270 s: the agent cache expires at 5 min and the whole context is re-written"
metadata:
  type: feedback
---

Measured 2026-11-01 (usage audit, 10-30..11-01, 230M weighted): **agent cache re-writes were 19.2% of the TOTAL** — 226 of 227 came right after ONE blocking tool call longer than 5 minutes (sleep/wait loops 5.4%, mutation sweeps 4.5%, other gates 3.8%), every day (20/18/22%). Agents use a 5-minute prompt cache; the coordinator's is 1 hour.

**Rule:** in every agent brief: "no single tool call may block longer than ~270 s. Start a long job in the background writing to a log file, then poll it with foreground calls of `sleep 240` + a status check, each under 270 s; still ONE final report." A poll costs a cache READ (0.1×); a >5-min call costs a re-WRITE of the whole context (1.25×).

**Why:** my own 10-30 rule "agents wait in the FOREGROUND" ([[a-waiting-line-must-measure-age]]) caused this — it fixed lost reports and silently bought cache expiry. Foreground is still right; LONG single calls are the defect.

**How to apply:** add the line to every brief that runs CI watch, `--mutate`, `gates-for-pr.py`, or a sleep. `gh pr checks --watch` must be replaced by a poll loop. Candidate for a hook (filed with the audit rows).
