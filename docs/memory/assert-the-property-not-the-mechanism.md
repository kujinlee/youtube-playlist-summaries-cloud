---
name: assert-the-property-not-the-mechanism
description: "FIRES-WHEN: writing the test that guards a fix you just made, or re-checking a fix against a reviewer's mutation — A guard that asserts the FIX is present, rather than the PROPERTY it delivers, passes on the exact defect it was written for — measured 3 blind spots in one 2-line guard"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 44b2b306-b802-467e-8eb8-4d81cc0ddd80
  modified: 2026-09-08T04:43:57.003Z
---

**RULE: assert the PROPERTY the fix delivers, not the presence of the fix.** A guard written from the
symptom passes on the defect it exists to catch.

**The tells, and what to do instead:**
- **The guard names the tokens the fix introduced.** If you can read the fix off the assertion, it only
  defends the deletion of that fix. Ask *"what property was violated?"* and assert that.
- **You are asserting a NUMBER** (count, presence, existence, "the rule is there"). Ask what it stands in
  for — identity, ratio, the measured property — and assert that.
- **A substring test is not a rule test** — on a page, `in` matches a scoped near-miss; on a REGEX, `in`
  cannot see the set shrink. Anchor it, pin the near-miss as its own case, and for two copies of one rule
  assert their AGREEMENT ([[one-rule-one-place]], [[a-second-implementation-of-one-rule-drifts]]).
- **The property's model of WHERE it applies can be wrong.** A cross-product asserts pairs that never
  co-occur and misses pairs that do — use explicit pairs plus a drift check; pin an inherited value at
  its SOURCE.
- **A guard returning a LIST must RAISE when it cannot parse its subject**, or "no failures" equals "never ran".
- **When a reviewer hands you a mutation, re-run THAT mutation against your fix** — not your own variant.
- **Executing a plan is strictly stronger than reading it.**

Found every time by asking *what observation would make this case FAIL?* — not by the mutation tally.

## History (PR #175 `gen-dashboard.py`, PR #176, PR #256)
- **r1, 2026-08-29:** `("a{color:var(--link)}" in ht, ht.count("--link:")) == (True, 2)` — mutation-tested
  four ways, green, three blind spots: value (`#0000EE` restores the 1.90:1 defect, SURVIVED 105/105),
  scheme (count is a TOTAL), `a:hover` uncovered; yet it caught a harmless reformat. Replaced with "WCAG
  ratio for every colour on every surface in both schemes". A substring guard passed with the unscoped rule
  deleted (`.qabody a{color:…}` satisfied it); see [[a-positional-read-needs-a-verified-shape]].
- **r2:** the cross-product missed `.num a{color:inherit}` (70 links) — 1.37:1 SURVIVED at 64/64; the
  reviewer's fix (add `--ink-3`) would have reddened a correct page. Modelling `inherit` then left the parent
  unchecked — survived again at 69/69, found only by re-running the reviewer's exact mutation. Four
  instances in one small branch, two introduced by a fix.
- **r3, same day, backlog #70 (PR #176):** my `EXPECTED_MUTATIONS` per-file COUNT let a duplicated entry
  keep 32 while narrowing coverage — fixed by rejecting duplicate names and anchors.
- **r4, 2026-09-07, `check-catalog-coverage.py` (PR #256):** `any(r"relacl" in pat …)` over `MOVED_COVERAGE`
  could not see either copy of the ACL regex narrow. Replaced with "every `MOVED_COVERAGE` pattern is one
  `EXCLUDED` uses" — fails in both drift directions. Same branch: two reviewers read a plan and cleared four
  defects that appeared the moment it ran.

Related: [[after-fixing-search-for-the-class]], [[a-test-that-cannot-fail]],
[[a-convention-catches-what-you-read]], [[dual-review-what-it-catches]].
