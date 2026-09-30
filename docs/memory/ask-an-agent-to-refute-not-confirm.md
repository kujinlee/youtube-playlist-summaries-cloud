---
name: ask-an-agent-to-refute-not-confirm
description: "FIRES-WHEN: writing the prompt for a verification or research agent — ⭐⭐ A verification agent given a REFUTATION mandate found in minutes what a confirming one ratified — including a wrong correction I had already published to the backlog. Default to 'refuted' if uncertain"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 47586cf2-5f2e-4357-8ff6-1ddf3a06b5ee
  modified: 2026-09-23T16:24:05.498Z
---

**When dispatching an agent to check a finding, tell it to REFUTE the finding, not to verify it —
and tell it to default to *refuted* when uncertain.** A confirming prompt gets agreement; agreement
is the cheapest thing an agent produces.

**MEASURED 2026-09-23, four for four**, on the observer-family architecture review:

| Prompt shape | What came back |
|---|---|
| *"map the observer-log family"* (confirming) | a report whose SUMMARY contradicted its own TABLE — it concluded a docstring's referrer list was "still accurate" including a `block-idle-stop.sh` comment, while its own 19-file table omitted that hook. Re-measured: **0** references |
| *"try to break this claim, default to refuted"* | **refuted a sub-claim I had already published into backlog #164** — my worked example rested on `step` being a parameter of `check-banner-armed.decide`, and it is not; the banner rides inside `texts` (`:503`) |
| *"try to break this claim"* (2nd) | SURVIVED the main claim but supplied a **better control than mine**: `analyse` returns `(findings, examined_keys)` as a SET (`:703-708`) precisely so *"this entry did not fire"* and *"this parameter is no longer examined"* are distinguishable. My original run never reported it, so I could not have told a real pass from a vacuous one |
| the same discipline applied to MYSELF | F12's *"nothing states which rule is correct"* was too strong — `begin-plan.py:518-520` states quite a lot |

⭐ **The asymmetry is the whole point.** A confirming agent that is wrong costs you a false green you
will never look at again. A refuting agent that is wrong costs you five minutes of re-measurement.
The expected values are not close.

**How to apply:**

- Say it explicitly: *"Your job is to REFUTE this, not confirm it. Default to 'refuted' if
  uncertain. A refutation is worth more to me than agreement."*
- **Name the failure mode you most fear** and ask them to hunt it — *"is my synthetic fixture
  representative of what the real code does?"* is what found the #164 error.
- Give them the claim WITH its evidence, so they attack the reasoning rather than re-derive it.
- Apply it to your own findings before publishing: *what would I see if this framing were wrong?*
- ⚠ **A survived refutation is a much stronger result than a confirmation** — record which one you
  ran, because a reader cannot tell them apart afterwards.

⛔ **THE TRAP THIS MEMORY EXISTS FOR:** on 2026-09-23 I observed this pattern, wrote it in a review
document, said in chat twice that it was "worth keeping" — and built nothing. The user asked *"have
you done something to keep the pattern?"* and the answer was no. That is the exact failure the same
day's architecture review spent 587 lines documenting: **naming a class does not stop it; prose is
not the missing mechanism.** Writing this file, and the rule in `docs/review-method.md`, is the
mechanism.

Related: [[dual-review-what-it-catches]], [[a-filed-finding-s-proposed-fix-is-a-hypothesis]],
[[measure-the-population-the-code-actually-sees]], [[agent-tool-restriction-has-no-owner]]

⟳ **CORRECTION, same day, prompted by the user refusing to believe the framing.** This memory's
first version rested on my claim that *"nothing says how to prompt a Claude subagent"*. **FALSE.**
Measured: **33 documents** under `docs/reviews/` carry a reviewer line *"Claude (adversarial
mandate)"*, and `docs/plugins.md` specifies one for the Codex-fallback path verbatim. Claude REVIEW
HALVES have been dispatched adversarially for months.

⭐ **The gap is a DIFFERENT POPULATION, and naming it wrongly nearly buried the real finding.** The
dual-review protocol covers the two review halves. It says nothing about the agents you dispatch to
**map a subject or check a finding** — and all four of the measured dispatches above were `Explore`
agents, prompted *"map the family"* / *"answer these questions"*, which are **confirming by
construction**. That is the population that needs the rule.

⚠ **The lesson inside the lesson:** I reached for "nothing anywhere" without grepping, in a session
whose whole subject was claims that outrun their evidence. The user's *"I cannot believe this"* was
the falsifier. **Before writing "nothing/never/only" about this repo, run the grep** — see
[[quote-the-code-dont-characterise-it]].
