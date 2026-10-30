---
name: usage-is-cache-rewrites-of-parked-agents
description: "FIRES-WHEN: I am about to reuse a teammate for a new slice/round, or park an agent waiting for my 'go' — measured 2026-10-30, reused long-lived teammates were ~70% of weighted usage, mostly full-context cache RE-WRITES after idling; the weekly limit halted all work ~24h"
metadata:
  node_type: memory
  type: feedback
  originSessionId: a6abe358-4c0b-44cb-a058-5446372998ef
  modified: 2026-10-30T12:58:07.350Z
---

**Fresh agent per slice AND per round; never park an agent waiting for "go"; coordinator /clear only at natural pauses.**
Decided by the owner 2026-10-30 (selection card), after a weighted measurement.

Measured over the 24 h before the 10-29 halt. The weights are API list prices used as a proxy: read 0.1×, 1h write 2×, output 5×.
- **Reused teammates: 69.5% of weighted cost.** Five long-lived agents. Their cost was mostly cache WRITES: 65 full-context rebuilds of 100k tokens or more, after they idled past the cache TTL and were woken.
- **The coordinator: 25.9%,** mostly cheap reads. Its 1h cache meant only 3 rebuilds.
- **Fresh subagents: 4.3%,** about a 65k build each.

**Why:** the weekly limit was halting work for about a day, every week, for several weeks. Raw token shares misled me at first: 99% of raw tokens are reads, but reads are cheap. The owner caught that I hadn't weighted cache costs or counted reset overhead.

**How to apply:** finish the in-flight work with the existing agent, then retire it. Brief a fresh one for the next fold or round. Don't hold an agent idle "until I say go": let it exit, and brief a fresh one later. Don't ask for a coordinator /clear per PR while the backlog #396 restore is broken.
The statusline caches the weekly % in `~/.claude/.rate-limits.json`. Backlog #399 is the planned pacing hook.
Related: [[a-signal-needs-its-base-rate]], [[always-choose-subagent-driven-execution]].
