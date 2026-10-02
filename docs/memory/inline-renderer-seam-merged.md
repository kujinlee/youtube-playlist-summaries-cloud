---
name: inline-renderer-seam-merged
description: "FIRES-WHEN: citing backlog #71, PR #180, or the shared page renderer — Backlog #71 MERGED — PR #180, squash 0972c55, 2026-08-30. One renderer (scripts/page_markup.py) for all four page generators; #72 and #73 filed alongside; Phase 6 candidates 3 and 4 still open"
metadata: 
  node_type: memory
  type: project
  originSessionId: 026980a1-ac42-4306-9327-ecd78a7e933b
  modified: 2026-08-31T01:13:13.957Z
---

**MERGED 2026-08-30 — PR #180, squash `0972c55`, branch deleted.** Phase 6 **candidate 1** from
`docs/reviews/architecture-review-2026-08-30.md`. Spec:
`docs/superpowers/specs/2026-08-30-inline-renderer-seam-design.md`, anchor `status-visibility`.

**What shipped.** `scripts/page_markup.py` — one escape rule, one left-to-right scan at the union
feature set, `safe_href`, `trim_url_tail`, `orphaned_delimiters`. All four generators import it
(`gen-dashboard`, `gen-backlog-page`, `gen-goals-page`, `explainer-serve`).
`_close_orphan_markup` stays in `gen-dashboard` — truncation POLICY, not rendering, and it asks the
renderer rather than copying it. **Underscore filename = importable library**; the hyphenated
`scripts/*.py` are executables, which is why they need `importlib`.

**The decision that shaped it (user, 2026-08-30):** ONE behaviour for all four pages = the *union*
feature set carried by the *single-scan algorithm* — **not** `gen-dashboard`'s feature set, which is
minimal only because its corpus is (0 markdown links in 593 lines; adopting it would have stripped
59 `<em>` spans and 3 links off the backlog page). Generators' inline cases DELETED, not kept.

**Verified on regenerated pages:** `backlog-table.html` 6→0 crossed spans and 10→0 markup-in-code;
`goals.html` and `dashboard.html` both 0/0; no `javascript:` hrefs anywhere. Four generators agree on
8/8 probes (they disagreed on **11 of 13** before). `--mutate .` 3 files, **73 mutations, 0 survivors**.

⭐ **`EXPECTED_MUTATIONS` is now gen-dashboard 47 + page_markup 14 + check-dashboard-entry 12, and the
SUM IS DELIBERATELY UNCHANGED AT 73.** 14 entries moved to the file they guard; only the per-file
split distinguishes a relocation from a deletion. Do not "simplify" that to a total.

**Filed alongside, NOT fixed:** backlog **#72** 🟠 the guard inventory cannot see a guard not *named*
`check-*` (population is `glob("check-*.py")` at `check-ratchet-contract.py:395`, so the
docstring-self-declaration route is unreachable — same shape as the review's finding A, one layer
out); **#73** 🟢 `discover_ratchets` is dead code reached only from its own self-test, blocked on #72.

**Still open:** Phase 6 **candidate 3** (the `HOME` question — measured: harness passes under a
redirected home 73/0, writing nothing; the trade is destruction-hazard removal vs output-path
fidelity, since six scripts resolve `Path.home()` at module level) and **candidate 4** (flatten the
verification stack — its arithmetic improved, since the same stack now defends four pages).

⚠ **`docs/roadmap-to-launch.md` still says "PR OPEN"** for this section — it should read merged via
#180. Ride that tick in the next docs PR rather than pushing to master.

Lessons: [[a-report-format-is-a-contract]], [[measure-the-population-the-code-actually-sees]].
