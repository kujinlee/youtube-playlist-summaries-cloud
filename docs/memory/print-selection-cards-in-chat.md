---
name: print-selection-cards-in-chat
description: "FIRES-WHEN: about to put a decision to the user — ⛔ EVERY decision goes in an AskUserQuestion card — ALWAYS, including mid-design. The user does NOT read all the prose and misses questions buried in it. A decision in a paragraph, a page, or a PR body has not been asked"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 24bed3bc-51b2-4b47-b1fe-a488b2d3db19
  modified: 2026-09-15T05:08:06.017Z
---

## ⛔⛔ THE ABSOLUTE RULE, restated by the user 2026-09-14 — NO EXCEPTIONS, INCLUDING MID-DESIGN

> *"when you ask me for decision, use selection card so that I can easily recognise it. **I am not
> reading all your prose and easily miss your questions** — remember this"*

**The reason is the operative part: they SKIM. A question inside a paragraph is not seen.** Not
"is seen and deferred" — **not seen**. So the test is not *is prose acceptable here*, it is
**does what I do next depend on their answer?** If yes → `AskUserQuestion`. Every time.

⚠ **THIS OVERRIDES MY READING OF [[putting-a-choice-to-the-user]].** That memory says
prose during design — and on 2026-09-14 I applied it to a whole architectural discussion, presenting
three approaches and a rename question **in prose with no card**. The user had to ask *"btw, you
forgot to show selection cards for these choices. What was the decision that I need to make (two
decisions?)"* — they could not tell **that** a decision was owed, or **how many**. The correct split:

| | form |
|---|---|
| exploring, naming tensions, showing what the code says | prose |
| **any point where I need them to choose** | **a card — even mid-design, even if the surrounding turn is prose** |

Two decisions owed = two questions in one card, not two sentences in two paragraphs. And never end a
prose section with an embedded question: my inclination gets buried and the ask disappears with it.

## ✅ THERE IS NOW A MACHINE — a malformed card is REFUSED, not just discouraged

`.claude/hooks/enforce-selection-card.sh` (PreToolUse on `AskUserQuestion`) →
`scripts/check-selection-card.py` (24 cases, 6 mutations, in `EXPECTED_MUTATIONS`). Built
2026-09-10 after the measurement below. It blocks: an unlettered option, no/misplaced/duplicated
`(Recommended)`, a missing question-shaped last option, and a bare label.

⚠ **Passing it is NOT satisfying §19.** It checks SHAPE. It cannot see whether two options are the
same work — the defect §19 was written about — nor whether the axis is named, nor whether a
rationale is true. Those stay mine. Read §19 anyway; the hook is the floor, not the rule.

## ⛔ PRE-FLIGHT — READ `docs/portable-practices.md` §19 BEFORE EVERY `AskUserQuestion` CALL

**§19 IS THE RECIPE. This file is the read-trigger, not a second copy of it** — a second copy of a
rule is a copy that drifts, and that is this project's own §7/§13 lesson applied to itself.

Six checks, all of them from §19. A card failing any one of them is malformed:

1. every label starts with a letter — `A —`, `B —`, `C —`;
2. **exactly one** is marked `(Recommended)`, placed FIRST, **with its reason in the description**;
3. the LAST option is *"D — I have a question about these"*;
4. every option carries a **rationale AND a trade-off** — what it costs or gives up;
5. every option produces **different work** (two that collapse to one action is the defect that
   caused §19 to be written);
6. the **question text names the axis** — *"A/B differ in whether X ships now"*.

⚠ **MEASURED 2026-09-10, and it is why this block exists.** Three cards in one session: card 1 had
the recommendation but no letters and no question-exit; card 2 had none of the three; only card 3
complied, after two corrections. The rule was not missing — it was in §19 and in this file the whole
time. **I reconstructed it from recall instead of opening it.** The user's words: *"you seem to
deviate proven style. I'd like to have this style recorded and followed."* Recorded it already was;
what it lacked was a trigger to read at the moment of use. Related: [[it-already-exists-under-a-name-i-didnt-search]].

---

**"Print selection cards"** — user, 2026-09-09, adding: *"you used to do it but stopped"*, and
*"it should be remembered as portable practice"*.

**What I had drifted into.** I was writing decisions into `**Decide:**` blocks in the dashboard
entry and into PR bodies, then mentioning them in chat as a single trailing line
(*"two decisions are waiting on the dashboard"*). The decision was recorded, routed and rendered —
and the person who has to make it was handed a pointer instead of the choice.

**Why that fails.** This user does not follow the work in real time
([[the-user-does-not-follow-in-real-time]]). A pointer costs them a context switch — open the page, find the
tray, reconstruct what the options were and why — for something that fits in ten lines of the reply
they are already reading. Recording a decision is for durability; **printing it is how it gets
made.**

## How to apply

## ⛔ THE MECHANISM IS `AskUserQuestion`, NOT PROSE — corrected by the user, 2026-09-09

> *"previously, selection cards were literally I can select one or more and continue next selection
> cards. each selection also had a free form question or other idea selection too. it was good
> design."*

They mean the **interactive** cards: real options the user clicks, `multiSelect` where the choices
are not exclusive, **several questions in sequence**, and every one carrying a free-form escape
("Other") so they can answer something the options did not anticipate. Prose cards in the reply are
a **degraded imitation** — they cannot be selected, cannot chain, and force a typed answer.

Use `AskUserQuestion` whenever real decisions are open. Prose is the fallback only when the tool is
unavailable, or when the decision is genuinely one line. This memory originally recorded the lesson
as "print them in the reply", which was the right diagnosis (a pointer is not an ask) and the wrong
remedy.

**When writing them:** letter each label `A —`/`B —`/`C —`, set `multiSelect: true` when more than
one can be chosen, put the recommended option FIRST and mark it, and state the axis in the question
text. The tool supplies the "Other" escape itself — do not spend an option slot on it.

## The shape of a card, when prose really is the fallback

At the end of any turn that produced open decisions, print each as a card:

```
### <the question, as a question>
- **A —** <action> · *<what it costs / implies>*
- **B —** <a genuinely different action>
- **C —** <if there is one>
**Rationale:** <the evidence, one or two lines — what was measured>
**Recommendation:** <A/B/C> — <why>
```

- **Options must differ in the WORK they produce**, not the wording — see
  [[putting-a-choice-to-the-user]], where two of four collapsed into one action.
- **Always carry a recommendation.** "Your call" with no lean is the analysis-without-a-verdict
  failure in [[how-to-shape-a-message-to-me]].
- **Rationale is the measurement, not the argument.** Say what was observed.
- The dashboard `**Decide:**` block and the PR body stay — they are the durable record. The chat
  card is *additional*, never instead. Same content, two audiences.
- Applies equally when the decision is small: if I am about to write *"let me know"*, that is a
  card I have not printed.

⚠ **Do not confuse this with [[putting-a-choice-to-the-user]].** If one option is clearly
superior, decide it and say so in one line. This is for real forks only — the same bar as the
dashboard tray's `[needs-you]`.

Belongs in `docs/portable-practices.md` — the user named it a portable practice, and it is
project-independent. See [[project-has-two-deliverables]].
