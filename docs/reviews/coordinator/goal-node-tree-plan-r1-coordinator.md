# Round 1 — `goal-node-tree-plan` — coordinator — ⟳ NOT CONVERGED (both halves); 12 fixed, 0 rejected, 0 ESCALATE

```yaml
round: 1
fixes_nontrivial: true
subject: goal-node-tree-plan
halves:
  codex: ran
  claude: ran
findings:
  - {id: XB1, severity: Blocking, aim: deliverable, fix_induced: false, component: page-links, disposition: fixed}
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: batch-ci, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: false, component: batch-ci, disposition: fixed}
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: false, component: wiring-pins, disposition: fixed}
  - {id: XM4, severity: Medium, aim: deliverable, fix_induced: false, component: page-links, disposition: fixed}
  - {id: XM5, severity: Medium, aim: deliverable, fix_induced: false, component: ids, disposition: fixed}
  - {id: Xm1, severity: Low, aim: deliverable, fix_induced: false, component: migration-slices, disposition: fixed}
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: false, component: grammar, disposition: fixed}
  - {id: CM2, severity: Medium, aim: deliverable, fix_induced: false, component: guard, disposition: fixed}
  - {id: CM3, severity: Medium, aim: deliverable, fix_induced: false, component: migration-slices, disposition: fixed}
  - {id: Cm1, severity: Low, aim: deliverable, fix_induced: false, component: guard, disposition: fixed}
  - {id: Cm2, severity: Low, aim: deliverable, fix_induced: false, component: guard, disposition: fixed}
```

Halves: `docs/reviews/codex/goal-node-tree-plan-r1-codex.md` (1 BLOCKER, 5 Major, 1 Minor) and
`docs/reviews/claude/goal-node-tree-plan-r1-claude.md` (F1–F3 Major, F4–F5 Minor; here CM1–CM3, Cm1–Cm2).
Severity mapped BLOCKER → Blocking, Major → Medium, Minor → Low.

Every finding was re-derived against the files at `9b03ee6b` before acting; each proposed fix was treated
as a hypothesis and checked against the symbols it names. No spec decision was changed, so nothing is
ESCALATE. The bare `#<slug>` ids spec §3.5 requires are kept.

## Findings

| id | half | Verified? — evidence | Action |
|---|---|---|---|
| XB1 | codex | YES. Tasks 18–19 emitted cross-view links whose targets (`goal-<slug>` on the other pages) only exist after Task 20; CI's `check-page-links.py --build --ci` runs `dangling` over the built `/goals` and `/features`, so those commits go red | FIXED: Tasks 18–20 emit ids only (`key_link` dropped from their Consumes; links behaviours and cases replaced by id cases); Task 21 now adds every heading's two links, with `links:` cases per generator, a link-drop mutation and a Step 4 of `--sources`, `--build --ci` and the local `--build`. *Global Constraints* states the S4 order |
| XM1 | codex | YES. `blocks` is additions only: `_added` raises `Refuse` on an edited base line in a hunk, `_blocks` splits only at `## `, and `postcondition` P1 ejects an identical addition on both sides. The plan's "it lands once" and "edit + addition both survive" were not what the policy does | FIXED: Task 16 adopts `blocks` unchanged and states the consequences; rows 2, 3a, 3b, 4 restated (identical addition EJECTS; distant edit survives via `postcondition`; in-hunk edit `Refuse`); no `resolve_hunk`/`postcondition` change, STOP-and-notify if one is needed. C7 rewritten |
| XM2 | codex | YES. `resolve_text(path, text)` dispatches on `UNION_FILES.get(path)`; cases calling `resolve_hunk("blocks", …)` directly would not redden when the entry is removed | FIXED: Task 16 row 7 and case `features union: dispatch is by path`; every resolving case goes through `resolve_text("docs/features.md", …)`; the entry-removed mutation's `expect` names the dispatch case |
| XM3 | codex | YES. `scripts/check-fixture-variation.py` pins `gen-goals-page parse_registry.text` in `EXAMINED_KEYS`; Task 8 removed the parameter and Task 10 unpinned it, so Task 8's commit was red | FIXED: W5 row says the pin moves in the same task and commit, naming the three known pins; Task 8 Files gains the unpin; Task 10 becomes "verify (no edit)"; Task 7 Files gains the `check_cross.anchors_declared` unpin |
| XM4 | codex | YES. `regen-pages.py:fresh` builds from a fresh `origin/master` clone, so it never sees the slice's generators | FIXED: Tasks 8, 18, 19 and 21 Step 4 run this checkout's generators (`gen-*-page.py --out "$(mktemp -d)/…"`) and `check-page-links.py --build --ci`; Task 8's FAILS IF reworded; *Global Constraints* says never `regen-pages.py` |
| XM5 | codex | YES. Spec §3.5 keeps the bare `<slug>` id for one release; the plan's C8 kept only `f-<slug>` (what `page_markup.feature_id` emits) | FIXED: Task 17 `second_ids` on `/features` returns the bare `<slug>` AND `f-<slug>`, plus `goal-<was>`; a slug equal to a chrome id (e.g. `chrome-theme`, the reason `frag_id` took the `f-` prefix) gets no bare id; two new cases and two mutations; Task 18 behaviour 8 asserts `#dev-speed` and `#f-dev-speed` land. C8 rewritten |
| Xm1 | codex | YES. After S2, `## GOAL dev-speed-first` in `docs/goal-threads.md` is a structured use that Task 11's search would call a defect, with no stated exception | FIXED: Task 11 Step 3 lists five classes; class 5 is the one bounded S2 exception (that heading only, owned by Task 13), with a grep that must print exactly one line; FAILS IF extended |
| CM1 | claude | YES. No parser in `scripts/` reads a parenthesised list; C1 invented the grammar | FIXED: C1 and Task 1 use bare comma lists (`adrs: 0001, 0005`, `was: a, b`); `(` or `)` refused; behaviour 2 and the case renamed `grammar: adrs and was are bare comma lists`; every parenthesised literal in the plan converted |
| CM2 | claude | YES. Task 2's `absent` rule did not say whether `adrs` or an anchored document counts as built evidence; live `docs/features.md` nodes carry `adrs:` without `areas:` | FIXED: Task 2 behaviours 13–15 (absent with adrs passes; absent with an anchored document passes; absent with an area refused), a paragraph on the two counts (spec row 4.45), new cases, two mutations, FAILS IF extended |
| CM3 | claude | YES. Renaming `harness-speed` in place changes the heading level and re-parents its five following siblings | FIXED: Task 5 row 4.24 MOVES the block to a `###` after `guard-soundness`, naming the five siblings; FAILS IF gains a parent diff against `origin/master` via `parse_features`. Task 12 gets the same move rule and a parent diff with an allowed list |
| Cm1 | claude | YES. The summary line counted stateless nodes as "declared absent" | FIXED: Task 2 produces `summary_line(nodes)`; behaviour 16 `(1 built, 1 absent, 1 stateless)` with its case |
| Cm2 | claude | YES. G9 read `docs/goal-threads.md` unconditionally, so a missing file made `check-features.py` CANNOT RUN with no `done:` anywhere | FIXED: Task 3 behaviours 6 and 8 — the read happens only when some node carries `done:`; case `G9: no done line needs no threads file` with a reader that raises if called; a mutation removes the guard |

## Gates run on the folded plan

`check-docs.py`, `check-anchors.py`, `check-plan-file-tags.py`, `check-plan-task-order.py` (this plan: 22 tasks
produce, 22 consume, no forward references), `check-doc-citations.py --base origin/master` (re-run after
staging) and `check-reference-namespace.py --base origin/master`: all exit 0.
