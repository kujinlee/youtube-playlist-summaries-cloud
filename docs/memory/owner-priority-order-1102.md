---
name: owner-priority-order-1102
description: "Choosing what to work on next? Owner 11-02: ONE goal, two lanes — DIRECTION (comprehensibility, needs the owner: do it while they are present) and THROUGHPUT (dev speed: while AFK); YouTube product third"
metadata:
  type: project
---

**Owner, 2026-11-02 09:05**, after the token-usage work was judged done (high-impact builds shipped, effect measured at
the 11-06 reset): *"Our main thrust was comprehensibility suite and publishing them as public tool (as plugin) and
development speed enhancement. After these, original youtube playlist product at 3rd priority."*

1. **Comprehensibility suite, published as a public plugin.** Gated on the owner's walkthroughs: backlog #384 (roles
   page `docs/explainers/2026-10-28-topic-suite-roles-review.html`, several answers open) and PR #376 (the
   marketplace-inventory spec, "could a stranger use any of this", parked 11-01). Phase 1 is the human gate
   ([[document-approval-is-interactive]]), so walkthroughs come first when the owner is present.
2. **Development speed.** Speed backlog rows, led by #405 (mutation harness stops at the named case) and #406.
3. **The YouTube product** (PR #392 and the rest).

**Why:** supersedes the 10-30 "token usage FIRST" ordering ([[behavior-follows-the-budget-situation]]); token work
returns to the front only if the 11-06 measurement shows no drop.
**How to apply:** while a priority-1 item waits on the owner, work priority 2 autonomously; do not start product work
ahead of 1 and 2.

**⟳ 2026-11-02 09:09, the owner:** *"let's make development speed issues higher priority than others."* The order is now
**1. development speed, 2. comprehensibility suite → public plugin, 3. the YouTube product.** Speed rows go first even
when a suite walkthrough is answered; the suite walkthroughs (#384, PR #376) still happen whenever the owner offers them.

**⟳ 2026-11-02 09:12, the owner:** *"comprehensibility side is also closely intertwined … If I cannot correctly understand what you
are doing or how the project is progressing, dev speed in local sense doesn't have much meaning. It may be tactically fast, but
heading to wrong direction (strategically incorrect or operationally sub-optimal)."* So: **one goal, two lanes.** DIRECTION
(comprehensibility: #384 suite design, PR #376 plugin spec, anything that lets the owner steer) goes first WHILE THE OWNER IS
PRESENT, because it needs their time; THROUGHPUT (speed rows #405, #406, #448–#451 …) runs while they are AFK. Passive signal
for the direction lane: owner messages per day asking "what is this?" / "read my questions" / a re-ask, from the transcripts;
reported at the 11-06 reassessment ([[behavior-follows-the-budget-situation]]).

**⟳ 2026-11-02 09:29 walkthrough results.** PR #376 (plugin inventory): **D2 KEPT** — inventory all three efforts before
any per-unit spec; next step there is a re-merge (92 commits behind) and a refresh, not a narrowing. Backlog #384: every
roles-page item answered (all as recommended), spec PR #474 drafted and walked through; the owner refined D1 into TWO
"needs you" sets with one source each — *blocking now* (in-flight ledger) and *waiting until picked* (backlog
`status: needs-you`). Backlog readability: *"without changing current wording … line break, indenting"* — layout only,
falsifier = identical visible words over every real row.
