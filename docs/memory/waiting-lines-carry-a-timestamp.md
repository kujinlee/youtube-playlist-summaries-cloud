---
name: waiting-lines-carry-a-timestamp
description: "FIRES-WHEN: about to emit a ▶ STEP banner, a ⏳ waiting line, a status line or table, or report that something is still running — every one carries a CLOCK TIME from `date`; and when told I stopped doing something, FIND the old decision before re-specifying it. Asked 2026-10-06, extended to banners 2026-10-19"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 014deb4c-b607-46d5-b015-d204f337780e
  modified: 2026-10-19T19:24:27.869Z
---

⛔ **Every status report carries a clock time — ⏳ waiting lines, status tables, AND `## ▶` step banners.** The
premise is *the reader arrives late*, and it does not care which glyph leads the line.
- **Banner format is NOT restated here** — the authoritative copy is the banner spec in `~/.claude/CLAUDE.md`
  (`[mm-dd hh:mm]`, prepended); history in [[the-user-does-not-follow-in-real-time]]. A second copy of a format drifts.
- **Waiting lines:** lead with the time and give the START as well as the duration whenever both are known — the start
  is the fact, the duration the inference. Example as originally recorded: `⏳ **13:25 PDT** — shards running, ~25 min
  (started 12:58)`. A status table during a wait puts the time in its header.
- **Source:** `date`, or the timestamp printed by the command being relayed — never the UserPromptSubmit hook's stamp of
  the user's last message (can be an hour off; relaying it as now is a fabricated observation).

**Why:** the user reads these LONG after they are written. "running, ~25 min" an hour later cannot be told apart from
*finished*, *hung*, or *started one minute ago*. A clock time is self-contained.

**How to apply — the narrower lesson:** when told I have stopped doing something I used to do, the first move is to
FIND THE OLD DECISION, not to re-specify it from the reason. The reason underdetermines the format. And a rule scoped
to its example (the ⏳ glyph) is a rule I have silently shrunk.

## History
- **2026-10-06**, after `⏳ Shards running (~25 min)` with no clock time, the user: *"this line doesn't have time stamp.
  It would be helpful if hourglass line shows its timestamp so that I can gauge how long ago it happened"*.
- **2026-10-19**, mid-turn: *"I notice that you don't add timestamp on banners any more"* — "any more": the rule already
  covered every status report, and I had read it as being about the ⏳ glyph. On being reminded I invented
  `▶ 13:25 PDT · STEP n` and wrote it into `~/.claude/CLAUDE.md` — timezone, no date, `·` separator, all three already
  forbidden by the 2026-10-16 decision. The user caught it within two minutes; a conflicting rule in the durable spec
  is worse than a missing one.

Related: [[show-a-waiting-signal-not-prose]] (the ⏳ marker itself), [[how-to-shape-a-message-to-me]].
