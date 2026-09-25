# Round 3 — `velocity-doc-consistency` — coordinator

```yaml
round: 3
fixes_nontrivial: true
subject: velocity-doc-consistency
halves:
  claude: ran
  codex: "GAP: alternation — Codex took r2, so r3 is the Claude half"
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: true, component: round-attribution, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: self-counts, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: false, component: exhaustiveness-claim, disposition: fixed}
```

REVIEW GAP: codex — alternation, per `review-method.md` -> Round topology step 4: Codex took r2, so r3 is the Claude half. Not a failure to run.

## ⭐ Both questions the round was convened for came back CLEAN — and it still found a High

The reviewer opened by saying it expected to say CONVERGED. That makes the finding it did return
worth more, not less.

**Q: is the tally-vs-finding distinction sound?** — *substance yes, label no*, and **the label is
what got written down.** `:310` counts a subset of §3's signals and goes stale if §3 gains one, so it
is a tally too; and *tally vs finding* **cannot be applied by a reader**, because both survivors are
findings *about* the document. ⭐ **It supplied the better rule: RECOVERABILITY — is the number named
elsewhere?** `development-velocity.md:58-59` names the two mechanisable signals by name, so a reader
resolves `:310` in one jump and an editor who breaks it must pass through the sentence that repairs
it. *"All five were settled"* was recoverable from nothing. **Same verdict on both, by a test a
reader can run.** Adopted.

**Q: is withdrawing the exhaustiveness claim a fix or a self-authored retreat?** — *a fix*, and it
said it tried to break that. The terminating evidence is **not** self-authored:
`process-checklists.md:394` records the syntactic hunt rejected at three scopes on 2026-08-27, and
the document reaches the same verdict independently. The claim asserts **less**, not more, and
nothing governing moved.

## H1 — a new un-derived count of our own history, inside the fix for un-derived counts

*"The fourth pattern today"* is **the sixth**. `velocity-177-r4-coordinator.md:25-27` enumerates five
predecessors individually — bolded digits, any digits, number-words, `file:line` locators,
doc-relative positions — and commit `2d4d874c`'s own subject says *"the fifth fix"*.

⭐ **THE TELL, and it is the sharpest observation of the branch: the r1 and r2 coordinator documents,
written in one fold, both reached "fourth" from DIFFERENT predecessor lists** — one omitting
locators, the other merging them into number-words. **Two roads to one number from incompatible
premises is not corroboration; it is the signature of a count nobody derived.**

⛔ **Fixed by stating no total anywhere** outside the append-only store, pointing instead at the
document that enumerates them — recoverable in one jump, which is r3's own rule applied to r3's own
finding. The two dashboard sites stand and are corrected by a new entry.

⚠ **Graded High deliberately, and the reviewer said why**: r1 graded this identical class High twice,
and the error runs in the *safe* direction (the argument is stronger than stated, not weaker).
**Grading it down for being conveniently wrong would be exactly the self-authored retreat this branch
is otherwise refusing.**

## M1 — rule 2 failed again, in the same sentence it had just repaired

`:263` said *"the other three"* over §9's **five** questions, and the arithmetic closes under no
reading — *"the scope"* is not one of the five. **The r2 fold repaired the previous clause of that
same sentence and left this one.** That is *fix the sentence in place* failing at the granularity of
a clause.

## L1 — a standing exhaustiveness claim nobody revisited

`:25` claimed *"Every number below was measured in that session"* — falsified repeatedly by this
branch and never revisited. Narrowed.

## ⚠ What r3 offered and did not file — recorded so it is not lost

*No search* can find every tally, but a **shape** invariant can prevent them
(`velocity-177-r4-coordinator.md:32-37`). It correctly does **not** apply to a rationale document
whose purpose is to carry measurements — but this branch never says why, and that silence is the gap
between the two documents' treatment of the same class.
