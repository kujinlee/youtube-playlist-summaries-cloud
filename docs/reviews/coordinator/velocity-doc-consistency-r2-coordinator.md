# Round 2 — `velocity-doc-consistency` — coordinator

```yaml
round: 2
fixes_nontrivial: true
subject: velocity-doc-consistency
halves:
  codex: ran
  claude: "GAP: alternation — the coordinator authored the r1 fold and r2's risk was verifying git-derived claims, which review-method.md Round topology step 4 routes to Codex"
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: true, component: exhaustiveness-claim, disposition: fixed}
```

REVIEW GAP: claude — alternation, per `review-method.md` -> Round topology step 4: the coordinator authored the r1 fold, and r2's risk was reproducing git-derived history claims, which that step routes to Codex. Not a failure to run.

## ⭐ The six git-derived claims HELD — which is what r2 existed to test

r1's two Highs were round attributions written from memory. The fold replaced them with claims
derived from git, and **those were the most likely thing to be wrong next**. Codex ran the commands
and confirmed all six: `ccc19857` is the r3 fold and **added** *"five rules, not four"* while leaving
the *"Four rules came out of this"* opener as context; r3's finding is titled *"four rules" names a
population of five* and cites the file; `e44be4b0` is the **round-1** fold and is the commit that
split the catch-all row; and `git log --all --reflog` shows **no r5/r6 commit touching the file**.

**So the third generation of the wrong-history defect did not happen.** That is the useful negative.

## H1 — but the completeness claim was wrong again, in a shape with a long history

The fold said the self-counts were *"All removed"*. Two survived:
`development-velocity.md:262` *"All five were settled"* and `:310` *"two of them look measurable"*.

⭐ **Why, measured:** the certifying sweep required a noun from
`[rules, signals, questions, sections, rows, items]`. The survivors say *five were **settled*** and
*two of **them*** — a verb and a pronoun. **Another pattern narrower than the claim it certified.**

⛔ **r3 (High): the first version of this said "fourth", and so did five other places in this same
fold.** `velocity-177-r4-coordinator.md` enumerates **five** predecessors individually, and commit
`2d4d874c`'s own subject says *"the fifth fix"* — so this one is the sixth. ⭐ **The tell that no
count was derived: two documents from this one fold reached "fourth" from different lists.** A new
un-derived count of our own history, written into the fix for un-derived counts of our own history.
**No total is stated here now** — the enumeration lives in that document and is recoverable from it.

### ⛔ The fix is not a fifth pattern — the CLAIM is withdrawn

There is no exhaustive instrument for this class: *Qualify every number in prose* records the
syntactic hunt measured and rejected at three scopes, and this branch reproduced that result twice
more. **So no document here asserts exhaustiveness for it.** Widening the pattern has now failed
at every previous attempt (`velocity-177-r4-coordinator.md`
enumerates them); withdrawing the claim cannot fail the same way, because it claims nothing a sweep
has to support.

### ⚠ And one survivor is kept deliberately — the distinction the sweep cannot make

*"two of them look measurable"* survives; *"All five were settled"* was removed.

⛔ **THE RULE JUSTIFYING THAT WAS WRONG, AND r3 SUPPLIED A BETTER ONE.** This said the survivor is a
*finding* and the removed one a *tally*. **It is not** — `:310` counts a subset of §3's signals and
goes stale if §3 gains one, so it is a tally too. Worse, *tally vs finding* **cannot be applied by a
reader**: both survivors are findings *about* the document.

⭐ **The property that actually sorts them is RECOVERABILITY — is the number named elsewhere?**
`development-velocity.md:58-59` names the two mechanisable signals **by name**, so a reader resolves
`:310` in one jump, and an editor who breaks it must pass through the sentence that fixes it.
*"All five were settled"* was recoverable from nothing. **Same verdict on both survivors, reached by
a test a reader can actually run** — which is the difference between a rule and a rationalisation
that lets a convenient number stay. A wider sweep
confirms the rest are measurements and findings — *14 minutes*, *three hand-kept path lists*, *six
functions*, *13 mutation entries*. **The defect was never numbers. It was numbers that must be
maintained to stay true**, and a pattern cannot tell those apart — which is the real reason the
instrument was always going to lose.

## Also verified rather than accepted

No section under more than one banner status (Codex read the rows rather than trusting an `rg`
count, and noted the extra `§N` hits are explanatory prose inside cells). Meaning was not lost by
removing the counts. `check-docs.py`, `check-dashboard-entry.py`, `git diff --check` all pass.
