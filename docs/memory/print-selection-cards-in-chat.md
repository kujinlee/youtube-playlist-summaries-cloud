---
name: print-selection-cards-in-chat
description: "FIRES-WHEN: about to put a decision to the user — ⛔ a decision in CHAT goes in an AskUserQuestion card, ALWAYS, incl. mid-design; a decision on a page under review gets a yellow ✍ DECISION tag + counter instead. The user skims; a question in prose or a PR body has not been asked"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 24bed3bc-51b2-4b47-b1fe-a488b2d3db19
  modified: 2026-09-15T05:08:06.017Z
---

## The rule (current)

1. **A decision raised in CHAT → an `AskUserQuestion` card. Every time, including mid-design.** Test: *does what I
   do next depend on their answer?* If yes → card. Prose is for exploring; any point where they must choose is a card,
   even inside a prose turn. Two decisions = two questions in one card. Never end a prose section with an embedded
   question.
2. **A decision on a PAGE the owner is reviewing → NOT a card** (a card interrupts the review). Mark it in the page like
   a contract SIGNATURE LINE: a YELLOW "✍ DECISION n of N" tag at the spot, plus a counter at the top ("Decisions: N
   total · M remaining"), each flipping to answered. Still name the open ones in the ⛔ line of every chat status.
3. **Relaying a report:** grep it for "owner could", "optionally", "your call", "if you prefer" — each is a fork and
   goes on a card in the same turn, never into a table row. "Optional" is a decision with a default.
4. **When I take my own recommendation for lack of an answer**, say so in the ⛔ line as **TAKEN BY DEFAULT —
   overturn?**, never in prose.
5. **In AFK mode, a card BLOCKS** — decide anything reversible myself and flag it (rule 4); block only on what is
   critical. See [[a-blocking-question-while-afk-costs-the-whole-night]].
6. If one option is clearly superior, decide it and say so in one line — cards are for real forks
   ([[putting-a-choice-to-the-user]]).

**Card shape — READ `docs/portable-practices.md` §19 BEFORE EVERY `AskUserQuestion` CALL.** §19 is the recipe; this
file is the read-trigger, not a copy. Its six checks: lettered labels (`A —`, `B —`); exactly one `(Recommended)`,
FIRST, reason in the description; LAST option *"D — I have a question about these"*; each option has a rationale AND a
trade-off; every option produces DIFFERENT work; the question text names the axis. Use `multiSelect: true` when
choices are not exclusive. Always carry a recommendation ([[how-to-shape-a-message-to-me]]).

**The machine:** `.claude/hooks/enforce-selection-card.sh` (PreToolUse on `AskUserQuestion`) →
`scripts/check-selection-card.py` refuses a malformed card (unlettered option, missing/misplaced/duplicate
`(Recommended)`, no question-shaped last option, bare label). ⚠ It checks SHAPE only — it cannot see two options
that are the same work, an unnamed axis, or a false rationale. Those stay mine.

**Why:** the user, 2026-09-14: *"when you ask me for decision, use selection card so that I can easily recognise it.
**I am not reading all your prose and easily miss your questions** — remember this"*. A question in a paragraph is
not seen — not deferred, NOT SEEN. The user does not follow the work in real time
([[the-user-does-not-follow-in-real-time]]), so a pointer to a page costs them a context switch. And 2026-10-27: *"you recommended in a transcript which I may or may not read
(mostly not). if you want some real action, it must be a selection card."*

**How to apply:** the dashboard `**Decide:**` block and the PR body stay as the durable record; the card is
additional, never instead. Prose cards (the `### question / A — / B — / Rationale / Recommendation` shape) only when
the tool is unavailable. Belongs in `docs/portable-practices.md` ([[project-has-two-deliverables]]).

## History

- **2026-09-09:** *"Print selection cards"* — *"you used to do it but stopped"*, *"it should be remembered as portable
  practice"*. I had been routing decisions into dashboard `**Decide:**` blocks and PR bodies with a one-line pointer in
  chat. Then corrected to the interactive tool: *"previously, selection cards were literally I can select one or more
  and continue next selection cards. each selection also had a free form question or other idea selection too. it was
  good design."*
- **2026-09-10, measured:** three cards in one session — card 1 lacked letters and the question-exit, card 2 had none
  of the three, only card 3 complied after two corrections. I reconstructed §19 from recall instead of opening it
  ([[it-already-exists-under-a-name-i-didnt-search]]). *"you seem to deviate proven style. I'd like to have this style
  recorded and followed."* The hook was built that day.
- **2026-09-14:** presented three architectural approaches and a rename question in prose, no card. *"btw, you forgot
  to show selection cards for these choices. What was the decision that I need to make (two decisions?)"*
- **2026-10-27:** relayed a subagent's "the owner could optionally choose X or Y" as a table cell (rule 3).
- **2026-11-11 05:58:** two decisions sat in an explainer-page section titled *"Two things I would like you to
  check"*; the owner reviewed the other page, approved the spec, and I took my own recommendations. *"If I need to make
  a decision on a point, can you clearly flag them so that I don't miss? … I need to know clearly when you need my
  decisions."* Refined 06:03 into rule 2.
