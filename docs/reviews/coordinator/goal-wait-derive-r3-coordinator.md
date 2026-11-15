# goal-wait-derive (PR #592, backlog #650) — round 3, coordinator

REVIEW GAP: claude — alternation (round 3 is the Codex half; rounds 2+ alternate, `docs/review-method.md` → *Round topology*).

Codex round 3 (`docs/reviews/codex/goal-wait-derive-r3-codex.md`), at `d3b1e5a4`: NOT CONVERGED, 3 MAJOR + 1 MINOR.

| # | Severity | Finding | fix_induced | Disposition |
|---|---|---|---|---|
| 1 | MINOR | `after PR #442 and PR #451` keeps only PR #442; premature idle alarm | true (round-2 N2) | REMOVED BY REDESIGN — the matcher is deleted; prerequisites are declared in the ledger's `after` field |
| 2 | MAJOR | `waiting for PR #442` / `blocked on PR #442` never expire | true (round-2 N2) | REMOVED BY REDESIGN — prose waits are shown verbatim and never parsed; a prerequisite is declared |
| 3 | MAJOR | `Do not do this: start after PR #451` — the colon strips the negation and hides an idle item | true (round-2 N4) | REMOVED BY REDESIGN — `what` is never read for refs |
| 4 | MAJOR | `PR #442 or PR #451` treated as needing both | false | REMOVED BY REDESIGN — alternatives are not expressible; a declared list means all, stated in the review |

**THRASHING armed:** round 2's findings came from round 1's fix, and round 3's from round 2's, in the same two components (prerequisite matcher, wait resolver). The Phase 6 review is `docs/reviews/coordinator/architecture-review-2026-11-15-goal-wait-derive.md`. It recommends deleting both components in favour of a declared `after` list; the redesign is built on this branch.

Outcome: continued. The next round reviews the redesign.
