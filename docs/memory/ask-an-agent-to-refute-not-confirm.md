---
name: ask-an-agent-to-refute-not-confirm
description: "FIRES-WHEN: writing the prompt for a verification, mapping or research agent (not a review half — those are already adversarial) — ⭐⭐ a REFUTATION mandate found in minutes what a confirming one ratified, including a wrong correction I had already published. Default to 'refuted' if uncertain"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 47586cf2-5f2e-4357-8ff6-1ddf3a06b5ee
  modified: 2026-09-23T16:24:05.498Z
---

**RULE: when dispatching an agent to check a finding or map a subject, tell it to REFUTE, not verify —
and to default to *refuted* when uncertain.** A confirming prompt gets agreement, the cheapest thing an
agent produces.

**Which population:** the dual-review protocol already dispatches Claude REVIEW HALVES adversarially
(33 documents under `docs/reviews/` carry *"Claude (adversarial mandate)"*; `docs/plugins.md` specifies
one for the Codex fallback). The gap is the OTHER agents — `Explore`/research agents prompted *"map the
family"* / *"answer these questions"*, which are confirming by construction.

**How to apply:**
- Say it: *"Your job is to REFUTE this, not confirm it. Default to 'refuted' if uncertain. A refutation
  is worth more to me than agreement."*
- **Name the failure mode you most fear** and ask them to hunt it (*"is my synthetic fixture
  representative of what the real code does?"* found the #164 error).
- Give the claim WITH its evidence, so they attack the reasoning rather than re-derive it.
- Apply it to your own findings: *what would I see if this framing were wrong?* **Before writing
  "nothing/never/only" about this repo, run the grep.**
- ⚠ Record whether you ran a refutation or a confirmation — a reader cannot tell them apart afterwards,
  and a survived refutation is much stronger.

**Why:** a wrong confirming agent costs a false green you never look at again; a wrong refuting agent
costs five minutes of re-measurement.

## History — measured 2026-09-23, four for four (observer-family architecture review)
| Prompt shape | What came back |
|---|---|
| *"map the observer-log family"* (confirming) | a SUMMARY contradicting its own TABLE — called a referrer list "still accurate" including a `block-idle-stop.sh` comment its 19-file table omitted. Re-measured: **0** references |
| *"try to break this claim, default to refuted"* | **refuted a sub-claim already published into backlog #164** — `step` is not a parameter of `check-banner-armed.decide`; the banner rides inside `texts` (`:503`) |
| *"try to break this claim"* (2nd) | survived, but supplied a better control: `analyse` returns `(findings, examined_keys)` (`:703-708`) so "did not fire" and "no longer examined" are distinguishable |
| the same discipline on MYSELF | F12's *"nothing states which rule is correct"* was too strong — `begin-plan.py:518-520` |

- The user asked *"have you done something to keep the pattern?"* — I had named it twice in chat and built
  nothing. Naming a class does not stop it; this file and the rule in `docs/review-method.md` are the mechanism.
- Same day: this memory's first version claimed *"nothing says how to prompt a Claude subagent"* — FALSE
  (the 33 documents above). The user's *"I cannot believe this"* was the falsifier. See
  [[quote-the-code-dont-characterise-it]].

Related: [[dual-review-what-it-catches]], [[a-filed-finding-s-proposed-fix-is-a-hypothesis]],
[[measure-the-population-the-code-actually-sees]], [[agent-tool-restriction-has-no-owner]]
