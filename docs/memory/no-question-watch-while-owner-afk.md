---
name: no-question-watch-while-owner-afk
description: "Watching ~/explainers/questions.md? Use a ONE-SHOT background Bash poll (no expiry, 0 tokens idle), never a 30-min Monitor re-armed every expiry (~30k input-equivalent tokens per empty wake)"
metadata:
  node_type: memory
  type: feedback
  originSessionId: b387c8e6-9003-42f5-a944-1d4eb1de0c9b
  modified: 2026-11-12T23:50:09.617Z
---

Owner 2026-11-12 15:47, after I re-armed the questions Monitor six times (11:50–15:20) while they were AFK:
"I have been AFK" — then asked what re-arming costs vs running a watcher all the time.

**Measured (this session's transcript, 11-12 15:20–15:49):** the watcher PROCESS costs nothing (local tail/poll,
no model call). The cost is the WAKE: a Monitor expires after ≤30 min and each expiry is a model turn — 2 API
calls, each re-reading ~121k cached context tokens, ~0.5–1.5k cache written, ~300–900 output. Weighted
(cache read 0.1×, 1h cache write 2×, output 5× — standard price ratios, an inference) ≈ 30k input-equivalent per
empty wake, growing with context. Always-on via Monitor = 48 empty wakes/day ≈ 1.4M.

**Why:** the Monitor's 30-min cap, not the watching, is what costs.

**How to apply:** watch the questions file with Bash `run_in_background` and a poll loop that EXITS on the first
new line (`wc -l` baseline, `sleep 5`) — no timeout, 0 tokens idle, one wake per real question; re-arm after
answering. ⚠ Not `tail -F | awk exit`: tail never gets SIGPIPE on a quiet file, so it hangs. Keep the
30-min Monitor only for streams needing per-event delivery with a known end (CI checks).
