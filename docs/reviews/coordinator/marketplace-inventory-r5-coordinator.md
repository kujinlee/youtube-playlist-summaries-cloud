# Round 5 — coordinator fold

**Subject:** `marketplace-inventory` (PR #376), commits `2e79f464..b0b425d5` — the implementation of
architecture-review candidate 1 (ADR-0015) plus the four commits no round had seen.

**Halves:** Codex `docs/reviews/codex/marketplace-inventory-r5-codex.md` (`gate_ran: true`, model
`gpt-6.1-sol`). Claude half dispatched AFTER this fold, per `review-method.md`'s alternating rule
for rounds 2+ — the point of alternating is that the second half reviews the FIXES, and this round
is the case for it: the Codex half refuted a closure I had already published.

**Verdict: NOT CONVERGED.** 2 High, 2 Medium, 1 Low; all five folded below. No Blocking.

---

## ⛔ The finding that matters most, because it is about my verification and not the code

**r5 CODEX H1 and H2 — two of backlog #297's three drifts were STILL LIVE in both pages when I
closed the row and told the owner all three were fixed.**

The mechanism, which is more useful than the fix:

> I verified with a regex built on the character class `[^<>]`. **That class cannot cross a tag
> boundary.** The live assertion is `graded against <strong>D9</strong>`, so my own output
> truncated immediately before the `D9`; I read *graded against* with nothing after it and
> concluded it was an unrelated passage.

⭐ **That is exactly the defect class the prose matcher I had just DELETED existed to catch** — its
own r3 CODEX H4 reads *"inline markup HIDES a registered claim: `<em>support verdict</em>` scored
(0, 0) — identical to a reader, invisible to the guard."* I reproduced it by hand, in the same
session, while verifying a fix about that class. The verification that works **strips tags first,
then matches**, and every check in this fold was redone that way.

⚠ **H2 was worse than a miss.** My edit landed on a *different* passage — the honest-cost note —
leaving `Its falsifier, stated now` and its retired, unobservable condition intact. The citation I
added also pointed at **§4c**, which is D6 and harvest; D5's checkable rule is **§4b**. So the one
edit I made in the name of "cite, don't restate" cited the wrong section.

**Folded:** the criteria table no longer grades C4 by D9 and says the spec withdraws that predicate;
the retired falsifier is replaced by a §4b citation that names what was withdrawn and why it could
never fire; the section reference is corrected. Verified on the **composed** page with tags stripped.

## r5 CODEX M3 — three surviving `_Carriers` branches no case pinned

The reviewer applied three independent mutations and got **41/41 green** on each: accumulating
`data` instead of `data.strip()`; reducing `VOID` to `{"img"}`; clearing the stack on an unmatched
end tag. These are gaps **I introduced** by reducing `_Blocks` to `_Carriers` — surviving branches
left uncovered, which is the shape ADR-0014 exists for.

**Folded:** 8 new cases (49 total) and 3 new mutations (18 for this file). ⭐ The void case is a
**loop over the vocabulary**, not one member, because the deleted matcher made exactly that mistake
three times — each fix covering the spelling its finding named.

## r5 CODEX M4 — a memory entry's "unmutatable" claim, refuted

`a-harness-cannot-read-a-cause-from-a-childs-text.md` called the derived-page expansion
*"unmutatable"*. **False, and the repository's own manifest proves it:** a *substitution* —
`wanted |= {d["page"] for d in DERIVED}` — fails cleanly and attributed, and that entry is live and
killed. The claim was reached from **one mutation shape** (deletion, which crashes).

**Folded:** the claim is withdrawn in place with its refutation, and the sharper lesson kept —
*"unmutatable" is a claim about EVERY mutation of a line, and deletion is the crudest shape; weaken
before concluding impossibility.*

## r5 CODEX Low — the retirement count did not close

I wrote **19 retired**; `32 − 19` is 13, not 15. The real figure is **17**, and 19 was the
intermediate value from the first pass before two entries were restored as retargets.

**Folded:** corrected at both sites and now **derived** by diffing the manifest against `8a583f7c^`
rather than retyped. The declared-sum comment now shows its arithmetic (`1489 − 17 + 3 + 1 = 1476`)
instead of asserting a net figure, because a sum whose derivation is hidden is the same defect.

## Also folded — found by CI, not by either half

**`CONTEXT.md` was declared a citing site, and `HARNESS_TREE` stages no repo-root files.** So
`audit()` reported *"declared a citing site but does not exist"* inside the staged tree, reddening
this guard's own control: **6 of 8 mutation shards reported NOT MEASURED**. ⚠ My local run could not
see it because I had scoped the harness to **one** manifest, so this guard's suite never ran — the
scoping that made the run fast is what hid the failure. The tell was in the data: no other `cites`
entry is a root file. Fixed, with a case asserting the invariant over the **live** table and a
mutation that re-adds a root file.

---

## Measured state after the fold

| check | result |
|---|---|
| `check-claim-propagation --self-test` | 49/49 |
| `check-canonical-source --self-test` | 28/28 |
| `check-plan-code --self-test` | 178/178 |
| scoped `--mutate .` over BOTH changed manifests | **25 mutations, 25 killed, 25 attributed, 0 survivors**, controls and re-controls green |
| the two Highs, on the composed page, tags stripped | `graded against D9` absent; retired falsifier absent |
| document guards (the `check-*` list from `ci.yml`) | re-run after the fold |

## Thrashing or prose floor?

**Codex says continued thrashing with new ground, and I agree — with one distinction that matters.**

Its two Highs are **not** caused by the architecture review's redesign; they are the *original*
defects the review filed as evidence, which my corrective pass **claimed to fix and did not**. That
is not the thrashing shape (*a fix creating the next finding*) — it is a **false closure**, which is
worse in one specific way: thrashing leaves a visible open finding, a false closure leaves a green
row over a live defect, and the owner had already been told.

M3 is genuinely new ground (coverage of code that did not exist before this branch). M4 belongs to
an earlier unreviewed commit. The Low is an arithmetic error introduced by the same corrective pass
— that one *is* fix-induced.

⛔ **So the architecture review is NOT re-armed.** Its own remedy is landed and is not what produced
these; what produced them is one verification method I used twice and have now replaced. The
standing question for round 6 is whether the Claude half, reviewing these fixes, finds a third
instance of the same false-closure shape — and if it does, the subject is my verification, not the
design.
