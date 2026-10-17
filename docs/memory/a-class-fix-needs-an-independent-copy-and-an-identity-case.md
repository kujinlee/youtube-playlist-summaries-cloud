---
name: a-class-fix-needs-an-independent-copy-and-an-identity-case
description: "FIRES-WHEN: a review says my case covers only the member it names and I am about to generalise it by LOOPING OVER THE SET the code uses — ⛔ that is UNSOUND: the fixture then derives from its own subject, so shrinking the set SHRINKS THE CASE LIST and nothing reddens (measured 57/57 -> 56/56 passed, zero failures). Write an INDEPENDENT literal plus an IDENTITY case asserting the two agree. Also fires when adding a mutation whose anchor another entry already uses"
metadata:
  node_type: memory
  type: project
---

**Generalising a case by deriving its inputs from the code under test produces a case that cannot
fail.** The obvious class fix is the wrong one, and it fails silently in the direction of good news.

**MEASURED 2026-10-17, r5 CLAUDE H1, `check-claim-propagation.py`.** A case pinned one void element;
the fix was supposed to pin all fourteen. Three versions:

| version | drop `area` from `VOID` | verdict |
|---|---|---|
| hardcoded 6-tuple (what I wrote, with a comment claiming it covered the set) | **49/49 passed** | 8 of 14 members unpinned |
| `for _v in _Carriers.VOID:` — **the obvious fix** | **56/56 passed** (was 57/57) | ⛔ the case COUNT fell; nothing failed |
| independent literal + identity case | **2 of 58 FAILED** | ⭐ two witnesses |

⭐ **THE SOUND SHAPE, and it is the one place a second copy is correct:**

```python
_VOID_EXPECTED = "area base br col embed hr img input link meta param source track wbr".split()
case("the VOID vocabulary is exactly the 14 HTML void elements",
     sorted(_Carriers.VOID), sorted(_VOID_EXPECTED))   # ← the identity case
for _v in _VOID_EXPECTED:                              # ← driven by the INDEPENDENT copy
    case(f"a <{_v}> carrier captures nothing that follows it", ...)
```

A divergence then reddens **twice**: the identity case says *the vocabulary changed*, the member case
says *the behaviour changed*. Deriving the loop gives neither.

⚠ **This is a genuine EXCEPTION to [[a-second-implementation-of-one-rule-drifts]]**, which is this
repository's most-measured rule (17 instances). The reason it does not apply: the second copy is not
a second *implementation* — nothing consumes it but the identity assertion, whose only job is to fail
when the two disagree. **A duplicate guarded by an identity case is a ratchet; a duplicate with no
identity case is the 17-instance defect.** The test for which one you have: *if these two drift
apart, does something go red?*

## The shape it belongs to

Same family as [[a-case-can-pass-for-an-ambient-reason]] (the fixture supplies the value the case
asserts) and [[a-sever-substitutes-todays-value]] (the mutation substitutes today's value and the
case still passes). The distinguishing feature here is **the case list itself is the thing that
moves**, so the tally shrinks instead of a failure appearing — and a shrinking tally reads exactly
like a smaller suite, not like a regression. ⛔ **`N/N passed` is not evidence; `N` must be pinned
too**, which is what `check-selftest-counts.py` and the declared docstring count exist for.

## And two adjacent traps measured the same hour

1. ⛔ **A mutation can be UNFALSIFIABLE because the live data has no adversarial case.** I added one
   asserting a path predicate normalises; over the live table no entry used the `./x` spelling, so
   reverting the normalisation changed nothing and the mutation would have SURVIVED. The fix was to
   extract the predicate and exercise it with a fixture containing all three spellings. **Assert
   over the live table AND over input the rule must refuse — the first catches a real bad entry, the
   second catches the rule being weakened.**
2. The harness refuses a second mutation on an anchor another entry already uses — *"it measures
   nothing new"* — which is correct. **Extend the existing entry's `expect` list instead.**
