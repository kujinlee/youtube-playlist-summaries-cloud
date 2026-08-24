# Post-Plan Gate — adversarial review of the slice A implementation plan (round 1)

You are an adversarial reviewer. Find defects. **Read the actual files.**

## What to review

`docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md` — 12 tasks, 86 steps.
Spec: `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md`.

This is the **Post-Plan Gate** (`docs/dev-process.md` Phase 2). Nothing has been implemented. The
question is whether an engineer with **zero context for this codebase** could execute this plan and
produce correct, well-tested code — and whether following it exactly could ship a defect.

## Context you need

The spec took **five** adversarial rounds. Rounds 4 and 5 each found Blockings **in the previous
round's own fixes**. The dominant defect shape, four times over, was *a claim true about the object
it names and silent about the layer that overrides it* — a function whose table has a trigger, a
predicate that ignores a field its record carries, tests that cover a call but not the write it
performs. **Citation-checking never caught any of them.** Assume that shape is present in the plan
too, and hunt it: for each assertion a step makes about existing code, ask **"what else touches
this?"**

## Attack these hardest

**1. The ordering chain `T3 → T10 → T4`.** T4 arms a mechanism; T3 and T10 make it safe. Verify from
the code that both couplings are real, that the stated costs are right (~6¢ per bare press; a
UTC-day-long 503), and — the part I care most about — **that the chain is COMPLETE.** Is there a
fourth task that must also precede T4, or any other pair with this shape that nobody noticed? A
missing edge here ships a live defect.

**2. Task 9's migration — the money path.** `spend_ledger` is **global, one row per UTC day**
(`0011:11`). Confirm that the clamp, the loud rejection, the `revoke … from public`, and the ceiling's
mutation-check together make it impossible for one authenticated account to exhaust the global daily
cap. **Try to find the input that gets past them.** Also judge: is `correction_max_cents` default 25
sound, and is the cap-soundness test derived correctly from the TS constants?

**3. Every step that claims a test will fail for a stated reason.** A step saying *"Expected: FAIL
with X"* is a prediction about a codebase you can read. Check the ones that matter. A TDD step whose
red phase is wrong teaches the implementer to ignore the red phase.

**4. Interfaces between tasks.** An implementer sees only their own task. Do the signatures in each
task's **Produces** block match what later tasks **Consume**, exactly — names, types, nullability?
`fixSummary` returning `{ text, usage }` with `usage: GeminiUsage | null` crosses several tasks.

**5. The mutation-checks.** Several steps require a mutation to turn a test red. For each: would the
stated mutation *actually* be caught, and does the test reach the branch at all? This repo has
measured a guard whose operands came from one stale closure — it could never fire, and a surviving
mutation is indistinguishable from "does nothing".

**6. What the plan does NOT cover.** There is an "Out of the 12 — must not be forgotten" section with
four items. Is that list complete against the spec? Name anything the spec requires that no task
implements and that section does not list.

## Also assess

- Placeholders: "TBD", "add appropriate error handling", "similar to Task N", or a step that says what
  to do without showing how. The plan claims a clean scan — verify.
- Types or functions referenced by a task and defined by none.
- Whether any task is too large to review as one unit, or too small to be worth its own gate.
- Test *design*: do the negative tests assert **which** error? Do any assert on a mechanism rather
  than a consumer?

## Output

**Blocking / High / Medium / Low**, each with file:line, the concrete failure scenario, and a
suggested fix. Mark anything you could not run **NOT VERIFIED**. End with `CONVERGED` or
`NOT CONVERGED`.

If the plan is executable and the residue is genuinely implementation detail, **say so plainly** —
this gate exists to catch defects before code is written, not to produce a sixth round of findings on
a design that has already had five.
