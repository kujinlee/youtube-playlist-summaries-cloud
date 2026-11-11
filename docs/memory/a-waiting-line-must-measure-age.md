---
name: a-waiting-line-must-measure-age
description: "FIRES-WHEN: I write '⏳ Waiting on …' for dispatched work, or brief an agent that runs a long background job — measured 2026-10-30: three items stalled for hours because agents ended their turn promising 'I'll report when the background job finishes' and I repeated the waiting line without checking age"
metadata:
  node_type: memory
  type: feedback
  originSessionId: a6abe358-4c0b-44cb-a058-5446372998ef
  modified: 2026-10-30T19:50:55.259Z
---

**A "waiting" line that measures nothing hides a stall.** On 2026-10-30, three dispatched jobs stalled unseen:
- PR #442's fold sat unpushed for about 10 h;
- PR #443 had 8 commits unpushed;
- PR #440's round-3 review was written at 07:15 and never reported.

In each case the agent's LAST message was an idle note promising to report when its background job finished. An idle subagent is not reliably woken by its own background job, so the promise became never. I repeated "⏳ Waiting on PR #442 sweep…" every turn for hours. The owner noticed three stalls and asked for the hole to be found and prevented.

**Why:** a turn that ends on a promise loses the promise. This is [[never-close-with-a-promise]] again, in agents rather than in me.

**How to apply:**
- Every agent brief says: never end the turn waiting on a background job; run it in the foreground with a timeout, then send ONE final report.
- My waiting line comes from the stall check (backlog #410, `scripts/check-stalled-work.py`), with AGES. Before it lands, check worktree heads against their remotes, and scratchpad review files against coordinator docs, before writing a waiting line.
- When an agent's last message says "will report when …", treat that as stalled as soon as the job should have finished.

**SECOND CAUSE, stated by two agents on 2026-10-30 (`fold-440-r3` at 12:06, `fold-449-r1` at 12:50): an agent's PLAIN-TEXT final answer does not reach the coordinator. Only a SendMessage does.** Both agents finished, wrote their report as ordinary output, and went idle. Their commits sat unreported for 50 minutes until a nudge made them re-send it via SendMessage. Brief rule: "send your ONE final report WITH SendMessage to the coordinator; plain output is not delivered." Until #410 lands, read the worktree, not the inbox.

**MEASURED 2026-10-30 11:37: a Monitor expires at 30 min even when armed with `timeout_ms: 3600000`.** My own question watch did this every time this session. So an agent that "arms a monitor and will report" on a 25–45 min sweep loses the watch before the sweep ends; that is the likely mechanism of `fold-446-r4`'s stall. Brief rule: wait in the FOREGROUND (bounded polling), never via a Monitor, for anything that can run past 30 min.

**⟳ REVERSED 2026-11-01 14:10 (owner chose option A): agents report through their FINAL TEXT only — no SendMessage report.** Measured over this session's transcript: 325 of 326 idle notifications carried the agent's result in a `result` field, including 63 on 10-30, so the "SECOND CAUSE" above was the two agents' claim, not a measurement. The double channel cost 278 extra coordinator turns = 32.7M weighted = 11.8% of coordinator spend. The copy the owner asked for already exists at no cost: every agent's transcript, final message included, is saved at `~/.claude/projects/<slug>/<session>/subagents/agent-<id>.jsonl`. If an idle notification arrives without a result (1 in 326 so far), read that file's last assistant text. Brief rule now: "Your final message IS your report (≤N lines). Do not use SendMessage."
