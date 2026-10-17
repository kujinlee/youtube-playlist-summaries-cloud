# marketplace-inventory — round 3, both halves folded, and the provenance moved out of the spec

**Round 3 is the first round whose two halves found different KINDS of defect.** Codex attacked the
spec's claims about the world and found a measured result that never happened. The Claude half
attacked the guard built in round 2 and found that its central behaviour was unfalsifiable, that it
denied a fail-open it had, and that four requirements were stated in one section and produced by
none.

| Half | Findings | Verdict |
|---|---|---|
| CODEX | 2 Blocking · 4 High · 6 Medium | NOT CONVERGED |
| CLAUDE | 1 Blocking · 4 High · 9 Medium · 3 Low | NOT CONVERGED |

Both halves are filed under `docs/reviews/{codex,claude}/marketplace-inventory-r3-*.md`, and
`check-review-rounds.py` reports **0 silent gaps** for the round.

⛔ **THE CLAUDE HALF RE-MEASURED BOTH OF CODEX'S BLOCKINGS FROM SCRATCH AND BOTH REPRODUCED** — 4 of
4 invocations exiting 2 in the two third-party repositories, and the three-stage arithmetic coming
out 3,599 / 3,737 / 6,525 with ratio 1.8130 and cross-set 3.0500. That is the first time in this
branch's history that one half has independently confirmed the other's measurements rather than
finding them wrong, and it is the reason both corrections were kept as written.

---

## Why this document now holds the spec's §9b and §9c

**r3 CLAUDE answered the readability question with a measurement rather than an impression:** over
1,059 lines, 67 round-citations on 56 lines, 20 `⟳`, 55 `⛔`, 55 `⚠`, 36 `⭐` — **166 lines, about
one in six, opening with an emphasis glyph.** Its verdict was that the corrections have *not* become
the document and that nothing load-bearing should be cut, but that the spec reads in two registers
at once and **the second is addressed to reviewers rather than to the owner.**

So the two sections below moved here, verbatim. They are provenance — what the self-review caught,
and what round 1 found — which a reviewer wants and an approver does not need in the document they
are approving. ⚠ **Nothing was deleted and nothing was summarised**; the spec carries a pointer to
this file at the place they used to sit.

⛔ **WHAT WAS DELIBERATELY NOT DONE, AND WHY.** The same finding recommended a second change —
moving the per-round attributions (*"(r2 CLAUDE H5, High, INTRODUCED BY ROUND 2'S FIX)"*) out of the
reading line into footnote form. That is **67 citations across a guarded surface**:
`check-doc-citations.py` compares citation strings, and `check-claim-propagation.py`'s registry
matches phrases inside this document. A sweep of that size during an unconverged review is how a
branch loses its subject. It is filed instead, for the owner to approve, because it changes what
they read rather than what is true.

---

## 9b. What the spec self-review caught in this document

Recorded rather than silently fixed, because this spec argues for derived numbers and was itself
written with an invented one.

- **"~13 components" was invented.** The derived figure is **24** (17 + 3 + 4). Nothing depended on
  13; that is the point — a number with no provenance passed straight into a design document whose
  §8 lists exactly this drift as a risk.
- **"the strongest candidate" was ambiguous** in D4 while §6 named the comprehensibility suite
  explicitly. D4 now names it too.

## 9c. What round 1 caught — dual adversarial review, 2026-10-16

Both halves returned **NOT CONVERGED**: Codex 4 Blocking / 6 High / 1 Medium, Claude 3 Blocking /
6 High / 6 Medium / 2 Low. Full documents:
`docs/reviews/codex/marketplace-inventory-r1-codex.md`,
`docs/reviews/claude/marketplace-inventory-r1-claude.md`.

⭐ **The four Blocking defects, and what each one was really about:**

1. **The component list omitted the mechanism the evidence endorses.** `scripts/recall-llm.py`,
   2,550 lines, on `master` — absent, while the lexical matcher the same paragraph rejects was the
   only thing listed. §3's instruction was unexecutable against §3's own scope.
2. **`CANNOT RUN` guarded the wrong failure.** It fires when a set cannot be resolved; the
   dangerous case is a set that resolves **successfully and incompletely**. Reproduced against this
   spec's own stated paths: a walk over `.claude/skills/shared/` finds nothing, because the entries
   are git symlinks and `grep -r` does not follow them — a clean score over an empty set.
3. **The experiment could pass by inheriting the author's machine.** `~/explainers/` is a symlink
   into this repository, so the composer finds a usable page that a stranger has none of.
4. **The pass condition could not fail in the way that matters.** All nine ground-truth items can
   return nothing, a page still composes and serves, Ask still works — a hollow page scoring `SHIP`.

⚠ **AND ROUND 1 REFUTED THIS DOCUMENT'S OWN HEADLINE FINDING**, which is the most useful thing it
did. The *"3x undercount"* was a cross-corpus comparison; same-set the figure was **accurate within
3.7% when written** and is **1.81x** low today. So the lesson drawn from it — *written from recall* —
was wrong, and §8's risk row was mitigating a failure this case is not an instance of. The real
failure is **a dated count decaying**. See §3 and §8.

⚠ **Two numbers in the walkthrough page were produced by nothing** and are corrected with the spec:
`346s` for the sharding result (`ci.yml` records `1758s → 353s`, measured on one machine
2026-10-05; `346` appears nowhere in the repo, and a prior review half had already filed it as a
defect), and *"15 document guards"*, a denominator that exists nowhere.

⟳ **AND THE ONE FINDING THIS SECTION SAID WAS NOT FOLDED HAS SINCE BEEN DECIDED — CORRECTED
2026-10-16 BY ROUND 3's CLAUDE HALF (H1).** This paragraph read: *"whether `SHIP` may be recorded
without demonstrated C4 evidence … is the owner's decision and is stated as an open question in §4."*

⛔ **BOTH HALVES WERE WRONG BY THE TIME ANYONE COULD READ THEM.** There was no open question in §4 —
the phrase appeared **once in this document, in this paragraph, pointing at nothing** — and the
decision had already been taken: **D5 (§4b) permits `SHIP` + `argued`**, where `argued` is *C1–C3
plus reasoning, no experiment reached it*, which is exactly *`SHIP` without demonstrated C4
evidence*. §4b's own header says *settled by the owner; do not re-open*.

⚠ **AND THE PAGE ALREADY SAID SO** — *"you have since decided it, as D5 above"* — so the page was
folded and this section was not. **That is this branch's measured failure mechanism appearing inside
the very round that built a guard for it**, and the guard was green over the disagreement because no
token was registered for this claim. It is now registered (`d5-ship-plus-argued`).

⛔ **WHY IT MATTERED MORE THAN A STALE SENTENCE:** this was the last substantive paragraph before
§10, so a reader walking the spec to approve it was told at the very end that a promise-changing
decision still awaited them — and would either hunt for something that does not exist or re-open a
decision of record.
