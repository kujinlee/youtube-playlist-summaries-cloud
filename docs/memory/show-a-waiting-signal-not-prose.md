---
name: show-a-waiting-signal-not-prose
description: "FIRES-WHEN: about to report that you are blocked on background work — When blocked on background work, show a VISIBLE waiting indicator (⏳, a status line) — do not bury \\\"still running\\\" in prose"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 47586cf2-5f2e-4357-8ff6-1ddf3a06b5ee
  modified: 2026-09-23T15:30:08.912Z
---

**When I am waiting on something — a background agent, CI, a long build — say so with a visible
signal, not a sentence.** A hourglass, a blinking-dot equivalent, a short status line. The user
asked for this directly on 2026-09-23.

**Why:** they do not follow the work in real time ([[the-user-does-not-follow-in-real-time]]), so
they arrive at a wall of text and have to *read* it to learn whether anything is happening. On
2026-09-23 they asked *"is requested page ready?"* while a fork was mid-build — the answer was in my
previous message, in prose, and it did not register. A glyph would have.

**How to apply:**

- Lead the message with the state, not the explanation: `⏳ **Waiting** — <what>, <since/eta>`.
- Use it every time a turn ends with work still in flight, and when answering "is X ready?".
- Pair it with what needs them meanwhile — usually "nothing".
- On completion, switch the glyph rather than dropping it: `✅ **Done** — <what>`.
- ⚠ It is a STATUS LINE, not decoration. One per message, at the top. Scattering glyphs through
  prose rebuilds the problem it solves.

This is the same principle as the step banner: the reader must be able to answer *"what is
happening right now"* by glancing, never by reading.

Related: [[the-user-does-not-follow-in-real-time]], [[how-to-shape-a-message-to-me]],
[[never-close-with-a-promise]]
