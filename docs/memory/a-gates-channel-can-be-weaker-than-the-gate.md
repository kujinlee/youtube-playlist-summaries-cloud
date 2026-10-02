---
name: a-gates-channel-can-be-weaker-than-the-gate
description: "FIRES-WHEN: adding a refusal, warning or block — deciding WHERE it prints — A hard refusal printed to a channel nobody reads is weaker than a warning printed where someone looks — ask what the gate's output CHANNEL is, not just its severity"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f872245b-d763-4621-9817-c63a543b2ef5
  modified: 2026-09-11T19:34:37.592Z
---

**Ask of every gate: not just "does it fail?" but "WHERE does the failure land, and does a human read
that place?"** A refusal whose only output goes to an unread channel is weaker than a warning
rendered where someone actually looks.

**MEASURED 2026-09-11, merged as `e597a8e7` (PR #290).** The backlog page had twelve open rows with
no `GROUPS` description, shown under *"Filed, but nobody has described them yet"*. `GROUPS` was a
**hard refusal** — `ShapeError`, exit 1, nothing written — until 2026-09-09. **Eight of the twelve
accumulated while that refusal was in force.** It fired on every edit to `docs/backlog.md`;
`.claude/hooks/regen-backlog-page.sh` caught the non-zero exit and printed the remedy naming the
file and the fix — to **hook stdout**, which `CLAUDE.md` states is *"shown to the assistant and not
reliably to the user"*. The page silently held a stale state and looked current.

**The 2026-09-09 change traded gate STRENGTH for channel QUALITY** — the page always builds, and the
gap renders as a visibly unfinished section. That is a *detector*, not a guard, and it is why the
user found this in one screenshot after a month of the stronger gate finding nothing.

⚠ **Same class as the step-banner lapse** (`scripts/begin-plan.py` printed a banner to Bash stdout
and reached nobody; that project's backlog #95). Two instances, one shape.

**How to apply:**
- Before trusting a gate, name the channel and ask who reads it. Hook stdout and Bash stdout reach
  the assistant, not the human.
- Prefer rendering a gap where the reader already looks over refusing in a log.
- The durable fix is structural: `gen-backlog-page.py` **never runs in CI**, not even its self-test,
  so nothing on a shared machine could see the gap. See [[a-check-result-is-not-the-claim]] and
  [[a-convention-catches-what-you-read]].
