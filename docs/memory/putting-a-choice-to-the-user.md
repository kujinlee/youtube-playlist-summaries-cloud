---
name: putting-a-choice-to-the-user
description: "FIRES-WHEN: about to offer the user options — orient in prose first, then a card: verdict line first, TAG A/B/C + a question exit, recommended option first with pros/cons in realistic magnitudes, never two options that are the same action; skip the card when one option is cost-dominant"
metadata:
  type: feedback
---

**The rule as it stands (latest: owner 2026-11-01).** The pre-flight checklist is [[print-selection-cards-in-chat]]
and the canonical rule is `docs/portable-practices.md` §19; this file is how to SHAPE the choice.

1. **Is it a decision at all?** If my own option descriptions show one option cost-dominant on every axis I named,
   there is no card: state the call in one line with the measurement and start work (user, 2026-09-16:
   *"If you think the choice is obvious (zero cost) then don't even bother to provide selection cards."*). Fold
   trivial sub-choices into the write-up as stated decisions. Real gates (spec approval, a HOLD) are still asked.
2. **Orient before deciding.** For anything non-trivial: (1) orientation in prose — the problem, the mechanism,
   what is safe vs risky, my leaning and why; (2) let them probe; (3) only then the card. The tell that I skipped
   (1): option descriptions that need a paragraph each.
3. **If the next action depends on their answer, it is a CARD** — even mid-design ([[print-selection-cards-in-chat]]).
   Two answers owed = two questions in one card, never a paragraph hinting at both. Pure exploration (naming
   tensions, what the code shows) stays prose; do not end every design turn with a menu.
4. **Lead with the VERDICT in plain words** (owner 2026-11-01 10:14): one sentence — is the realistic benefit big
   or small, does the risk outweigh it; then any correction to numbers I gave earlier and WHICH past decisions it
   touches; then pros/cons; then the card.
5. **Card shape:** tag every option `A —`, `B —`, `C —`; the last option is *"I have a question about these"*;
   the question text says what the options differ on. Recommended option FIRST with `(Recommended)` and its
   reason, on EVERY card. Non-neutral choices are not framed neutrally: label the others *unsafe* or *redundant*.
6. **Every option carries `Pro: … Con: …` in REALISTIC impact** (owner 2026-11-01 10:10: *"provide pros and cons
   analysis (in realistic impact) when you present selection"*): tokens or % of weekly limit, minutes/days, what
   breaks, how likely. If the card cannot hold it, a short table right above the card.
7. **Each option must produce DIFFERENT work.** A menu whose entries collapse implies a distinction that is not there.

**Why:** the user skims and reads late ([[the-user-does-not-follow-in-real-time]]); a card is how a decision is
seen, but a card without orientation, magnitudes or a recommendation cannot be answered confidently, and a card for
an obvious choice is ratification theatre.

**How to apply:** before sending a card, read my option descriptions back against points 1, 6 and 7. Related:
[[feedback-agree-before-filing]], [[how-to-shape-a-message-to-me]], [[never-close-with-a-promise]],
[[process-conventions]].

## History (merged from `feedback-tag-options-and-offer-a-question`, `feedback-prefer-discussion-over-menus`, `feedback-dont-ask-when-obvious`)

- **2026-07-11** (Stage 2c): asked new-tab-vs-iframe when new-tab was obviously right; user pushed back → decide
  obvious choices myself.
- **2026-07-24** (#13 dev-login): a neutral 3-option card where A was right, B unsafe, C redundant; user: *"state
  the points clearly and recommend clearly so I don't have to spend much time."*
- **2026-07-31**: two consecutive cards during a design discussion rejected — *"I wasn't going to skip it. rather
  I wanted to discuss about the details."* → prose while exploring.
- **2026-09-04**: user replied to a menu *"What is the difference between first and last choices?"* — two of four
  options were the same action; no question-shaped exit → A/B/C tags + question option.
- **2026-09-10**: *"for selection cards, provide recommendation whenever appropriate."* — first card had
  `(Recommended)`, two later ones none.
- **2026-09-14**: OVER-APPLIED the prose rule — three approaches and a rename question in prose, no card. User:
  *"btw, you forgot to show selection cards for these choices. What was the decision that I need to make (two
  decisions?)"* → the line is exploration vs decision, not design vs implementation.
- **2026-09-16** (backlog #137): a 3-option card whose option A read *"zero added wall clock, Actions minutes are
  free"* while B/C cost a script or a CI restructure; they picked A and said not to have asked.
- **2026-09-18** (wake-on-visit): went straight to a §19-compliant card with the analysis packed into option
  descriptions; user: *"let's have discussion phase before you let me decide with selection cards. Without
  understanding your intent with background, I cannot choose confidently."* After one prose explanation: *"this is
  better"* → the orientation→discussion→card order.
- **2026-11-01**: the global-trim card first claimed 2–3 KB; the measured saving was ~1 KB → magnitudes required.
