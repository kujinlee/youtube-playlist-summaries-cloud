---
name: a-gate-can-be-blocked-on-a-decision-not-work
description: "FIRES-WHEN: estimating a gate or milestone that is not moving — M1.4's last two items looked like engineering and were not — B4 needed a product decision and then took an hour; the \\\"expensive prod-risky experiment\\\" it described was a data fixture"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 44563227-eadb-43b6-9b7a-a92b0c8e93e9
  modified: 2026-08-12T01:02:16.696Z
---

M1.4 sat on two "remaining checks" for weeks. Neither was engineering work.

**B4** read as *"deploy an image whose `GENERATOR_VERSION` differs from the local checkout … check
whether a rendering share starts returning 503."* That framing made it look expensive (a deploy) and
prod-risky (a knowingly-skewed live image). Both were false:

1. **It was blocked on a product decision**, not on work — *tolerate / refuse / heal* are three
   coherent answers and the same observation is a pass under one and a failure under another. Once the
   user said "tolerate" (2026-08-11), implementation was one call site plus tests.
2. **The experiment was a data fixture.** Version skew is a property of the **stored envelope**, not
   the running image. Writing an envelope with an old `generatorVersion` reproduces it exactly. No
   deploy, no prod risk.

**Why:** an item phrased as an experiment ("check whether X happens") hides which of those two things
it is. Asking *"what observation would make this FAIL?"* separates them immediately — a decision has no
answer, so it surfaces as "a decision is missing", which is actionable. See
[[a-test-that-cannot-fail]], the same instrument finding the same class.

**How to apply:** when an item looks costly, ask what *state* the expensive step is really producing
and whether it can be written directly. And before scheduling work on any "check whether" item, decide
whether it is blocked on a fact or on a choice — the second one is the user's, costs minutes, and
unblocks the first.

Corollary measured the same day: implementing B4 **overturned a specified, tested rule** (spec D3 and
behaviour row B8 of the 1F-b design both mandated 503 on skew). A decision that reverses a spec must
rewrite it in place, not quietly contradict it — [[what-mutation-testing-proves]].
