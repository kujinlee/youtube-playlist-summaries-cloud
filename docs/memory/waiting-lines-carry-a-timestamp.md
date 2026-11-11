---
name: waiting-lines-carry-a-timestamp
description: "FIRES-WHEN: about to emit a ▶ STEP banner, a ⏳ waiting line, a status line, or report that something is still running — the user cannot tell how long ago it happened unless the line carries a CLOCK TIME. Asked for 2026-10-06, extended to BANNERS 2026-10-19."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 014deb4c-b607-46d5-b015-d204f337780e
  modified: 2026-10-19T19:24:27.869Z
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

## ⤳ EXTENDED TO STEP BANNERS, 2026-10-19 — and the extension was needed because I NARROWED it

The user, mid-turn, with banners running and no clock on any of them:

> *"I notice that you don't add timestamp on banners any more"*

**"any more" is the part that matters: this was not a new request.** The rule above already said
*"every ⏳ waiting line **and every status report**"*, and a `## ▶ STEP n of N` banner is the most
frequent status report I write. I read the rule as being about the `⏳` GLYPH rather than about the
reader's problem, so the clock went on waiting lines and came off everything else. ⛔ **A rule scoped
to its example is a rule I have silently shrunk** — the premise is *the reader arrives late*, and
that premise does not care which glyph leads the line.

⛔ **AND THE BANNER FORMAT WAS ALREADY DECIDED — I DID NOT LOOK, I RE-DERIVED, AND I GOT IT WRONG.**
`[[the-user-does-not-follow-in-real-time]]` has carried it since 2026-10-16: **`[mm-dd hh:mm]`,
prepended, no timezone, no seconds, no `·` separator** — under a heading that says *"take it from
here and do not re-derive it"*. On being reminded that banners had lost their clock I invented
`▶ 13:25 PDT · STEP n` and wrote that into `~/.claude/CLAUDE.md`: timezone, no date, `·` separator,
all three forbidden. **A conflicting rule in the durable spec is worse than a missing one**, and the
user caught it within two minutes. ⛔ *This file does not restate the format* — the authoritative
copy is the banner spec in `~/.claude/CLAUDE.md`, with the history in that memory. A second copy of
a format is a copy that drifts, which is this project's most-measured failure.

**The lesson is narrower than "remember the format":** when told I have stopped doing something I
used to do, the first move is to FIND THE OLD DECISION, not to re-specify it from the reason. The
reason underdetermines the format — all three of the rejected variants served "the reader arrives
late" equally well.

⚠ **This is cheap and I have no excuse for omitting it** — one `date` call, or the timestamp already
printed by the command whose output I am relaying. Relates to
[[show-a-waiting-signal-not-prose]], which asked for the ⏳ marker itself; this adds the clock to it,
and [[how-to-shape-a-message-to-me]] for the shape of the report around it.
