---
name: a-waiting-line-must-measure-age
description: "FIRES-WHEN: I write '⏳ Waiting on …' for dispatched work, or brief an agent that runs a long background job. The waiting line must carry AGES; agents run long jobs in the FOREGROUND and report as their FINAL TEXT (no SendMessage)"
metadata:
  node_type: memory
  type: feedback
  originSessionId: a6abe358-4c0b-44cb-a058-5446372998ef
  modified: 2026-10-30T19:50:55.259Z
---

**The rule: a "waiting" line that measures nothing hides a stall. Every waiting line carries AGES, and every agent brief forbids ending a turn on a promise.**

**How to apply:**
- **Agent brief:** never end the turn waiting on a background job — run it in the FOREGROUND with a bounded timeout, then end with ONE report. **"Your final message IS your report (≤N lines). Do not use SendMessage."** (owner, option A, 2026-11-01 14:10). Never wait via a Monitor for anything that can run past 30 min.
- **My waiting line** comes from the stall check (`scripts/check-stalled-work.py`, backlog #410) with ages; otherwise check worktree heads against their remotes and scratchpad review files against coordinator docs before writing it.
- **An agent whose last message says "will report when …" is stalled** as soon as the job should have finished.
- **An idle notification with no result** (1 in 326 measured): read the last assistant text of `~/.claude/projects/<slug>/<session>/subagents/agent-<id>.jsonl`.

**Why:** a turn that ends on a promise loses the promise — [[never-close-with-a-promise]] in agents rather than in me. An idle subagent is not reliably woken by its own background job.

## History (condensed)

- **2026-10-30, three unseen stalls:** PR #442's fold unpushed ~10 h; PR #443 with 8 commits unpushed; PR #440's round-3 review written 07:15 and never reported. Each agent's last message promised a report; I repeated "⏳ Waiting on PR #442 sweep…" for hours. The owner found the three stalls and asked for the hole to be prevented.
- **2026-10-30 11:37, measured:** a Monitor expires at 30 min even with `timeout_ms: 3600000` — the likely mechanism of `fold-446-r4`'s stall.
- **Superseded the same day:** two agents (`fold-440-r3`, `fold-449-r1`) claimed plain-text final answers do not reach the coordinator, so briefs required a SendMessage report. **Reversed 2026-11-01:** 325 of 326 idle notifications carried the result (63 on 10-30); the claim was not a measurement, and the double channel cost 278 extra coordinator turns = 32.7M weighted = 11.8% of coordinator spend.

Related: [[a-usage-limit-stop-needs-a-wake-at-reset]].
