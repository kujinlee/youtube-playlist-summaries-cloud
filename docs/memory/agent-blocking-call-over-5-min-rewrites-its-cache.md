---
name: agent-blocking-call-over-5-min-rewrites-its-cache
description: "Briefing an agent that waits on a long job (sweep, CI, sleep loop)? It never waits on CI, and no single tool call runs over ~270 s: the agent cache expires at 5 min and the whole context is re-written"
metadata:
  type: feedback
---

**CURRENT RULE — two lines that go in every build/fold brief:**
1. **An agent NEVER waits on CI** (owner 11-13 21:41, "about 3% of usage is wasted"). When its PR is pushed and only CI remains, it ends with its final report (head SHA, HOLD verdicts, pilot record); the COORDINATOR waits with a background shell (0 tokens idle), then merges or re-merges master itself.
2. **No single tool call may block longer than ~270 s.** Start a long job in the background writing to a log file, then poll it with foreground calls of `sleep 240` + a status check, each under 270 s; still ONE final report. `gh pr checks --watch` is replaced by a poll loop.

**Why:** agents use a 5-minute prompt cache (the coordinator's is 1 hour). A poll costs a cache READ (0.1×); a call over 5 min costs a re-WRITE of the whole context (1.25×). Foreground waiting ([[a-waiting-line-must-measure-age]]) is still right — LONG single calls are the defect.

**How to apply:** add both lines to every brief that pushes a PR, runs `--mutate`, `gates-for-pr.py`, or a sleep. Candidate for a hook (filed with the audit rows).

## History
- **2026-11-01 usage audit** (10-30..11-01, 230M weighted): agent cache re-writes were **19.2% of the TOTAL** — 226 of 227 came right after ONE blocking call longer than 5 min (sleep/wait loops 5.4%, mutation sweeps 4.5%, other gates 3.8%), every day (20/18/22%). Cause: my own 10-30 rule "agents wait in the FOREGROUND" fixed lost reports and silently bought cache expiry.
- **2026-11-13:** two Fable agents polled CI ~7 h through 3–4 conflict-restart cycles, ~135k context per poll, 15–30 polls/h; the weekly meter went 22% → 25% with no new work → rule 1.
