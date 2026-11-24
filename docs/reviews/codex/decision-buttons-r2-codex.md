<!-- codex-review: model=gpt-6.1-terra -->

- **Major — Sent state still transfers between different decisions.** [brief-compose.py:1235](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/decision-buttons/scripts/brief-compose.py:1235) truncates the question to 400 characters before hashing it, and [the key](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/decision-buttons/scripts/brief-compose.py:1241) has no other identity for an unlabelled decision. Two unlabelled decisions with the same question, or whose questions differ only after character 400, therefore share a key. After one is sent, a reload shows *sent* on the other. The renumbering test uses distinct questions and cannot catch this.

- **Major — Heading decisions can lose their sent state on reload.** [questionOf](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/decision-buttons/scripts/brief-compose.py:1231) includes the tray’s `.askbtn` text. The decision script loads stored state before the tray script adds that button, but a later click saves the key after it has been added. For an `h2` or `h3` decision, the saved question thus ends in `ask`, while the next load looks up the question without it. The card offers answers again even though one was sent; the posted quote also includes `ask`. The heading self-test does not run the tray script.

- **Minor — The heading-placement test does not prove “after.”** [The assertion](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/decision-buttons/scripts/brief-compose.py:3282) checks only that the box’s parent is `BODY` and that its text is outside the heading. Moving the box *before* the heading would still pass, despite the case claiming to verify placement after it.

Both requested self-tests passed: `brief-compose.py` **245/245** and `ask_answerer.py` **124/124**.

VERDICT: NOT CONVERGED
