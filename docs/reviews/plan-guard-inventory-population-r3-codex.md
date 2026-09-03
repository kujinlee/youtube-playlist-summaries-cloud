# Post-Plan Gate — round 3 — Codex half

**Subject:** `docs/superpowers/plans/2026-09-02-guard-inventory-population.md` **v3**.
**Scoped to v3's own fixes.** Branch `fix/guard-inventory-population`. **Backlog:** #72, #73.
**Date:** 2026-09-03.

**Provenance.** `scripts/codex-review.py --prompt-file` → `gpt-5.5`; 3,015-char final message.
`verdicts/plan-r3-codex.verdict.json`, `gate_ran=true`.

**VERDICT: NOT CONVERGED** — 1 Blocking, 2 High. (r1: 4 Blocking · r2: 2 · r3: 1.)

> ✅ **THE PLAN IS NOW MECHANICALLY EXECUTABLE — the first round where that is true.** The reviewer
> applied T1–T7 in a temp copy and ran the mutation suite:
> `OK — delivered scripts mutated: 8 file(s), 166 mutation(s), 0 survivor(s)`.
> Rounds 1 and 2 both established it could **not** run. The three findings below are **completeness**,
> not correctness — a different and much later class of defect.

---

## Blocking — the change would close #72/#73 while they still assert the deleted mechanism

T9 says how to close the rows (Item cell, Status cell, `GROUPS` tuple) and **never says to rewrite the
row bodies**. `docs/backlog.md` is in neither T8's file list nor F8's grep.

**CONFIRMED by the author:**
```
$ grep -c 'discover_ratchets\|glob("check-\*\.py")' docs/backlog.md      -> 2
$ (docs/backlog.md mentioned anywhere in T8 or F8)                       -> 0
```

Spec v4 §7 lists those rows explicitly: *"edited by this PR anyway; **must not be left describing the
old mechanism**."* Shipping as written violates the spec's own blast-radius section — and reproduces
§1.2's shape (a false claim surviving at a site nobody swept) **in the very rows that record the
finding**.

**v4:** T9 gains a step rewriting both bodies; `docs/backlog.md` joins F8's grep.

## High — F8 does not cover every site T8 lists

T8's modify list includes `docs/superpowers/specs/2026-08-30-inline-renderer-seam-design.md:176,183`.
F8 greps only `scripts/ .github/ .claude/ docs/process-checklists.md docs/dev-process.md
docs/roadmap-to-launch.md`. An implementer can skip that living spec and still pass the falsifier.

⚠ **F8 has now been wrong in FOUR consecutive versions** — too narrow for `docs/`; unsatisfiable via
`docs/`; unsatisfiable via `__pycache__`; and now narrower than the task it guards. Each fix corrected
the instance and left the class. **v4 derives F8's path list from T8's own file list rather than
restating it**, so the two cannot diverge again.

## High — the manifest dropped the non-string mutation the spec requires

Spec v4 §10 requires `NOT_A_GUARD` **detection accepting a non-string value** → red via that case.
Plan v3's four entries are: population default, nested assignment, whitespace-only reason, stop
compiling. The non-string discriminator has a self-test case but **no mutation proving it
load-bearing**.

**CONFIRMED:** spec `:446` names it; the plan's manifest names do not include it.

**v4** adds a fifth entry (`isinstance(value.value, str)` → `True`), expecting
`NOT_A_GUARD: non-string value`; `EXPECTED_MUTATIONS` becomes **5** and the sum **167**, not 166.
⚠ That also moves T7 Step 2's third edit, which v3 pins at 166.

---

## Disposition

All three accepted; all re-verified by the author. None disputes the executed 166/0 result — they
concern what the suite does **not** cover, and one document the change forgets to correct.

Claude half: [`plan-guard-inventory-population-r3-claude.md`](plan-guard-inventory-population-r3-claude.md).
