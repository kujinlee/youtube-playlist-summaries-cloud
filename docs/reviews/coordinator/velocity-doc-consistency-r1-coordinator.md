# Round 1 — `velocity-doc-consistency` — coordinator

```yaml
round: 1
fixes_nontrivial: true
subject: velocity-doc-consistency
halves:
  claude: ran
  codex: ran
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: true, component: round-attribution, disposition: fixed}
  - {id: H2, severity: High, aim: deliverable, fix_induced: true, component: round-attribution, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: overclaimed-scope, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: false, component: self-counts, disposition: fixed}
```

**Subject:** a three-line prose fix to `docs/development-velocity.md`. **Both halves ran**, dispatched
concurrently per `review-method.md` step 1.

## ⭐ The fix for a count defect contained two wrong counts

The three target contradictions were fixed correctly. **Both Highs are in the replacement text**, and
both are round attributions written from memory rather than derived.

**H1.** The new note said *"six review rounds plus an architecture review passed over it — none of
them had this file's internal consistency in scope."* **False in both halves**, and the Claude half
derived each from git:

- `git show ccc19857` shows the **r3 fold ADDING** the closing sentence, so the contradiction did not
  exist before it. Only **r4, r5, r6** followed — three, not six.
- r3 plainly **did** have it in scope: its finding is titled *"four rules" names a population of
  five* and cites this paragraph. **r3 found the defect; the fold repaired it badly.**

**H2.** The banner note credited the double-status rows to *"the r5 fold"*. `git show e44be4b0` — the
**round-1 fold** — is the single commit that split the catch-all row, and **no r5 or r6 commit touches
this file at all**. The defect stood through **r2–r6**.

⭐ **THE TELL IS THAT THE TWO CLAIMS ARE WRONG IN OPPOSITE DIRECTIONS** — too many rounds in one, too
few in the other. That is what a count nobody derived looks like. **Rule 1 applies to counts of our
own history**, not only to counts of code, and neither of these was looked up.

## The Codex half declined a High I had set up for it

The brief said: *"if ANY round did examine this file, the PR's central excuse is false and that is a
High."* Codex checked, found the rounds **had** touched the file, and **declined the High anyway** —
because touching a file in a diff review is not sweeping it for internal consistency, and the
distinction is the point. It offered the narrower true claim instead. **A reviewer correcting the
reviewer's instructions**, which is worth more than the finding it declined to inflate.

## L1 / M1 — the fix was incomplete and the claim was absolute

Codex (Low) and Claude (Medium) converged from different directions on the same thing: surviving
counts of the file's own contents — `§3` headed *Four signals* plus *"all four"*, `§9` headed *The
five open questions*, `§10`'s *"two of four"*, two more in §2's Q0 block, and a *"three rows above"*
in the banner note itself. Removed, and the sections now **list** rather than count.

⛔ **The first version of this line said "ALL removed" and r2 refuted it (High).** Two survived —
`"All five were settled"` and `"two of them look measurable"` — because the sweep that certified
the claim required a noun from a fixed list, and those say *settled* and *them*. **That is the
fourth pattern today that was narrower than the claim it certified** (bolded digits → any digits →
number-words → a noun list), so the fix is not a fifth pattern: **this document no longer claims
exhaustiveness for this class**, because no exhaustive instrument exists — the syntactic proxy is
refuted at three scopes by *Qualify every number in prose*.

⚠ **AND ONE SURVIVOR IS KEPT ON PURPOSE.** *"two of them look measurable"* is a **finding** — two
specific signals are mechanisable, and §2 names them — not a tally of the document's own contents.
*"All five were settled"* was a tally and is gone. The defect was never *numbers*; it was numbers
that must be maintained to stay true.

⚠ Claude's M1 is the sharper form: the dashboard entry's *"no count-of-rules survives"* is refuted by
the **immediately preceding entry**, which opens *"four rules about what an author writes down"*.
Corrected by a **new entry**, since the store is append-only.

## What both halves verified rather than accepted

`git diff --check` clean · each §1–§10 now in exactly one banner status row · `process-checklists.md`
untouched as claimed · **attack 3 TRUE** (r3's fix appended rather than edited, verified from the
`ccc19857` hunk by both halves independently) · `check-docs.py` and `check-dashboard-entry.py` rc=0.

## ⚠ Why this round was worth running on a prose fix

`check-review-recorded.py` reports no guarded path changed, so no round was *required*. It found two
High findings anyway — both invented numbers, in the fix for invented numbers. The scope rule that
made this a one-round change was right; the instinct to skip the round would not have been.
