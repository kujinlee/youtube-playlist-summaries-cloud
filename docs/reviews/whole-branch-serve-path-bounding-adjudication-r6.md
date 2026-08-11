# Whole-branch review #46 — ROUND 6 ADJUDICATION

| reviewer | verdict | findings |
|---|---|---|
| Codex (gpt-5.5) | **CONVERGED** | 0 — enumerated 9 values, verdict CLOSED |
| Claude (isolated worktree) | **NOT CONVERGED** | 1 High, 2 Medium, 2 Low — enumerated 11 values, verdict **"CLOSED at HEAD, and closure is not maintained by any mechanism"** |

## The most useful disagreement of the whole review

Both reviewers were asked the same question — *enumerate the population of lease-spent values and
prove the set closed* — and **both enumerated it correctly and found no instance N+4.** They then
disagreed about what that means, and the disagreement is the finding:

> Codex: the set is closed → ship.
> Claude: the set is closed **and nothing keeps it closed** → that is the difference between shipping
> this branch and shipping the thing the branch says it is.

Claude is right, and it matters here more than it usually would: this branch's entire thesis is
replacing *"the numbers happen to agree"* with *"the numbers cannot disagree"*. Shipping a correct-
but-unenforced enumeration would have reproduced, at the level of the whole design, the exact defect
the branch spent six rounds removing from its parts.

## Adjudication

| id | verdict | how established |
|---|---|---|
| **H-R6-1** the population of bounded values is not pinned | **CONFIRMED — fixed** | The guard counts calls to the three functions in its own table; a *fourth* bounded function is never searched for. The reviewer's mutant M5 — a new brand, a new bounded helper, one call inside the lease — compiles with all gates green and spends 30s the floor does not cover |
| **M-R6-1** the backoff fix cannot fail if reverted | **CONFIRMED — fixed** | `SERVE_BACKOFF_BASE_MS` is 400 and `generateJson`'s inherited default is *also* 400, so passing it and not passing it were observationally identical. A fixture-masked mutation: the other three fields were caught only because their values happen to differ from their defaults |
| **M-R6-2** the two attempt counts shared one brand | **CONFIRMED — fixed** | `AttemptCount` covered both, so the generation count was a legal settle count, with no guard behind it |
| **L-R6-1** the fourth overclaimed comment | **CONFIRMED — fixed in three places** | Round 5 asked for this sentence to be corrected and it was not. Two of its three clauses were falsified by this round's own mutants |
| **L-R6-2** `create index` blocks writes during build | **CONFIRMED — judged, recorded** | Measured: `ledger_audit` is 60 rows / 48 kB and grows one row per PAID serve. `CONCURRENTLY` cannot run inside a migration transaction, and splitting the migration is not worth it at this scale. Written into 0025 with the measurement and a revisit trigger |

## The fixes, and how each was verified

1. **A population gate** — `tests/lib/serve-budget-population.test.ts`. Every branded budget must be
   spent in the sum; every `ServeBudget` field must be an accounted scalar (so the carrier cannot
   smuggle one across the boundary); every unbranded export must be unbranded *on purpose*, with the
   reason recorded. Verified against mutant M5: it names `SERVE_VERIFY_TIMEOUT_MS` and fails.
2. **Distinct brands for the two counts** — `GenerationAttemptCount` / `SettleAttemptCount`.
   Verified: spending one as the other is now `TS2322`.
3. **A `serveBudgetWith` test minter** so a field's pass-through is observable with a value no
   default can produce. Verified: reverting the backoff pass-through is now RED, where it was green.

### A gate of mine that was vacuous, caught by my own mutation

The first population gate read a *line range* between two declarations — and most of the constants
are DECLARED in that range, so every name matched its own declaration and the check proved nothing.
It passed mutant M5 happily. Rewritten to read the right-hand sides of `SERVE_BOUNDED_MS` and
`SERVE_BACKOFF_TOTAL_MS`, so a constant counts only when genuinely SPENT.

Recorded because it is standing shape #3 — *a green gate testing the wrong thing* — written by me
while fixing standing shape #3, and caught only because the mutation was run rather than reasoned
about. That is the whole argument for mutation-testing a guard at the moment you write it.

## Scoreboard across six rounds

| round | Highs | source | reviewers' verdicts |
|---|---|---|---|
| 1 | 3 | original defects | Codex CONVERGED (wrong), Claude NOT |
| 2 | 2 | round 1's fixes | Codex CONVERGED (wrong), Claude NOT |
| 3 | 2, different per reviewer | round 2's fixes → **FIX → REDESIGN** | both NOT |
| 4 | 1, found by **both** | redesign 1's residual field | both NOT |
| 5 | 1 + 1 coordinator self-finding | redesign 1's second count | Codex CONVERGED (wrong), Claude NOT |
| 6 | 1 | the *enforcement* of the enumeration | Codex CONVERGED, Claude NOT |

**A single CONVERGED was wrong four times out of five.** Dual review was not redundancy here; it was
the gate. And in round 3 the reviewer with the worse verdict record produced the sharpest finding —
so reviewers were read on their merits every round, never weighted by reputation.

**What never produced a finding, across six rounds, three reviewers and ~50 mutations:** the bounding
mechanism itself. The static sum, the required-positional boundaries, the migration floor and the
live CHECK absorbed everything. Every High in this review was about an *instrument* or a *signal*.

## Gate status

`tsc --noEmit` clean · unit **264 suites / 2662 tests** · full integration **67 suites / 487 tests** ·
migrations 0024 + 0025 verified from scratch · `check-docs.py` OK.

**Round 7 is required by the stop condition** — round 6 returned a High, and its fixes include a new
gate, which is new unreviewed design.
