# Round 1 — `marketplace-task17` — coordinator — NOT CONVERGED; eleven findings fixed, one filed (backlog #696)

Both halves reviewed 94e9fd08 (plan Task 17 of `docs/superpowers/plans/2026-11-11-marketplace-inventory.md`, PR #616:
the CI layer's six effort (2) inventory rows and the engine comparison). Codex:
`docs/reviews/codex/marketplace-task17-r1-codex.md` (X1, X2 MAJOR; X3, X4 MINOR; NOT CONVERGED). Claude:
`docs/reviews/claude/marketplace-task17-r1-claude.md` (C1 MAJOR; C2 to C8 MINOR; NOT CONVERGED). Every finding came from
the build, not from a fold, so none is fix-induced. Severity below uses the header grammar's words: MAJOR is `High`,
MINOR is `Medium`.

- **X1 = C1, one defect.** `coverage-verdict` is a stdlib-only type module (imports `sys`, `dataclasses`,
  `__future__`), not a parser. `check-plan-code` imports it (`check-plan-code.py:104-109`) and nothing goes the other
  way at runtime; `sweep-red-alert`'s import (line 442) is in its self-test. Re-argued: C3 pass, C4 pass (the engine's
  C4 failure is attributed to the manifests, not to this library), verdict DON'T-SHIP on reasoning (its only runtime
  consumer is the DON'T-SHIP engine), harvest none, route practice. Scenario now names `check-plan-code`. The scan
  emitted nothing for it, so `cites: []` (disposition 5 below). Dashboard entry's "the parser it reads" removed.
- **X2 = C2.** `sweep-red-alert`'s runtime (`main`) needs only the standard library and `gh`. The C3 fail is re-argued
  from `RECORD_SCHEMA` (line 58, written by `check-plan-code.shard_record`) and the five-key `record_problem` contract,
  plus the self-test's dependency on the engine. The three cites are kept and labelled as self-test lines (the scan
  has no finding on the runtime path). C2 now rests on `gh`; git is self-test only. Route re-priced from 6 h to 3 h
  (publish the record contract; replace `_writer` with literal fixture records), public bar 8 → 6 h, next project
  3 → 2 h.
- **X3.** Conclusions (a) and (c) and the dashboard entry now scope each absence to the fetched pages.
- **X4.** The plan clarifications (route `kind` vocabulary; how a zero-finding row is substantiated) are filed with
  Claude's ambiguities 1, 2, 4, 6 and 7 as **backlog #696**.
- **C3.** `check-plan-code` cites `:2:1` (described as an `unread` load, an unjudged coupling, not a repo path) and
  `:6:3`. `:4:1`, `:4:2` and `:6:1` are dropped and named as self-test internals. C3 rests on spec §2c and
  `HARNESS_TREE`, which has no scan finding (stated as a bound).
- **C4.** `mutation-sweep-job` cites `:2:106`, `:2:107` and `:2:108` (the three findings at line 1117 or later);
  `:2:98` and `:2:21` (verify-job steps) dropped. Split restated: 105 of 108 findings precede line 1117.
- **C5.** `mutation-manifests` has zero scan findings, so it cites nothing (`cites: []`), per disposition 5. Its C5
  now follows the same rule as `velocity-docs`: a data row's C5 is pass only when a content review covers it; none
  does, so both are `unanswered`.
- **C6.** cargo-mutants `ci.html` (one full `cargo mutants -vV --in-place` job, pr-diff only linked), Stryker pipeline
  (break threshold and dashboard baseline; upload sourced from the dashboard page, re-fetched) and Stryker.NET `since` /
  `with-baseline` reworded to the pages' own words; the "marked experimental" claim dropped.
- **C7.** The PIT/Arcmutate row is `fetched` against `https://pitest.org/quickstart/maven/`, quoting "arcmutate's git
  integration" and "provides pull request integration"; "now lives in" removed. 0 rows are `unverified` now.
- **C8.** Conclusion (b) now records mutmut's stack-depth test relevance and Stryker's per-test mutation coverage as
  the nearest equivalent to observed-reach selection, and keeps only the import-closure absence. mutmut and StrykerJS
  incremental rows extended to match.

Every page cited in a changed sentence was re-fetched 2026-11-22 (eight pages, all HTTP 200).

**Disposition 5 conflict, recorded, not papered over.** Two non-SHIP rows (`coverage-verdict`, `mutation-manifests`)
now have `cites: []`. The plan's Task 19 rule requires a non-SHIP row to cite an emitted finding, so the throwaway
row checker reports exactly those two rows; that is plan gap (b) of backlog #696.

```yaml
round: 1
fixes_nontrivial: true
subject: marketplace-task17
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: marketplace-inventory-rows, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: false, component: marketplace-inventory-rows, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: false, component: marketplace-inventory-rows, disposition: fixed}
  - {id: X4, severity: Medium, aim: deliverable, fix_induced: false, component: marketplace-inventory-rows, disposition: filed}
  - {id: C1, severity: High, aim: deliverable, fix_induced: false, component: marketplace-inventory-rows, disposition: fixed}
  - {id: C2, severity: Medium, aim: deliverable, fix_induced: false, component: marketplace-inventory-rows, disposition: fixed}
  - {id: C3, severity: Medium, aim: deliverable, fix_induced: false, component: marketplace-inventory-rows, disposition: fixed}
  - {id: C4, severity: Medium, aim: deliverable, fix_induced: false, component: marketplace-inventory-rows, disposition: fixed}
  - {id: C5, severity: Medium, aim: deliverable, fix_induced: false, component: marketplace-inventory-rows, disposition: fixed}
  - {id: C6, severity: Medium, aim: deliverable, fix_induced: false, component: marketplace-inventory-rows, disposition: fixed}
  - {id: C7, severity: Medium, aim: deliverable, fix_induced: false, component: marketplace-inventory-rows, disposition: fixed}
  - {id: C8, severity: Medium, aim: deliverable, fix_induced: false, component: marketplace-inventory-rows, disposition: fixed}
```
