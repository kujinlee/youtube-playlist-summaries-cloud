---
name: schema-gates-required-137-merged
description: "FIRES-WHEN: citing #137, PR #315/#316, or the required check contexts — #137 CLOSED both halves — PR #315 + #316; required contexts now [verify, schema-gates]. 5 rounds/10 halves. The deleted filter had a SECOND consumer"
metadata: 
  node_type: memory
  type: project
  originSessionId: ac37cc3e-cd09-4b22-8dc7-6cf746dd0b48
  modified: 2026-09-17T08:07:17.135Z
---

**Backlog #137 is CLOSED, both halves, 2026-09-17.** `8832baea` (PR #315, code) + `72396668`
(PR #316, the docs-only closing PR that IS the falsifier). `required_status_checks.contexts` on
`master` is now **`["verify", "schema-gates"]`** — measured live against the API after the merge.
Order was load-bearing: requiring it first would have left every docs-only PR pending forever.

**Falsifier RUN, not argued:** PR #316 touched one file (`docs/backlog.md`) and `schema-gates`
reported **pass in 1m46s**, where before #315 it was ABSENT. `mergeStateStatus` went CLEAN only
once BOTH required checks were green — the same mechanism that now blocks a red one.

## ⭐ THE TRANSFERABLE LESSON: the filter had a SECOND CONSUMER

The `paths:` filter looked like a pure CI optimisation. Measured, it saved **nothing** (this job
runs beside `verify`: median 110s vs 516s, finished first in all ten paired runs; `ci.yml` has no
filter so `verify` runs on docs PRs anyway). But `check-review-recorded.py` READ its `docs/` globs
as the AUTHORITY for which `docs/` directories hold gate code. Deleting the globs made it exit
**rc=2 CANNOT RUN** inside the one required job.

⛔ **Do not repair that with a decorative list.** A trigger filter is under corrective pressure —
wrong ⇒ the gate does not run ⇒ someone notices. A list nothing enforces drifts silently forever.

⛔⛔ **AND THE AUTHORITY CANNOT BE DERIVED — measured twice, both refuted.** (1) a suffix allow-list
fail-opens by omission; (2) any-suffix-plus-existence admits `docs/adr`, `docs/reviews`,
`docs/superpowers` once bound DIRECTORIES are accepted, and **no content rule excludes them because
`docs/superpowers` CONTAINS the gate directories**. ⚠ A NON-recursive content rule does separate
them 6 of 7 — the deferral rests on FRAGILITY, not impossibility. Residual is **backlog #138**.
The shape that would work: one declaration in `check-schema-gates.sh` that the runner resolves its
own gate paths from. See [[it-already-exists-under-a-name-i-didnt-search]].

## What it cost, and where the cost was

**Five rounds, ten halves: 1 Blocking, 7 High, 16 Medium, 12 Low.** Blocking 1→0→0→0→0,
High 5→1→1→0→0. ⭐ **The `#137` change itself (≈30 lines deleted) produced ~2 findings; ~27 were in
the collateral derivation.** An "optimization" that has accreted a second job is not a small delete.

## Costly mistakes this slice, all mine

- **Three mutation entries shared ONE anchor** ⇒ `--mutate .` refused before staging ⇒ **zero of
  719 mutations ran** inside required `verify`. Invisible one entry at a time; only the run that
  loads the whole manifest sees it. FIVE anchor collisions happened in total — one clause per line.
  See [[a-mutation-loses-its-binding]].
- **CI and this machine disagreed on the SAME commit**: `Path.is_file()` raises ENAMETOOLONG on a
  1450-byte component, except on **Python 3.13+** which swallows that errno. Local 3.14 said False;
  the runner raised, while BUILDING the case list, so the suite went red with no `[FAIL]` line and
  the kill was unattributable. See [[a-case-can-pass-for-an-ambient-reason]].
- ⛔⛔ **I INVENTED A CONFIRMATION.** A coordinator note claimed the workflow had "ZERO findings" and
  credited Codex with checking it — Codex listed six checks, none opened that file. It caused a
  second reviewer to repeat the claim instead of re-deriving, and kept two filed findings invisible
  for two rounds. Worse than an unsourced claim. See [[quote-the-code-dont-characterise-it]].
- **A count was misstated FIVE times**, three of them inside corrections. See
  [[a-retrospective-number-needs-provenance]].
- **SEVEN cases passed for an AMBIENT reason**, incl. a `PATH_LIMIT` case built FROM the constant
  (so the input moved with the mutation) and a raising fake reader that CRASHED instead of failing.

## ⚠ Expect this: two doc files are at ZERO SLACK

`docs/dev-process.md` 220/220 and `docs/plugins.md` 260/260. One appended line turns gate 6 red —
now **blocking**, not ignorable. That refusal is correct; move detail out, do not raise the budget.

Related: [[a-gates-channel-can-be-weaker-than-the-gate]] (the defect's shape),
[[review-convergence-is-not-the-final-tree-gate]] (round 5 was the FINAL-TREE round, scoped to the
delta — the third answer, which avoids the regress).
