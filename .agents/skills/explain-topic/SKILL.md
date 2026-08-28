---
name: explain-topic
description: Build a self-contained HTML page explaining a topic, concept, mechanism or open question, served locally so the reader can ask questions back and get answers in the page. Use when the user asks to understand how something works, says "explain X to me", "I want to understand X", "teach me X", asks for an interactive page about a subject, or types /explain-topic. Not for a code change (use explain-diff), the status of work (use brief), or findings needing a file/don't-file verdict (use explain-findings).
---

# Explain Topic

Free-form input — a question, a concept, a mechanism, a piece of jargon — becomes a page the reader
can interrogate. The other page-producing skills are handed their subject (a diff, a findings list, a
body of work). **Here the subject arrives underspecified, and pinning it down is the first real step.**

## Why this exists — read this before citing it as necessary

⚠ **A no-guidance control PASSED.** Measured 2026-08-27: a fresh headless agent, given only *"explain
RLS as an interactive page I can ask questions on"*, found the delivery loop unaided and produced a
contract-compliant served page. **This skill does not prevent a measured failure.** It was requested
for two other reasons, both legitimate and neither a defect:

1. **Consistency and speed.** That agent spent ~15 minutes rediscovering the mechanism.
2. **Someone must be left to answer.** A page invites questions; a one-shot agent exits and the
   questions land where nothing reads them. **This skill runs in the user's live session** — that is
   the difference, and it is the point.

Do not cite the baseline as evidence the guidance is load-bearing. It is not.

## Which skill

| The subject is | Use |
|---|---|
| A concept, mechanism, question, "how does X work" | **this skill** |
| A code change, branch, or PR | `explain-diff` |
| Where a piece of work stands | `brief` |
| Findings needing a file / don't-file verdict | `explain-findings` |

## 1. Pin the subject before researching

Free-form input is ambiguous in a way a diff never is. "Explain the job queue" could mean the schema,
the lease protocol, the failure modes, or why it exists. **State the reading you chose in one line at
the top of the page**, so a reader who meant something else finds out in five seconds rather than
five minutes. Ask only if two readings would produce genuinely different pages.

## 2. Ground every claim, and mark the ones you could not

This is where an explainer goes wrong, because prose about a system is indistinguishable from prose
about a system you imagined. For each substantive claim, either:

- **quote** it — `file:line`, a catalog row, a real policy predicate; or
- **execute** it — run the query, read the live value; or
- **label it unverified**, in the page, in the reader's line of sight.

Prefer reading the **running system** over the source when the question is about behaviour — and say
which you read. Local and production disagree; a claim true of one can be false of the other.

**End the page with a table separating what was measured from what was inferred.** A reader cannot
tell them apart from the prose, and the difference is usually what they came for.

## 3. Build for understanding, not coverage

A page that lists everything teaches nothing. Lead with the thing that reframes the subject — the
detail that makes the rest follow — and put the traps where a reader will hit them, not in an
appendix. Sections should answer questions someone would actually ask, in the order they would ask
them.

Diagrams and tables beat paragraphs for structure and comparison. Prose beats both for *why*.

## 4. Delivery

**Follow `../shared/explainer-delivery.md`** — where the file goes, the self-contained-HTML rules,
composing the Ask tray by extraction, serving it, arming the push loop, verifying before handover,
and answering in the page. It is the one description of that loop; do not restate any of it here.

Two points from it that this skill leans on hardest:

- **Verify the affordance, not the handler.** `element.click()` fires regardless of whether a human
  could reach the button. The hit test is in the shared doc; use it.
- **Answer in the page**, not only in chat. A page whose answers live in the transcript has the
  problem it was built to solve.

## 5. Stay available

The reader will ask something. When the monitor fires, answer under the section the question came
from, recompose, and say in chat that the page is updated. **This is the whole reason the skill runs
in a live session** — if you are about to end the turn, say the page is live and questions will
reach you.

## Common mistakes

| Mistake | Why it fails |
|---|---|
| Restating the delivery procedure here | Two copies drift. `scripts/check-explainer-delivery.py` fails the build |
| Answering the question you find easiest | The reader asked something specific; §1 exists to stop this |
| Prose confidently describing unread code | Quote it, execute it, or label it unverified |
| Verifying with `.click()` | Tests the handler; a stacked, unreachable button passes |
| Dumping everything known | Coverage is not understanding |
| Ending the turn silently | The page promises answers; nobody is left to give them |
