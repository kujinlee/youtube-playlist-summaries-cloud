# Whole-branch review #46 — ROUND 3 ADJUDICATION

| reviewer | verdict | findings |
|---|---|---|
| Codex (gpt-5.5) | **NOT CONVERGED** | 1 High, 1 Low |
| Claude (isolated worktree) | **NOT CONVERGED** | 1 High, 2 Medium, 3 Low |

**Both reviewers found a High. They are different Highs, and both were confirmed by measurement.**
Both also independently answered the escalation question **"wrong shape"** — for two different
components.

## The reviewers swapped roles, and that is worth recording

Codex returned CONVERGED in rounds 1 and 2 and was wrong both times. In round 3 it produced **the
sharpest finding of the entire review**: my round-2 "class" guard asserted that the expected token
*appears somewhere in the argument text* (`args.filter(a => a.includes(constant))`), not that the
argument **is** the constant — so `SERVE_PUT_TIMEOUT_MS + SERVE_MARGIN_MS` passed it while silently
spending the 20s unmodelled-work margin as enforced wait. I reproduced it: `tsc` exit 0, guard 8/8
green, 2653/2653 tests green.

The lesson is not "Codex got better". It is that a reviewer's verdict track record does not predict
its next finding, and that **weighting reviewers by reputation would have thrown away the most
valuable finding in three rounds.** Both were read on their merits, every round.

## Adjudication

| id | source | verdict | how established |
|---|---|---|---|
| **H-R3-C1** the class guard accepts a larger expression containing the constant | Codex | **CONFIRMED — dissolved by redesign** | Reproduced the `+ SERVE_MARGIN_MS` mutant myself: everything green |
| **H-R3-A1** the settle signal cannot be acted on — `indeterminate` names a table that records no settle, and no money log carries an identifier | Claude | **CONFIRMED — dissolved by redesign** | `settle_serve_model`'s only `ledger_audit` writes are `release_underflow` (`0020:281,287,294`); a clean settle writes nothing. Verified in the live catalog. And `grep` over the six `console.*` lines: not one carried owner, doc, day or token |
| **M-R3-1** the `anAttemptMayHaveCommitted` latch's `error` half was unpinned | Claude | **CONFIRMED — fixed** | Now pinned by a test: errored attempt → no-op reply → `indeterminate`, not `refused` |
| **M-R3-2** a failed KEEP settle was silent on the throw path, logged on the success path | Claude | **CONFIRMED — fixed** | Same event, now logged on both terminal paths |
| **L-R3-1** the no-literals rule could not see hex/exponential literals | Claude | **CONFIRMED — fixed** | `0x1D4C0` mutant now red on both guard rules (and a type error besides) |
| **L-R3-2** the guard pins syntactic call sites, not executed invocations | Claude | **ACCEPTED, recorded** | True. A call inside a loop is one syntactic site. The brands make the VALUE right regardless; multiplicity is what `SERVE_*_ATTEMPTS` covers |
| **L-R3-3** `data === null` was read as a database refusal | Claude | **CONFIRMED — fixed** | Only `false` is a refusal now; anything else is `indeterminate` with its own log |
| **L-R3-C1** the migration comment pointed at the old (integration) home of the floor pin | Codex | **CONFIRMED — fixed** | Comment now names `tests/lib/serve-budget.test.ts` |

## The escalation verdict, and what I did with it

`review-method.md`'s trigger fired: round 2's Highs came from round 1's fixes, round 3's Highs came
from round 2's fixes. Both reviewers said **wrong shape**. They disagreed about *which* shape, and
the disagreement is the most useful thing in this round — because they were each right about a
different component:

**1. The BUDGET BOUNDARY (Codex).** Three rounds, three detectors, each defeated by a slightly
different expression: an object literal, a decimal literal, an arithmetic expression. Every fix
taught the detector one more shape.

> **Redesign: stop detecting, start making it unrepresentable.** Every budget in
> `lib/serve-budget.ts` is now branded with the call site it belongs to, and every bounded API
> demands its own brand. Arithmetic on branded numbers yields `number`; a literal is `number`; one
> site's budget is not another's type.

Verified — all four drift shapes from all three rounds now fail to **compile**:

| mutant | round it came from | result |
|---|---|---|
| `{ attempts: 3, attemptTimeoutMs: 60_000, … }` | 1 | ✅ TS2322 |
| `120_000` | 2 | ✅ TS2345 |
| `SERVE_PUT_TIMEOUT_MS + SERVE_MARGIN_MS` | 3 | ✅ TS2345 |
| a swapped constant | — | ✅ TS2345 |

`tsc --noEmit` already runs in CI, so this is an enforced gate rather than a discipline. **Every
compile error the brands produced was in a TEST file** — production had always passed the right
constants. The code was never wrong; only the instrument was. That is the cleanest possible evidence
that the validation shape was the defect.

**2. The SETTLE-OUTCOME SIGNAL (Claude), and this is the deeper of the two.** A High in every round:
a boolean read transport success as "settled" (r1) → the fix's `false` meant three things (r2) → the
fix's third value points at a fact that exists nowhere (r3). Each round refined *the vocabulary of
the report*. None added the missing thing, **and the missing thing is not a vocabulary**: there was
no durable record of whether a settle applied. `settle_serve_model` mutated two counters and
returned a scalar; `ledger_audit` held only the underflow exception; `serve_model_charge.release_token`
is overwritten by the next reserve, so it answers only inside the ~161s lease window.

> **Redesign: migration 0025 — make the answer durable.** `settle_serve_model` now writes a
> `ledger_audit` row (`kind = 'serve_settle'`, `note = token || ':' || released`) past the
> `not found` gate, so **a row exists if and only if that token settled.** Plus an index on
> `(kind, note)`, because an operator instruction nobody can afford to run is the same defect one
> layer out.

`indeterminate` stops being an unfalsifiable log and becomes a resolvable state — one read answers
it, and a future attempt could answer it in code instead of guessing. Mutation-verified: deleting
the insert turns the biconditional tests red.

Claude explicitly offered the narrower scoping ("escalate the signal, not the branch") **and argued
against its own recommendation** — that a reviewer proposing a narrower escalation than the rule
specifies is doing what the rule exists to prevent. I took both redesigns rather than choosing, since
they are orthogonal and each was independently justified by a confirmed High. The bounding
mechanism's constants, boundaries and lease floor come out unchanged, which is what both reviewers
predicted a design pass would conclude.

## What did NOT change, and why that matters

**The bounding mechanism has never produced a finding** — not in three rounds, across three
reviewers and ~25 mutations. The static sum, the required-positional boundaries, the migration floor
and the live CHECK absorbed everything aimed at them. Every High in this review was about an
*instrument* or a *signal*, never about the bounding design itself. Recorded because a review trail
this long could otherwise read as "the branch was a mess".

## Gate status entering round 4

`tsc --noEmit` clean · unit **263 suites / 2656 tests** · full integration **67 suites / 487 tests,
green twice back-to-back after a `db reset`** · migrations 0024 and 0025 both verified to apply from
scratch · `check-docs.py` OK · every round-3 fix mutation-checked.

**Round 4 is required**: two redesigns are new, unreviewed design, and this project's own rule is
that a redesign must be re-reviewed before it ships.
