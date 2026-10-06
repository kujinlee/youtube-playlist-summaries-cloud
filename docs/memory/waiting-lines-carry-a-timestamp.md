---
name: waiting-lines-carry-a-timestamp
description: "FIRES-WHEN: about to write a ⏳ waiting line, a status line, or report that something is still running — the user cannot tell how long ago it started unless the line carries a CLOCK TIME. Asked for 2026-10-06."
metadata:
  type: feedback
---

**Every ⏳ waiting line and every status report carries a timestamp.** User, 2026-10-06, after a
long AFK stretch where I wrote `⏳ Shards running (~25 min)` with no clock time:

> *"this line doesn't have time stamp. It would be helpful if hourglass line shows its timestamp so
> that I can gauge how long ago it happened"*

**Why:** the user reads these messages LONG after they are written — this is the same premise as
[[the-user-does-not-follow-in-real-time]]. A duration ("~25 min") is only meaningful relative to a
start the reader cannot see, so "running, ~25 min" is unreadable an hour later: it cannot be
distinguished from *finished*, *hung*, or *started one minute ago*. A clock time is self-contained.

**How to apply:**

- Lead the line with the time: `⏳ **13:25 PDT** — shards running, ~25 min (started 12:58)`.
- Give the START as well as the duration whenever both are known. The start is the fact; the
  duration is the inference.
- The same applies to any status table written during a wait — put the time in the header
  (`| | at 13:25 PDT |`), not just in prose.
- Get it from `date`, never from the UserPromptSubmit hook's stamp of the user's last message —
  those can be an hour apart, and reporting theirs as mine would be a fabricated observation.

⚠ **This is cheap and I have no excuse for omitting it** — one `date` call, or the timestamp already
printed by the command whose output I am relaying. Relates to
[[show-a-waiting-signal-not-prose]], which asked for the ⏳ marker itself; this adds the clock to it,
and [[how-to-shape-a-message-to-me]] for the shape of the report around it.
