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

## H1 — but the completeness claim was wrong, for the fourth time in one shape

The fold said the self-counts were *"All removed"*. Two survived:
`development-velocity.md:262` *"All five were settled"* and `:310` *"two of them look measurable"*.

⭐ **Why, measured:** the certifying sweep required a noun from
`[rules, signals, questions, sections, rows, items]`. The survivors say *five were **settled*** and
*two of **them*** — a verb and a pronoun. **Fourth pattern today narrower than the claim it
certified**, after bolded digits, any digits, and number-words/locators.

### ⛔ The fix is not a fifth pattern — the CLAIM is withdrawn

There is no exhaustive instrument for this class: *Qualify every number in prose* records the
syntactic hunt measured and rejected at three scopes, and this branch reproduced that result twice
more. **So no document here asserts exhaustiveness for it.** Widening the pattern has now failed
four times; withdrawing the claim cannot fail the same way, because it claims nothing a sweep has to
support.

### ⚠ And one survivor is kept deliberately — the distinction the sweep cannot make

*"two of them look measurable"* is a **finding**: §2 names the two signals that are mechanisable.
*"All five were settled"* was a **tally** of the document's own contents, and is gone. A wider sweep
confirms the rest are measurements and findings — *14 minutes*, *three hand-kept path lists*, *six
functions*, *13 mutation entries*. **The defect was never numbers. It was numbers that must be
maintained to stay true**, and a pattern cannot tell those apart — which is the real reason the
instrument was always going to lose.

## Also verified rather than accepted

No section under more than one banner status (Codex read the rows rather than trusting an `rg`
count, and noted the extra `§N` hits are explanatory prose inside cells). Meaning was not lost by
removing the counts. `check-docs.py`, `check-dashboard-entry.py`, `git diff --check` all pass.
