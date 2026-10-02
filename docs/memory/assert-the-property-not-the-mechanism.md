---
name: assert-the-property-not-the-mechanism
description: "FIRES-WHEN: writing the test that guards a fix you just made — A guard that asserts the FIX is present, rather than the PROPERTY it delivers, passes on the exact defect it was written for — measured 3 blind spots in one 2-line guard"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 44b2b306-b802-467e-8eb8-4d81cc0ddd80
  modified: 2026-09-08T04:43:57.003Z
---

**A guard written from the SYMPTOM asserts that the fix is present. A guard written from the
PROPERTY asserts the thing you actually care about. The first one passes on the defect it exists
to catch.**

Measured 2026-08-29 on PR #175 (`scripts/gen-dashboard.py`). The guard was
`("a{color:var(--link)}" in ht, ht.count("--link:")) == (True, 2)` — falsifiable, mutation-tested
four ways by its author, green. It had **three independent blind spots**:

- **value** — `--link:#8cbde0` → `#0000EE` restores the original 1.90:1 defect. SURVIVED 105/105.
- **scheme** — the count is a TOTAL. Put both definitions in `:root`, delete the dark one. SURVIVED.
- **`a:hover`** — never mentioned, never covered.

And it *caught* `a{color` → `a { color`, which breaks nothing. **Silent on the defect, loud on a
reformat.** Replacing it with "compute the WCAG ratio for every colour on every surface in both
schemes" closed all three with one assertion — and covers colours nobody has chosen yet.

**The tell:** the guard names the same tokens the fix introduced. If you can read the fix off the
assertion, it probably only defends the deletion of that fix. Ask *"what property was violated?"*
and assert that instead.

Two corollaries, both measured the same day:

- **A substring test is not a rule test.** `"a{color:var(--structural)}" in page` is satisfied by
  `.qabody a{color:var(--structural)}`, so the guard passed with the unscoped rule deleted — the
  precise defect. Anchor it (`re.search(r"^a\{…", re.M)`) and pin the near-miss as its own case.
  The same hazard bit a mutation script minutes later (`assert count == 1` refused at 4 matches) —
  see [[a-positional-read-needs-a-verified-shape]].
- **A guard returning a LIST must RAISE when it cannot parse its subject**, or "no failures" is
  indistinguishable from "never ran". Give the instrument its own falsifier case.

## ⚠ Round 2: asserting the property is not enough if the MODEL of where it applies is wrong

Same PR, next round. The replacement guard measured a flat **cross-product** of foregrounds ×
surfaces. It missed `.num a{color:inherit}` — 70 links taking their colour from the parent — so a
mutation to **1.37:1 SURVIVED at 64/64**. And it would have over-asserted: `--ink-3` is sub-AA on
two surfaces it never touches, so the reviewer's proposed fix (add it to the foreground list)
**reddens a correct page**. *A cross-product asserts pairs that never co-occur and misses pairs
that do.* It passed only because one colour cleared AA everywhere — **the model was wrong and the
data hid it**. Fix: explicit pairs, plus a drift check that fails when the page grows a link rule
the model has not heard of.

**Then the fix for THAT was also insufficient.** Modelling the link as `"inherit"` left the parent
unchecked, so repointing `.num`'s colour survived a second time at 69/69. **Found only by re-running
the reviewer's exact mutation against the fix instead of assuming it closed.** An inherited value
must be pinned at its SOURCE.

**Rule: when a reviewer hands you a mutation, re-run THAT mutation against your fix.** Do not
substitute your own variant — mine (change the variable's value) passed while theirs (repoint the
variable) still survived. Four instances of this defect shape in one small branch; two of them
introduced by the fix for an earlier one.

Related: [[after-fixing-search-for-the-class]] (the same PR's fix was instance-not-class — the
sibling generator had the defect worse), [[a-test-that-cannot-fail]],
[[a-convention-catches-what-you-read]], [[dual-review-what-it-catches]] (round 2's
reviewer was right about the defect and wrong about the fix — adjudicate by measuring).

## ⚠ Round 3, SAME DAY: I rebuilt this defect inside the guard written to prevent it

Backlog #70 (PR #176). To stop a mutation manifest silently shrinking, I added
`EXPECTED_MUTATIONS` — a per-file **count**. Codex reproduced the hole in one move: replace an entry
with a duplicate of another, count unchanged at 32, coverage narrowed, **still green**.

Counting is a proxy for *how many*; the property is *which ones*. Hours after writing this memo, in
the guard whose entire purpose was this class. Fixed by rejecting duplicate names and anchors —
identity, not cardinality.

**The general form: when you catch yourself asserting a NUMBER, ask what the number stands in for,
and whether you can assert that instead.** Count, presence, existence, "the rule is there" — all
proxies. Ratio, identity, the measured property — the thing itself.

## ⚠ Round 4, 2026-09-07: the substring was tested against a REGEX's own text

`scripts/check-catalog-coverage.py` (PR #256). The ACL rule
`^(relacl|proacl|attacl|typacl)$` is written **twice**: once in `EXCLUDED`, once in
`MOVED_COVERAGE`, which claims those columns are covered by another instrument instead. Nothing
checked the two copies agree. The case that looked like it did:

```python
check("the ACL row is the one that claims its facts moved",
      any(r"relacl" in pat for pat, _, _ in MOVED_COVERAGE), True)
```

**A substring test on a PATTERN is even weaker than one on a page**, because a regex is a *set* and
`in` cannot see the set shrink. Narrow either copy and those six letters still appear, so a column
ends up excluded here and claimed by nobody there — silently. Replaced with the agreement
invariant: every `MOVED_COVERAGE` pattern must be one `EXCLUDED` actually uses. Fails in **both**
directions of drift, which the substring test could not do in either.

Found the same way as everything above — by asking *what observation would make this case FAIL?* —
not by the mutation tally. See [[a-second-implementation-of-one-rule-drifts]] and
[[one-rule-one-place]]: two copies of one rule need an executable agreement check, or
the older copy is decoration.

Also from that branch: **executing a plan is a strictly stronger instrument than reading one.** Two
reviewers read it and cleared four defects that appeared the moment it ran — including a
substitution table that read 1:1 where two entries occurred twice, and an insertion point that put
new test cases *after* the line printing the total, so the suite printed a stale count while the
drift check that exists to catch exactly that read the counter later and passed.
