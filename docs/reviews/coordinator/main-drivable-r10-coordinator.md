# Round 10 — coordinator's record: the Phase 6 arming call, and what the fold actually did

**Subject:** `scripts/check-main-drivable.py` · branch `d2-main-drivable` · PR #365
**Reviewed tree:** `5101f82c` · **Round 10 Claude half:** `docs/reviews/claude/main-drivable-r10-claude.md`
**Written:** 2026-10-05, by the coordinator, after folding.

This file exists because `docs/review-method.md` requires the thrashing call to be recorded with its
per-finding evidence, and because the round's own reviewer explicitly declined to make it
(*"the arming condition deserves the coordinator's judgement, and I am not going to decide it
quietly"*). The review document is **testimony** and is not edited here.

---

## 1 · The arming condition appears met on its face

`docs/dev-process.md` arms an architecture review when **two consecutive rounds carry findings caused
by the previous round's own fix, in one component**. Round 10's own table:

| | |
|---|---|
| findings | 11 — 1 Blocking, 3 High, 4 Medium, 3 Low |
| aimed at the deliverable | **10 of 11** |
| caused by round 9's own fix | **6 of 11** (B1 partly; H1, H3, M3, M4, L1, L3) |
| component | one — `scripts/check-main-drivable.py` throughout |
| round 9, the round before | its Blocking was round 8's repair one step short |

So the surface condition holds: two consecutive rounds, fix-induced findings, one component.

## 2 · But the surface condition is not the test, and using it as one has a measured cost

`review-method.md:198` is explicit:

> **⚠ THE SYMPTOM LIST IS A PROMPT, NOT THE TEST. There is one test, and it is this:**
> ### Can a redesign remove it?

and `:212` records why the distinction is written down rather than assumed: applying the symptom list
as a checklist on 2026-08-14 produced a **false REDESIGN** in one reviewer and a true one in the
other, on the same document. Two findings both matched a listed symptom; only one was a mechanism
defect.

**Applying the single test to round 10's Blocking:** B1 is `substitution_changes_the_world`
discarding `world_class`'s LIVE verdict whenever any leaf of the value is a name the case bound.
A different shape — one authoritative world verdict that no route may override, or the narrower
repair actually taken — **dissolves it**. It is therefore a **mechanism defect**, and the redesign
is owed.

## 3 · The call: the redesign was OWED and was DONE — there is no override to record

The rule says a mechanism defect escalates *from FIX to REDESIGN, and the next round is a design
review*. That remedy was applied **inside this fold** rather than deferred to a separate Phase 6
review, because the redesign the test pointed at was local to one function and nameable:

> replace the **proxy** — *a case-bound name appears in the expression text* — with the
> **property** — *does this value hand back the same world global it is replacing?*

This is the sound warrant, not the unsound one. Three deletions in this slice were **reversed**
because they were argued *"its mutation cannot die, so the clause does nothing"*; the deletions that
**held** were argued *"a later, more general mechanism subsumes it"*. The module-dict branch one
level up already compares resolved world identity to the name being replaced
(`return _key is not None and _key != name`); the clause below it was the same question asked
through a weaker proxy. That is the second warrant.

**Nothing here is an override**, so no override falsifier is owed under `:245`. What is owed is the
ordinary one:

> **FIRES TO ARCHITECTURE REVIEW IF:** round 11 produces a fix-induced finding in
> `scripts/check-main-drivable.py` that is a **mechanism** defect — one a redesign would dissolve —
> rather than a branch-coverage gap or a stale cross-reference.

**Decision taken by the repository owner on 2026-10-05**, from a selection card offering (A) the
named redesign, (B) patch-in-place plus another defect-hunt round, (C) stop and merge with the
residue written down. A was chosen.

## 4 · ⭐ The coordinator's brief was wrong, and the implementer refuted it with a measurement

Recorded because it is the clearest instance this slice has produced of *a finding is real and its
proposed fix is a hypothesis* — and this time the bad hypothesis was **mine**, not a reviewer's.

The brief specified `return bool(yielded) and yielded != {name}`, and claimed it would close all five
of B1's measured rows. The implementer refused that form and reported why:

- it **refuses 9 asserted cases**, six of them defending the modified-copy substitution the clause's
  own docstring exists for (`check-surface-recall.py:652`);
- three of the brief's five rows — `os.path.relpath(td)`, `os.path.join('.', td)`,
  `os.path.join(f'.', td)` — are **correctly credited**, because at run time they hand `main` the
  tempdir the case built.

**Verified by the coordinator, by running it rather than reasoning about it:**

```
os.path.join('.', td) == td          ->  True   (the '.' is discarded; td is absolute)
os.path.relpath(td)   resolves to td ->  True
```

Had the brief been implemented literally it would have introduced **three false refusals**. What was
actually built keeps the leaf test as the **residual** rule for values whose provenance cannot be
followed, and replaces only the part that was a proxy — resolving a Name through its bindings and a
Call through `_resolve_callee` in the callee's own scope, which is what makes `same_root(td)` hand
back `ROOT`. It closes **3 of the 5 rows deliberately, not 5**, with the other two recorded as a
stated lost credit on PARAM rather than a false green on REBIND.

## 5 · Verification — the coordinator's own, against a control taken before the work

| check | result |
|---|---|
| `--self-test` | **437/437**, rc=0 (404 before) |
| guard over the real population | rc=0 — `param 3, argv 3, rebind 8, subproc 1`; 10 compliant, 27 debt |
| manifest vs `EXPECTED_MUTATIONS` | **183 == 183**; declared sum `1341 -> 1361` |
| mutations run by the implementer | 28 against a green 436/436 control, **zero survivors**, each dying via the case its `expect` names |
| **44-guard table** (the LIVE control) | **0 rows changed** — 44 classified, 10 compliant, every row byte-identical |
| expression probe, 36 cells | **1 flip**: `same_root(td)` on rebind `['rebind'] -> []` — the Blocking, closed |

⛔ **`--mutate .` was NOT run.** The full sweep needs ~85 minutes (measured; backlog #217 amended at
`5101f82c`), and PR #365's `verify` job is red for exactly that reason. Treat the whole-repo mutation
evidence as **NOT RUN**, not as passed.

⚠ Two of the implementer's own new cases **could not fail** on first run and were rebuilt — the
branched-binding row was answered by `_is_restore_value` before the rule under test, and the
`_parents` severance was invisible because the scope climb still appends `fn` and the module. Both
are the same class as H1, found by running the mutations rather than by reading the cases.

## 6 · Convergence

**NOT CONVERGED.** The stop condition (`review-method.md:104`) judges by **aim, not severity**, and
counts **two consecutive** rounds with no Blocking/High, nothing in the deliverable, and no
non-trivial fixes. Round 10 had a Blocking, three Highs, ten findings in the deliverable and a
non-trivial fix. **The counter remains at 0.**

Round 11's Codex half is dispatched against the tree that merges, which is also what
`scripts/check-review-recorded.py` requires before this branch can go green.
