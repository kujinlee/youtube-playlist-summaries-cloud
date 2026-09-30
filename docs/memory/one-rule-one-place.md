---
name: one-rule-one-place
description: "FIRES-WHEN: adding vocabulary or a mechanism for a concern that may already have one — One mechanism per concern: duplicate coordination vocabulary is the shadow of a duplicate protocol, and de-duplicating can DROP the half of a contract the shared signature cannot see"
metadata:
  type: feedback
---

> Merged 2 memories, bodies kept VERBATIM. Former names (still referenced by other memories): `two-mechanisms-for-one-concern`, `a-shared-function-can-hold-half-a-contract`

## two mechanisms for one concern

**Measured 2026-08-09, after twelve adversarial rounds.** Every component of the blob-addressing spec
converged and stayed converged **except one**, which produced a Blocking or High in six consecutive
rounds and was **four times broken by the previous round's own fix**.

**The cause was not a bug. It was a mechanism that should not have existed.**

`jobs` already had exclusivity + idempotency (`jobs_idem_active`, one unique partial index) and the
durable money guard (`ever_metered` + `reserved_cents`, PR #22). The artifact layer built a second
lease protocol beside it — different token, different expiry, different attempt counter, no shared
identity — and **every defect in rounds 7–12 lived in the seam between the two**.

Worse: it was solving a problem its own spec had eliminated. It was designed for the pre-ADR-0006
world where a summary had ONE MUTABLE ADDRESS and two writers collided. Stable addressing made the
producer's and replicator's writes land on **different keys by construction**, and nobody went back
to ask whether the lock was still needed.

**Three tells, all visible and all ignored:**

1. **Duplicate vocabulary** — `lease_token` and `lease_expires_at` on BOTH tables, `attempts` vs
   `lease_attempts`, `locked_by` vs `reserved_by`. *Duplicate vocabulary is the observable shadow of
   duplicate mechanism*, and it was there from the first commit.
2. **A component broken by its own fixes**, counted to eleven in the review briefs as trivia and never
   once allowed to conclude anything.
3. **The justification never mentioned the existing mechanism** — 2800 lines, zero references to
   `jobs`. *"What already serves this concern?"* was never asked.

**The generalisation, which is the reusable part:**

> **Before adding a coordination mechanism, enumerate the WRITERS and what identity each carries.**
> Five rounds of credential design failed because the design demanded ONE credential from two writer
> classes with structurally different identities — the worker has a job, a lease and a worker id;
> sync has none of them. No credential can exist. That is a broker or merge problem, and a lock will
> never converge on it.

Also: **a design that mixes coordination patterns cannot be repaired locally.** This one held
append-only-plus-merge, mutual exclusion, and an idempotency key at once, so the fence had to be
permissive (so a reclaimed writer still records) AND strict (so a stranger cannot complete). Round
8's "wrong credential" was the symptom; two philosophies on one predicate was the cause.

Full record: `docs/reviews/blob-addressing-retrospective-2026-08-09.md`.
See [[a-fence-wrong-both-ways-asks-the-wrong-credential]], [[quote-the-code-dont-characterise-it]],
[[defined-not-derived-constants]], [[blob-addressing-spec-state]].

## a shared function can hold half a contract

⭐ MEASURED 2026-09-03, `check-plan-code.py`, code review r3 (PR #214).

Round 2 found one contract implemented in two producers and did the right thing: extracted
`verdicts_are_trustworthy(m_muts, declared)`, one function, two callers. Round 3 found the contract
has **three** clauses and the extracted signature could see two. The dropped clause — *were the
controls green?* — lived in the caller as a separate statement, so extraction could not reach it.

Result: `check()` asserted `trustworthy: True` over a run whose suite was **already red before any
mutation**. A mutation editing only a COMMENT was certified `caught`. That is the precise bug the
extraction existed to eliminate, still standing in the sibling.

> **A shared function that holds PART of a contract is worse than two copies, because it LOOKS like
> the whole rule.** Two copies at least invite the question "do these agree?"

**Why:** de-duplication is judged by *"is there now one implementation?"* — which is satisfied the
moment the function exists. Nobody re-asks *"does the function express the whole rule?"* The tell is
a clause that lives at the CALL SITE as a separate statement (`ev["trustworthy"] = False` after the
fact, an early `return`, a flag set in a loop). Those are contract clauses wearing control flow.

**How to apply:** when extracting a duplicated rule, enumerate the contract's clauses FIRST, from the
callers, and check each one reaches the signature. Then ask what the function CANNOT see. If a caller
still overwrites or guards the extracted result afterwards, the extraction is incomplete — fold that
into the parameters and compute the value ONCE, at the point where every clause is known.

Related: [[one-rule-one-place]], [[a-second-implementation-of-one-rule-drifts]],
[[after-fixing-search-for-the-class]], [[assert-the-property-not-the-mechanism]].

