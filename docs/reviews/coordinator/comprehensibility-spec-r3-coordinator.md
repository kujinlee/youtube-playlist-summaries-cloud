# Round 3 — `comprehensibility-spec` — coordinator — ⟳ NOT CONVERGED (Claude); 4 fixed, 0 to the owner; Phase 6 armed and run

```yaml
round: 3
fixes_nontrivial: true
subject: comprehensibility-spec
halves:
  claude: ran
  codex: skipped
findings:
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: status-facet, disposition: fixed}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: true, component: status-facet, disposition: fixed}
  - {id: M3, severity: Medium, aim: deliverable, fix_induced: false, component: needs-you, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: false, component: status-facet, disposition: fixed}
```

REVIEW GAP: codex — alternation

Reviewed head `1dfb7344`. Claude half: `docs/reviews/claude/comprehensibility-spec-r3-claude.md` (M1–M3, L1; verdict
`docs/reviews/verdicts/comprehensibility-spec-r3-claude.verdict.json`). Round 3 is alternated, so only Claude ran.
Folded into `docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md` per the architecture review below.

**Rule applied:** the owner's answers (spec §1, §8, §10 Q1) are fixed; none had to change.

| ID | Sev | Disposition | What the spec now says |
|---|---|---|---|
| M1 | Medium | FIXED — by REMOVAL | §4 states the migration RULE in one sentence (strip leading glyphs, emphasis and a `(was …)`/`(filed …)` parenthetical; map the first word; prepend; keep the old cell). The per-value table and the normalisation grammar are gone; row 2's code computes them over the real file and its test pins the counts on its build commit |
| M2 | Medium | FIXED — by REMOVAL | the unsourced "16 not-done rows" is gone. §4 and row 2: the OWNER decides, at row 2's build, every row the rule cannot settle, from a list row 2's code produces — unmapped first words, cells a later `✅` contradicts, and every `needs-you` candidate. §10 notes it |
| M3 | Medium | FIXED | row 4 *Reference*: an entry references row N iff it carries a declared `row: N` field (`session-state.py --add … --row N`, beside `kind`); text mentions in `what`/`on_done` reference nothing; legacy entries migrate with no `row`. §7 new falsifier: a `needs-you` row leaves "waiting until picked" while no live entry's `row:` equals it |
| L1 | Low | FIXED | §5 and §9: `✅` in the Item cell on **150 of 422** rows, `gen-backlog-page.parse` `sev == "done"` on `befd0e6d` (= `origin/master` at r3); the old 117 of 333 is kept as history, sourced `9ac7c80d` |

**Counts:** 4 findings — 4 fixed, 0 rejected, 0 escalated. Spec 284 → 279 lines.

## Thrashing

**Armed.** `status-facet` carried fix-induced findings in two consecutive rounds — r2 C1 (from r1's H5 fold) and r3
M1, M2 (from r2's C1 fold) — the arming condition in `docs/dev-process.md` → *Phases*. `needs-you` is NOT armed: its
fix-induced findings were r2 only (C2, C3); r3's M3 predates r2.

The Phase 6 review is `docs/reviews/architecture-review-2026-11-02-spec-status-facet.md`. In short: every
status-facet finding since r1 attacked row-level arithmetic a fold had typed into prose, never the facet's design;
the redesign (rule + owner-at-build + falsifier in the spec, counts in row 2's build) would have prevented 4 of the 6
status-related findings of r2–r3 (C1, M1, M2, L1; not C2, C3). The coordinator's hypothesis held for the remedy and
was partly refuted on the cause — the backlog did not move during these rounds; prose failed to carry a computation.

**Stop condition for round 4** (from that review): a finding asking the spec for a count, row list or normalisation
detail of the status migration is FILED against row 2's build, not folded. A fix-induced `status-facet` finding that
is about the facet itself (the four values, no default, owner-at-build) means the redesign failed — to the owner.

## Round cap

This was round 3. **From round 4 on, findings are FILED unless a BLOCKER** (`docs/review-method.md` §0 Q4c). Round 4,
if run, is ONE half (alternation: Codex), and its non-BLOCKER findings go to the backlog or to row 2's build, not
into this spec.
