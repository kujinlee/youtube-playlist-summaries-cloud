---
name: what-mutation-testing-proves
description: "FIRES-WHEN: about to cite mutation results as proof of coverage — Mutation testing proves a rule is load-bearing, never that the set is complete — and a MUTATION can be masked exactly like a fixture, so the harness needs a verdict per mechanism"
metadata:
  type: feedback
---

> Merged 2 memories, bodies kept VERBATIM. Former names (still referenced by other memories): `a-rule-can-be-overturned-silently`, `mutation-harness-needs-a-verdict-per-mechanism`

## a rule can be overturned silently

**Measured 2026-08-07, round 7 of the blob-addressing review (fixes merged PR #56, `aad6aee`).**

On 2026-08-07 the user declined a reviewer's proposed `lease_token` veto, deciding:

> **The reservation guards SPENDING, not RECORDING. A writer that already paid always records.**

One day later, item 3 added a freeze trigger to `video_generations` for an entirely unrelated reason
(making `complete` terminal so a frozen blob address cannot point at rewritable content). Nothing in
that change mentioned the decision. It restored the rejection anyway — through the *parent* table
instead of the one the rule was written about.

Measured: a worker that merely **restarted** and forgot its own token got
`[23505] duplicate key value violates unique constraint "video_artifacts_paid_uq"`. No race, no
reclaim, live lease. The function whose own comment said it *"never refuses"* discarded paid work.

**⚠ THE OBVIOUS LESSON IS WRONG, AND THE REAL ONE IS SHARPER.** It is tempting to conclude "prose
does not survive; write a test." **A test was written, and it was mutation-checked, and it passed.**
`05_assert.sql:565` asserts the decision by name, and a mutation replacing the append with
`return 'refused';` turned it red.

It failed anyway, because **the assertion encoded the SCENARIO, not the PROMISE.** It passed a
*different* generation id from the holder's and *supplied* the span — precisely the two choices under
which a blind INSERT works (no `paid_uq` collision, no `art_dig_has_span` violation). Three other
arrivals at the same function broke the same promise with no assertion at all: same generation
(`23505`), span omitted (`23514`), generation completed by another party (`P0001`).

> **Mutation testing proves a guard is LOAD-BEARING. It does not prove the assertion set is
> COMPLETE.** It answers *"does deleting this code break a test?"*, never *"does the test cover the
> promise?"* A guard can be genuinely load-bearing for its one case while the property it claims to
> protect is violated three other ways. This is the blind spot of a project that leans on mutation
> testing as hard as this one does.

**Also correct the history, because it changes the lesson.** The `23505` shipped in `ccc7eb7` — the
commit that *implemented* the decision. So it was **under-implemented on day one**, not revoked
later. Only the `P0001` (item 3's freeze) is a later change silently overturning it. Two mechanisms,
not one.

**How to apply.** Write the assertion against the **property, quantified over the ways a caller can
reach it** — not against the scenario that prompted the decision. The prompting scenario is by
construction the case you were already thinking about, so it is the case the implementation gets
right; the decision's whole value is in the other arrivals.

The tool already exists and was simply never pointed here: `dev-process.md` requires an **Enumerated
Behaviors** table before writing tests — *for tasks*. Nobody required one for a **decision**. Build it
for the function the decision constrains (holder vs lost token × same vs different generation × args
supplied vs omitted × generation pending vs completed-by-other) and all four cells fall out
mechanically. Three were broken.

Corollary on where to look: the revocation came through a **different table on the same write path**.
Ask not only "who reads this field" (the existing rule) but **"what else is now on this path that the
decision was never re-derived against."**

See [[reservation-guards-spending-not-recording]] (the decision), [[blob-addressing-spec-state]],
and [[unsatisfiable-ordering-is-the-tell]] — round 7's other findings were the same class: fences
built for one table, never swept to the one added later.

## mutation harness needs a verdict per mechanism

**Measured 2026-08-07, item 3 of the blob-addressing review (PR #55, `1cd884a`).**

`mutate-schema.py` classified: `RED` (an assertion named it), `RED(constraint)` (a constraint caught
it), `GREEN` (survived), `INVALID` (the edit broke the SQL). Item 3's guards are **triggers**, and a
trigger's `raise exception` matches neither the assertion pattern nor the constraint pattern — so
**three working guards came back `INVALID`**.

`INVALID` means *nothing was tested*. That is indistinguishable from an untested guard, i.e. the
harness converts a catch into a miss — the **same shape as round 5's `when others`**, which converted
a failure into a pass. The docstring warns about exactly this one layer down and the harness did it
one layer up.

**Rule: a mutation harness needs one verdict per rejection MECHANISM the schema uses.** Adding
`RED(trigger)`, anchored on the schema's own `raise exception` prefixes (`video_artifacts:` /
`video_generations:`) so a genuine runtime error — a missing function, a bad cast — still classifies
as `INVALID` rather than being laundered into a pass.

**Second rule, from the same run: a mutation can be MASKED exactly like a fixture can.**
`produced_at = now()` looked like a fine mutation and was caught by the *freeze* trigger on an
unrelated complete fixture, long before the assertion it was written for ever ran — so it proved the
freeze worked and said nothing about the parameter being honoured. The sharp version drops the
parameter (`coalesce(produced_at, now())`), which leaves every complete generation untouched so only
the intended assertion can go red.

> **Round 5 H1's "every negative must violate exactly one guard" applies to MUTATIONS, not just to
> fixtures.** If a mutation is caught by something other than the guard you aimed at, you have tested
> the other thing.

Corollary that saved two of my own bad tests the same hour: pinning the expected SQLSTATE means a
double-violating negative surfaces as `expected P0001, got 23514` instead of a false GREEN. Fix the
negative anyway — needing the harness to disambiguate it is still the defect.

See [[test-harness-can-launder-failures]], [[dual-review-what-it-catches]],
[[blob-addressing-spec-state]].

