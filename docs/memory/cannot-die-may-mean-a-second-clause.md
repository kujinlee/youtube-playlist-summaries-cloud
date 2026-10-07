---
name: cannot-die-may-mean-a-second-clause
description: "A severance that stays green may mean a SECOND guard answers the same question, not that the clause is dead — and deleting on that reading has been reversed twice"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 94fc1f20-5834-44e2-816f-8cb71c0ca573
  modified: 2026-10-04T16:58:55.748Z
---

**"The mutation could not die" is not the same claim as "the clause does nothing."** It can equally
mean a *second* clause already answers the same question, so severing either leaves the other
giving the same answer and **neither can be killed**. A case written for one then passes against
both, which looks like coverage and is not.

⛔ **I have deleted clauses on the wrong reading TWICE IN TWO COMMITS (2026-10-03/04, `d2-main-drivable`),
and both times the NEXT review refuted it with one measurement.** Both of my written justifications
were locally true and about the wrong thing:

- *"a lambda's parameters are `ast.arg`, not `ast.Name`, so they never enter `names`"* — true of the
  **parameter**; a **reference to it in the body** is an `ast.Name`. `(lambda x: x)(saved)` beside a
  local `x` broke it.
- *"the rebind route only ever considers names in `world`"* — conflated **two different sets**.
  `classify` intersects with `world_names()` (assignments + imports + defs); the callee was handed
  `guard_world_globals()` (assignments only). **535 of 811 names across 37 guards sat in that gap.**

**Why:** a severance measures *today's reachability*, not the clause's meaning. Masking makes a live
clause look dead; a narrow corpus makes a reachable clause look unreachable. **Four masking pairs**
turned up in one file.

**How to apply:** before deleting a clause whose severance stayed green, do two things —
(1) **construct an input whose verdict changes**, and if you cannot, say so as the evidence rather
than asserting deadness; (2) **ask what ELSE answers this question** and check whether the two
sites receive the *same arguments* — a divergence in what is passed is the tell. If a pair is
found, delete the **unreachable** half; that is what makes the reachable half falsifiable.
See [[a-test-that-cannot-fail]], [[fixing-a-premise-is-not-covering-the-branch]],
[[a-second-implementation-of-one-rule-drifts]].
