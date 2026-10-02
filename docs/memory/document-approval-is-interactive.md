---
name: document-approval-is-interactive
description: "FIRES-WHEN: about to send the user a spec or plan for approval — Specs and plans go to the user as an INTERACTIVE page they can question, never as a yes/no — a document behind a single approval is a rubber stamp by construction"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 1e3f81fb-0947-4bcb-8aac-4219e1d96379
  modified: 2026-09-25T21:00:53.148Z
---

⛔ **A spec or plan put to the user as "approve?" gets RUBBER-STAMPED, and the user said so directly
(2026-09-25):** *"I didn't have chance to walk through the document with you currently and I tend to
rubberstamp the approval."*

**The user's preferred form: interactive question-and-answer OVER the document** — the same shape as
an `explain-topic` page that can ask the session a question and render the answer in the page.

**Why:** the Phase 1 gate is the ONLY human sign-off in the whole workflow (`docs/dev-process.md` —
*"the spec is the human gate"*; Phases 2 and 3 then run autonomously). So a rubber stamp there is not
one weak checkpoint among many — it is the single point of human control, disabled. And the cause is
mechanical, not attentional: a 243-line document with one yes/no attached offers no way to ask about
paragraph 40, so the only available action is "yes".

**How to apply:**
- ⛔ **Never close a spec or plan with a bare approval request.** Build the page first, hand over the
  URL, and let the gate be the conversation that happens on it.
- Use the page-producing machinery that already exists — `.agents/skills/shared/explainer-delivery.md`
  is the one delivery loop (`explain-topic`, `brief`, `explain-diff`, `explain-findings` all cite it).
  ⚠ **§5b — execute and verify the page — is the PARENT's job and is not delegable.**
- The page must carry the things a reader would otherwise have to take on trust: what approving
  commits them to, what it does NOT commit them to, the decisions the document makes, and the places
  a reviewer already pushed back.
- ⭐ **Run the adversarial review BEFORE the page, not after.** Walking someone through claims that a
  reviewer is about to refute wastes the one interaction that matters. See
  [[ask-an-agent-to-refute-not-confirm]].
- Related, same user, same root cause: [[print-selection-cards-in-chat]] (the user SKIMS, so prose
  questions are not seen) and [[the-user-does-not-follow-in-real-time]].
