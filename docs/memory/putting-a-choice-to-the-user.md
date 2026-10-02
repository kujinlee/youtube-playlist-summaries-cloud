---
name: putting-a-choice-to-the-user
description: "FIRES-WHEN: about to offer the user options — ⭐ How to offer a decision: TAG options A/B/C with a question-shaped exit, never ship two options that are the SAME action, prefer prose during design, and decide it yourself when one option is obviously superior"
metadata:
  type: feedback
---

> Merged 3 memories, bodies kept VERBATIM. Former names (still referenced by other memories): `feedback-tag-options-and-offer-a-question`, `feedback-prefer-discussion-over-menus`, `feedback-dont-ask-when-obvious`

## feedback tag options and offer a question

⛔ **THIS FILE IS THE INCIDENT, NOT THE RULE.** The rule lives in `docs/portable-practices.md` §19
and the pre-flight checklist is in [[print-selection-cards-in-chat]]. Read one of those before
writing a card; what follows is why §19 says what it says. Three copies of one rule is how it drifts.

When presenting choices, **tag each option `A —`, `B —`, `C —` …** and make the LAST option
**"I have a question about these"**, so the user can push back instead of being forced to pick.

**Why:** asked directly on 2026-09-04. The user's actual reply to a menu was *"What is the
difference between first and last choices?"* — they had no way to say that except by typing it as an
"Other". A menu with no question-shaped exit forces a decision where a clarification was wanted.

**How to apply:** in `AskUserQuestion`, prefix each `label` with its letter, and add a final option
like *"D — I have a question about these"* whose description invites them to say what is unclear.
State in the question text what the options actually differ on ("A/B differ in whether X goes live
now") — that is the thing they are choosing between.

⚠ **The trigger for the complaint was a real defect in my options, not just missing labels.** Two of
four were the *same action* dressed differently ("merge both in order" vs "merge both, review
after"); the ordering in one was a mechanical constraint, not a choice. Before presenting, check
that each option produces *different work*. A menu whose entries collapse is worse than prose,
because it implies a distinction that is not there.

⭐ **MARK THE RECOMMENDED OPTION — on EVERY card, not just the first one of a session.** Asked
directly on 2026-09-10: *"for selection cards, provide recommendation whenever appropriate."* The
trigger was a session that put "(Recommended)" on its first card and then shipped two later cards
with none, so the user had three well-argued options and no idea which I would pick. Put the
recommended option FIRST with `(Recommended)` in its label, and carry the rationale in the
description — a recommendation with no reason is just an instruction.

⚠ Not the same as [[putting-a-choice-to-the-user]]: that says *don't ask* when one option clearly
wins. This says that when the choice IS genuinely the user's, they still want to know what you would
do. Having a recommendation is not a reason to skip the card; hiding it is the failure.

See also [[putting-a-choice-to-the-user]] — prose during *design*; tagged options when a
**decision** is genuinely needed. And [[putting-a-choice-to-the-user]] — do not ask at all when
one option is clearly superior.

## feedback prefer discussion over menus

When the user is **thinking through a design**, respond in prose and let the discussion breathe.
Do not close each turn with an `AskUserQuestion` menu of options.

**Why:** on 2026-07-31, during a design discussion about section identity and sync authority, the
user rejected two consecutive `AskUserQuestion` calls (each with 2–3 elaborate options and
previews), saying *"I wasn't going to skip it. rather I wanted to discuss about the details."* The
menus converted an open design conversation into a series of forced choices, which skipped past the
details they wanted to examine. The productive turns were plain prose: present what the code shows,
name the real tension, and let them steer.

**How to apply:** reserve `AskUserQuestion` for a genuine fork where you are blocked and the answer
changes what you build next. In design discussion, state findings, name the tradeoff, and stop —
the user will direct. This does **not** conflict with [[putting-a-choice-to-the-user]]: that one
says decide instead of asking when an option is obviously superior; this one says discuss instead of
asking when the user is still exploring the problem.

## ⟳ CORRECTED 2026-09-14 — I OVER-APPLIED THIS AND DROPPED THE CARD AT THE DECISION POINT

Designing the review decision procedure, I ran the whole exploration in prose — correctly — and
then **presented three approaches and a rename question in prose too, with no card**. The user had
to ask: *"btw, you forgot to show selection cards for these choices. What was the decision that I
need to make (two decisions?)"* — they could not tell what they were being asked.

⭐ **THE LINE IS EXPLORATION vs DECISION, not design vs implementation.**

| | form |
|---|---|
| exploring the problem, naming tensions, showing what the code says | **prose** — this memory's original rule |
| *"pick one of these and I will build it"* | **a card**, §19-compliant, even mid-design |

A design conversation contains both, often in the same message. Ending a prose exploration with an
embedded question is the failure: my inclination gets buried in a paragraph and the user cannot see
that a decision is owed, or how many. **If the next thing I do depends on their answer, it is a
card** — and if two answers are owed, that is two questions in one card, not a paragraph hinting at
both. See [[print-selection-cards-in-chat]] and [[putting-a-choice-to-the-user]].

## ⟳⟳ CORRECTED 2026-09-18 — BOTH FORMS ARE RIGHT; I HAD THE **ORDER** WRONG

Reviewing the wake-on-visit slice, round 1 surfaced two Blockings that hinged on an unsettled
deployment-topology question. I went **straight to a §19 card** with the whole analysis packed into
the option descriptions. The user rejected it, and then said why:

> *"let's have discussion phase before you let me decide with selection cards. Without understanding
> your intent with background, I cannot choose confidently."*

⭐ **A CARD IS NOT A SUBSTITUTE FOR ORIENTATION, AND RATIONALE-IN-THE-OPTION DOES NOT SUPPLY IT.**
§19 requires each option to carry a rationale and a trade-off, and mine did. That made the card
*compliant* and still unusable, because a rationale explains one option against the others — it
cannot build the shared model of the mechanism needed to judge any of them. The user was being asked
to choose between Fly deployment topologies without first being told how Fly Proxy autostart works,
why a `[[services]]` block is the hinge, or which half of the slice is the risky one.

**The sequence for anything non-trivial:**

| phase | form | what it must deliver |
|---|---|---|
| 1 — orientation | prose | the concept: what problem, what mechanism, the key asymmetry, what is safe vs risky, and **my intent and leaning, with its reasoning** |
| 2 — discussion | prose | let them probe it; a good decision often falls out here and the card becomes unnecessary |
| 3 — decision | §19 card | only once the model is shared |

⚠ **The tell that I have skipped phase 1:** the option descriptions are long. If a card needs a
paragraph per option to be intelligible, that paragraph is the orientation I failed to write, and it
is in the worst possible place — inside a widget the user must decide on while reading it.

⚠ Do not read this as "ask less". Phase 3 is still mandatory when the next action depends on their
answer (the 2026-09-14 correction above stands). The change is that phases 1–2 come **first**, and
skipping them to reach the card faster is what made the card unanswerable.

Measured the same day: after one prose explanation of the design, the user's reply was *"this is
better"* — the same two decisions, now answerable.

Related: [[feedback-agree-before-filing]], [[print-selection-cards-in-chat]],
[[how-to-shape-a-message-to-me]]

## feedback dont ask when obvious

When brainstorming/designing, if one option is quite obviously superior (or is my
strong recommendation with no real competing tradeoff), **do not ask the user to
choose** — make the call, state it briefly, and proceed. Reserve AskUserQuestion for
genuine forks where the answer materially changes direction and reasonable people
would differ.

**Why:** the user runs an AFK-minimizing workflow and prefers plain, low-friction
interaction ([[the-user-does-not-follow-in-real-time]], [[process-conventions]]). Being
asked to rubber-stamp an obvious choice is friction that wastes a touchpoint. Concrete
trigger (2026-07-11, Stage 2c): I asked new-tab-vs-iframe for the summary viewer when
the self-contained magazine page made new-tab obviously right; user pushed back.

**How to apply:** default to deciding. Fold trivial sub-choices (default TTL, flat vs
submenu, copy semantics) into the design writeup as stated decisions, not questions.
Still honor the real gates (spec approval, merge) — those are required review
checkpoints, not "obvious choice" questions. Surface only genuine forks/blockers.

**⛔ REFINEMENT (2026-09-16, backlog #137) — THE SHARPEST FORM, AND IT RESOLVES THE TENSION WITH
[[print-selection-cards-in-chat]].** User, verbatim: *"If you think the choice is obvious (zero
cost) then don't even bother to provide selection cards."*

**The test is MY OWN ANALYSIS, not the topic's weight.** If the card's own rationale text says one
option costs nothing and the others cost real work, the card is theatre — I have already decided,
and I am asking them to ratify it. Trigger: a 3-option card on how to make a CI check always report,
where option A's description literally read *"zero added wall clock, Actions minutes are free"* and
B/C each cost a new script or a CI restructure. They picked A and told me not to have asked.

**How to apply.** Before offering a card, read my own option descriptions back: if one is
cost-dominant on every axis I named, **delete the card, state the call in one line with the
measurement, and start work.** [[print-selection-cards-in-chat]] still governs GENUINE forks — the
rule there is *where* a real decision gets made (in chat, not routed into a doc or PR body), not
that every choice is a decision. ⚠ A card is still right when the axes genuinely trade off, and
still right when I have found NEW information that changes the price — but then the honest move is
to say the price changed and proceed, not to re-card the same direction
([[never-close-with-a-promise]]).

**Refinement (2026-07-24, #13 dev-login):** even when I *do* lay out options, don't
present them as a neutral N-way question if they aren't neutral. LEAD with the clear
recommendation and WHY, and explicitly label the others **unsafe** or **redundant** so
the user can rubber-stamp in seconds instead of evaluating each. Trigger: I posed a
balanced 3-option AskUserQuestion (server-gate vs client-gate vs both) when A was
obviously right, B unsafe, C redundant; user said "state the points clearly and
recommend clearly so I don't have to spend much time." A neutral multiple-choice for a
non-neutral decision is itself the friction to avoid — reserve AskUserQuestion's
even-handed framing for genuinely even choices.

