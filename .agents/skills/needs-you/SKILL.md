---
name: needs-you
description: Write an ask — a decision that is waiting on the human — as a file in docs/asks/, or record the human's answer to one. Use when work cannot continue until the human decides or does something, when an open ask has been answered, or when the user types /needs-you. Not for recording what changed (git log and the goal tree show that), and not for explaining a topic, a code change or where work stands (use explain-topic).
---

# Needs you

Write one ask as one file, or append its answer. The goal tree's NEEDS YOU list reads these files.

**Announce at start:** "Using the needs-you skill to write an ask." (or "…to record an answer.")

## Why this exists

The goal (node `status-visibility` of `docs/features.md`): *a person who was away can see what needs
them without reading the chat transcript.*

The chat transcript is not that. It is gone after a `/compact`, and the one thing the reader needs —
*a decision is waiting on them* — sits in paragraph four of the fifth message. An ask file is the
durable answer: `scripts/goal-tree.py` reads every open one into NEEDS YOU, and the compaction snapshot
counts them.

⟳ 2026-11-25 (dashboard-retire S2): this skill was `dashboard`. It no longer records what changed, and
it does not regenerate the dashboard page (that page and its generator are retired in a later slice,
S3). `docs/dashboard-entries.md` is a **frozen** record.

## Writing an ask — a new file

`docs/asks/YYYY-MM-DD-<slug>.md` — the date you write it, then a **specific** lowercase-kebab slug
(`2026-11-26-archive-form`, not `2026-11-26-question`). The name must match
`^\d{4}-\d{2}-\d{2}-[a-z0-9]+(-[a-z0-9]+)*\.md$`; anything else is refused.

```md
# Which archive form do we keep?
One plain sentence a non-engineer can read, saying what is being asked and why now.

**Decide:** which archive form to keep
- A small record page [recommended]
- A full frozen render
```

- **The first line is `# <question>`.** It is what NEEDS YOU shows.
- **Then the `**Decide:**` block:** the question after the opener, at least two `- ` options, at most
  one marked `[recommended]`. The same grammar the old store used, read by `decisions()` in
  `scripts/check-ask-store.py`.
- Write an ask **only when the human has to decide or do something before work can continue**. Not for
  progress, not to draw attention: NEEDS YOU being non-empty must mean something.

## Recording an answer — append to the SAME file

An ask is open until its file has a line that is exactly `## Answer` — outside any code fence, not
indented, nothing after it on the line (`## Answer — A` does not count). Append it, then what was decided:

```md
## Answer
The owner chose the record page (selection card, 2026-11-26).
```

A later change of mind is another note appended below the answer, never a rewrite of it.

## The rules a gate enforces

`scripts/check-ask-store.py` runs on every pull request (the `ask store` CI step):

> ⛔ **An ask only grows.** Never edit, rename or delete an ask file — not its question, not its
> options, not an earlier answer. Every byte at the merge base must still be there, at the start of the
> file (F1). A wrong ask is answered ("withdrawn: …"), not removed.
>
> ⛔ **Never write `docs/dashboard-entries.md`.** It is frozen to pinned bytes (L1); any change to it
> fails the step on that pull request and on master. A new ask goes in `docs/asks/`, nowhere else.

- Every file in `docs/asks/` must read as an ask (A1): a well-formed name, `# ` first, UTF-8, at most
  64 KiB, no merge-conflict marker. `.gitkeep` is allowed only while it is empty.
- No bare `#N`: name the namespace (`backlog #N`, `PR #N`) — `docs/asks/` is in the reference check's scope.
- A problem in any ask file makes NEEDS YOU **NOT READ**, never "nothing waits on you".

## Seeing it

`python3 scripts/goal-tree.py` prints NEEDS YOU at the top; the served `/goal-tree` page shows it too,
and rebuilds when a file under `docs/asks/` changes. An ask shows by its file stem, with its question.
