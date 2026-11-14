---
name: a-reviewer-told-findings-are-filed-files-them
description: "Writing a CAPPED-round Codex prompt? \"a non-BLOCKER is filed\" made Codex open a GitHub issue itself (#513, 2026-11-05) — say \"REPORT it; do not open issues or touch GitHub\""
metadata:
  node_type: memory
  type: feedback
  originSessionId: f7c144b8-1b6c-4db3-8ef1-932d4e701b12
  modified: 2026-11-06T02:27:02.823Z
---

2026-11-05, `timeline-story` round 4: the prompt ended "This is the CAPPED round: report only what is WRONG on this tree;
a non-BLOCKER is filed." Codex read *filed* as an instruction and ran `gh issue create` — GitHub issue #513, under the
owner's account, unasked. The same wording had been used on earlier capped rounds without this happening, so it is not
reliable either way.

**Why:** Codex runs with `-s danger-full-access` and the owner's `gh` auth; any verb in the prompt that names an
outward action can be taken literally. Filing is the COORDINATOR's step (a backlog row), never the reviewer's.

**How to apply:** in every review prompt, write "REPORT findings in your final message only; do not open issues, comment,
push or otherwise touch GitHub." When it happens anyway, file the backlog row as usual and leave the issue for the owner
(closing it is also outward-facing). Related: [[running-codex]].
