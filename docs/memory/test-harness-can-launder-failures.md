---
name: test-harness-can-launder-failures
description: "FIRES-WHEN: writing a negative test that catches an error — A negative test that catches \\\"any error\\\" passes on typos, so the instrument itself must assert WHICH error — measured on this project, it hid two Blocking findings for a full review round"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 18820d36-e0cd-46c7-945b-e5f3417ebb5f
  modified: 2026-08-06T23:41:17.919Z
---

A `assert_raises`-style helper that catches **any** error reports a pass when the fixture merely fails
to parse. Measured 2026-08-06 on the stable-blob-addressing schema: six negatives were rejected by
`[42601] INSERT has more target columns than expressions` — a batch edit added a column name and no
value — while the suite printed `ok (rejected)` and exited 0. Two Blocking-severity guards shipped
**unverified**, and the coordinator reported them as mutation-checked.

**Why:** this is the one defect class that more testing cannot find, because every test runs through
the broken instrument. It is strictly worse than a fixture that violates two guards (which at least
tests something) and it looks identical in the output.

**How to apply:** a negative test must assert *which* failure it got — SQLSTATE plus constraint name
in Postgres, error type plus message in any language — and re-raise anything else. Two corollaries
measured the same day: an assertion that reads a fixture table **after** `set local role` fails on the
fixture, never reaching what it names; and a "sees 0 rows" check can never detect a **removed** RLS
policy, because removing one from a force-RLS table makes it more restrictive — only an owner-side
positive catches that.

Related: [[dual-review-what-it-catches]] — both are about not trusting a green verdict
without asking what it would have had to check.
