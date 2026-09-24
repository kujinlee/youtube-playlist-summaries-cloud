# Round 2 — `velocity-177` — coordinator

```yaml
round: 2
fixes_nontrivial: false
subject: velocity-177
halves:
  codex: ran
  claude: "GAP: not dispatched — rounds 2+ alternate to the half that did not author the fix (review-method.md Round topology, step 4); the coordinator authored the r1 fold, and the risk was reproduction, which that step routes to Codex"
findings:
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: number-populations, disposition: fixed}
```

REVIEW GAP: claude — rounds 2+ alternate to the half that did NOT author the fix (`review-method.md` -> Round topology, step 4). The coordinator authored the r1 fold and the risk was reproduction, which that step routes to Codex. Not a failure to run: a deliberate, rule-directed single-half round.


**Subject:** the r1 fold (`git diff 229be47a..HEAD`), not the original change.
**Half:** `codex/velocity-177-r2-codex.md` — `gate_ran=true`, model `gpt-5.5`, **NOT CONVERGED, 1 Medium**.
**Why r2 existed:** r1 produced two High, and `check-review-decision.py` returned `ROUND_OWED`. This
repo's measured rule is that the defects surviving furthest are the ones a FIX introduced, which a
concurrent pair on one frozen tree structurally cannot see.

## The finding, and why it is the most useful one of the branch

**M1 (Medium, fix-induced).** Rule 4's repaired scope is correct; its new measured count was not. The
fold wrote *"`ci.yml` invokes **34** distinct `scripts/*.py|sh`"*, from
`grep -oE 'scripts/…' ci.yml | sort -u`. Parsing the actual `run:` blocks gives **33**.

**The 34th is `scripts/check-schema-gates.sh`, which appears in `ci.yml` ONLY IN COMMENTS** (`:267`,
`:286`) — *the exact fact H2's correction rests on.* The fold established that fact to fix H2 and
then contradicted it one paragraph later, because the second measurement asked a different question
with a similar-sounding command.

⭐ **This landed inside rule 1b's own evidence table**, which the r1 fold had written to illustrate
*say what you counted*. Reproduced by the coordinator before fixing:

    ci.yml — invoked in run: blocks      : 33
    ci.yml — raw text occurrences        : 34   (what the grep counted)
    difference (text-only, NOT invoked)  : ['scripts/check-schema-gates.sh']
    ci.yml — distinct check-* invoked    : 28
    schema-gates.yml — invoked           : 4

Rule 1b gained a fourth row: **the row about itself.** A rule that catches its own author in the act
of writing it is stronger evidence than the three historical rows it was built from — it shows the
slip is not carelessness but a property of how measuring works, because `grep` answers a question
that *sounds* identical to the intended one.

## Dispositions verified by the reviewer, not accepted

Codex checked all thirteen r1 dispositions individually. **H1 fixed** — and it re-derived the
replacement claim rather than taking it: PR #342's `verify` ran 02:30:23Z → 02:38:31Z, exactly
**8m08s**, so the speed argument that now carries the practice is supported. **H2 partly fixed** —
scope correct, count wrong (M1 above). **M1–M6, L1–L5 fixed**, each with a `file:line`.

## ⚠ Thrashing watch — one link, not two

M1 is **fix-induced in the `number-populations` component**. The arming condition for an architecture
review is *two consecutive rounds carrying findings caused by the previous round's fix, in one
component*. This is link **one**. If r3 returns a fix-induced finding in the same component, that is
the trigger and it fires — it is not a count, and it is not to be litigated.

⚠ Against that: the component is a **number in prose**, not a mechanism, and this repo has measured
that a document can be right forever. The r2 fix changes one digit and adds a row; the de-escalation
rule applies if r3's findings shift to wording.

## ⚠ Gates — what actually ran

Codex ran, locally: `npm ci`, `npx tsc --noEmit`, the unit suite (**2,892/2,892**), the docs/static
self-test guard batch, `check-dashboard-entry` and `check-review-recorded` against the PR body, the
full local schema gates (**15/15**), and `git diff --check`. In CI it read `gh pr checks 345`:
`verify` **pass 11m14s**, `schema-gates` **pass 1m44s**, and `check-merge-ready.py --pr 345`
reporting **READY**.

⛔ **`check-plan-code.py --mutate .` was STARTED AND INTERRUPTED at 533/1030 locally** — the reviewer
stopped it once GitHub's `verify` completed green, treating the CI run as the authoritative one.
That is the adopted sweep policy working as intended, but it is recorded here as **a local run that
did not finish**, not as a local pass. The authority for the sweep on this branch is the CI `verify`
job, and nothing else.
