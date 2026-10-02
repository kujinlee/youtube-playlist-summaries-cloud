---
name: a-title-is-scanned-not-read
description: "FIRES-WHEN: about to write a commit subject, PR title, or dashboard entry heading — lead with the concrete SCOPE, then the finding; an essayistic title states what was learned and hides what was touched"
metadata:
  type: feedback
---

**Asked for 2026-10-02, by the user, from inside an explainer page:**

> *"While the essayistic line can be more thought provoking, I want more informative title so that I
> can grasp what in there. In other words, more straightforward wording can be more informative."*

## The rule

**Concrete subject first, then the finding, separated by an em dash.** Keep the insight — the
complaint was never that it is there — but stop making it the only thing present.

| what I wrote | what it should have been |
|---|---|
| Nine rounds found the same defect, so the tenth asked why instead | **ADR-0014 + D1 on `check-ratchet-contract.py`** — nine rounds, and each fix was generating the next instance |
| The CI budget was set before the guards that blow it existed | **`verify` timeout 15→30, backlog #217** — two subprocess-heavy guards add ~13 min to the sweep |
| The checkboxes were a claim; #360 merging made three of them false | **Reconcile roadmap + memory after #360** — three checkboxes went stale at merge |
| Two rows said LIVE about a branch that no longer exists | **Close backlog #201/#202, file #219** — the closure guard's token grammar is single-id only |

**Why:** the essayistic title states what was *learned* and omits what was *touched*. Someone
scanning `git log` to answer *"what changed?"* — the commonest reason to open a log — gets nothing.

## ⛔ Why I drifted into it, so the correction does not drift back

This repo's house style for **backlog rows, review documents and commit BODIES** is deliberately
argumentative: a row that merely labels gets skimmed and re-litigated, which is why they read as
essays. I carried that into titles, where it is wrong.

⭐ **A backlog row is READ. A title is SCANNED.** One sentence cannot serve both, and when they
conflict the scanner wins — because nobody reads a title on purpose. The body still argues; that
part was never the problem.

⚠ **And do not over-correct.** A log of `fix guard` and `update docs` tells you the scope and hides
every reason, which is the shape this project's commit messages exist to avoid. The finding stays;
it just stops going first.

Related: [[how-to-shape-a-message-to-me]] (lead with the conclusion), [[name-and-define-every-reference]]
(the same user, the same week, the same complaint in a different place — a reference nobody can
resolve and a title nobody can parse are one failure), [[the-user-does-not-follow-in-real-time]].
