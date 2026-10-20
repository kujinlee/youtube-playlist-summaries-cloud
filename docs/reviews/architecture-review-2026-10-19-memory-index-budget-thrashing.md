# Architecture review — the memory-index budget guard: THRASHING, and the redesign that answers it

**Date:** 2026-10-19 · **Subject:** `scripts/check-memory-index-budget.py` and its manifest ·
**Branch:** `baseline-surveys` · **Convened by:** the arming condition in
[`docs/dev-process.md`](../dev-process.md) → *Phases*, row 6.

> **Anchor:** `review-decides-itself` (ADR-0014).

---

## Why this document exists, stated as the process requires

`dev-process.md`: *"⟳ **THE ARMING CONDITION IS THRASHING, NOT A COUNT.** It fires when **two
consecutive rounds carry findings caused by the previous round's own fix, in one component**"* — and
it obliges answering *thrashing or prose floor?* **in the round document, with per-finding
evidence.** This is that answer.

⚠ It also says *"Reaching four rounds OBLIGES ASKING, and does not fire."* Four rounds were not
reached: this is rounds 1 and 2, four halves. The condition fired on the **shape**, not the count.

## The determination: THRASHING, on one function, and it is not a prose floor

Not a prose floor — a prose floor is a document whose rounds keep producing defensible wording
changes. Every finding below is **executable**: a mutation that survived a suite, measured over a
proved-green control. The subject is code, and the same clause failed four consecutive times.

### Per-finding evidence — the chain, in order

| round · finding | what it found | what caused it |
|---|---|---|
| r1 CLAUDE **N1** | `"1 characters…" in msg` is vacuous at `L=1000`: the overage `1` is a decimal **suffix** of the total `1,001`. A mutant printing the total survived 42/42 | the original assertion |
| r2 CODEX **#1** | my repair banned the literal total `1,241`. A mutant rendering `overage + 1000` gives `1,007`, which **still ends in 7** — survived 43/43 | **N1's fix.** I had banned one VALUE, not the class |
| r2 CLAUDE **H2** | the three messages render **ten** numeric fields; **two** carried a value assertion. Seven more survivors, including the **WARNING arm's headroom** — the same defect in a different arm | **#1's fix.** Its own words: *"third consecutive round on one function"* |
| my own closed loop | the loop written to fix H2 was itself vacuous: `"80"` is a substring of `"1,080"`, `"92"` hides inside `"920"`. Two mutants survived the very case written to catch them | **H2's fix** |

That is four consecutive iterations in which **the fix became the next finding**, all inside
`budget_verdict`'s message rendering. Two consecutive is the arming threshold; this is four.

⛔ **And a second, independent instance in the same slice — a REGRESSION, not merely a gap.**
r2 CLAUDE **H3**: my symlink-resolution "fix" to `.claude/hooks/check-memory-index-budget.sh` made
behaviour **worse**. Measured over two checkouts, a hook shared by symlink reported **SILENT** on a
25,000-character over-budget index where the code it replaced had correctly fired **OVER BUDGET**.
A loud wrong answer became a quiet one. Cause: r2 CODEX finding 3's fix.

## Root cause, which is not "I was careless"

Each repair was a **narrower assertion about a string**. The suite's only way to know a number was
right was to look for that number's *rendering* inside prose — and every such test is satisfiable by
infinitely many other renderings, because any digit string is a suffix of longer ones. The defect was
therefore **structural and renewable**: each round could only ever close the one field it had just
been shown, and a new field (or arm, or arithmetic shift) re-opened the class immediately.

`a-filed-finding-s-proposed-fix-is-a-hypothesis` names the error I kept making; the standing remedy
in this repo is **refuse, don't widen — change the KIND of fix**.

## The response: a redesign, not a fifth patch

**`budget_verdict` is split into `budget_facts` (the values) and `render` (the prose).**

1. Cases assert the **facts** — a dict compared exactly — so every number is a value, not a grep.
2. **One loop** asserts every fact *reaches* the rendered message, in every state. A field added
   later is covered **by construction** rather than by remembering to write a case.
3. That loop's own vacuity is a **checked precondition**: no fact's rendering may be a substring of
   another's, and `_vacuous_pairs` has a **known positive** (`["80", "1,080"]`) so neutering it
   reddens. Without that known positive the precondition was correct and *unexercised* — measured,
   the mutation survived.
4. Membership is a **delimited** match (`(?<![\d,])…(?![\d,])`), because `414` is a substring of
   `1,414` and a bare `in` could not see it. Exercised at exactly that input.
5. The parsed-field helper is **deleted, not kept**. I had written that parsing was *"the only form
   that cannot be fooled"*; r2 CLAUDE falsified it with a float rendering. A superseded mechanism
   kept "just in case" is one more thing to be wrong.

**For the hook:** the root now comes from **the file that was edited**, walking up to the repository
containing it — because the subject is the index the tool just wrote, not the script's location.
Neither `BASH_SOURCE` nor its resolved form was ever the right answer. It also gained a `--self-test`
(12 cases) and emits `additionalContext` rather than stderr, adopting `surface-recall.sh`'s **measured**
finding that plain output at exit 0 reaches the transcript and not the model.

### Measured outcome of the redesign

Every H1/H2 mutant, re-applied over a proved-green control: **11 of 11 KILLED**, including the two
that survived the first closed loop. Manifest **22 → 28**; harness: **28 killed, 28 attributed, 0
survivors**, green control and re-control. Suite 59 cases.

## What this does NOT claim

- ⚠ **The truncation ALGORITHM is still NOT VERIFIED.** The unit is measured (characters, not bytes);
  whether the cut is a strict prefix or row-wise is not, and the docstring says so.
- ⚠ **Code points vs UTF-16 units is unresolved** — 26,930 vs 26,931, both rounding to the reported
  26.3KB, so the warning arithmetic cannot separate them. The fixture that would settle it is named.
- ⚠ **The hook is outside the mutation population**: all 1,573 manifest entries target `.py`, and no
  precedent exists for mutating a `.sh`. Its 12-case self-test is the only mechanical cover, which is
  better than its sibling `surface-recall.sh` (no self-test, no mutations) and still a gap.
- ⚠ **The hook is UNREGISTERED.** Registering it edits `.claude/settings.json`, and the finding that
  prompted it came from a review agent rather than the owner. Until then CI is the only caller, and
  CI reads the committed tree while a session reads the working tree.

## For the owner — the one judgement I did not make

The arming condition fired and I answered it with a redesign **in place of convening a wider
architecture review**, because the root cause was local to one function and the structural remedy was
identifiable without a broader survey. ⛔ **That is a judgement about scope, and it is reviewable: if
you would rather this had convened a full Phase 6 pass over the guard family, say so and it still
can.** What is not in question is the determination itself — the evidence table above is executable,
and each row was reproduced before being written down.
