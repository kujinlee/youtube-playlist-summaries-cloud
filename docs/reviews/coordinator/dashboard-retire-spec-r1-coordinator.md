# Round 1 — `dashboard-retire-spec` — coordinator — ⟳ NOT CONVERGED (both halves); 17 fixed, 0 rejected; §7 decided by the owner

```yaml
round: 1
fixes_nontrivial: true
subject: dashboard-retire-spec
halves:
  codex: ran
  claude: ran
findings:
  - {id: XB1, severity: Blocking, aim: deliverable, fix_induced: false, component: migration-slices, disposition: fixed}
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: store-gate, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: false, component: goal-tree-view, disposition: fixed}
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: false, component: store-gate, disposition: fixed}
  - {id: Xm1, severity: Low, aim: deliverable, fix_induced: false, component: retired-reference-gate, disposition: fixed}
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: false, component: store-gate, disposition: fixed}
  - {id: CM2, severity: Medium, aim: deliverable, fix_induced: false, component: retired-reference-gate, disposition: fixed}
  - {id: CM3, severity: Medium, aim: deliverable, fix_induced: false, component: waiver-parser, disposition: fixed}
  - {id: CM4, severity: Medium, aim: deliverable, fix_induced: false, component: waiver-parser, disposition: fixed}
  - {id: CM5, severity: Medium, aim: deliverable, fix_induced: false, component: migration-slices, disposition: fixed}
  - {id: Cm1, severity: Low, aim: deliverable, fix_induced: false, component: inventory, disposition: fixed}
  - {id: Cm2, severity: Low, aim: deliverable, fix_induced: false, component: goal-tree-view, disposition: fixed}
  - {id: Cm3, severity: Low, aim: deliverable, fix_induced: false, component: inventory, disposition: fixed}
  - {id: Cm4, severity: Low, aim: deliverable, fix_induced: false, component: store-gate, disposition: fixed}
  - {id: Cm5, severity: Low, aim: deliverable, fix_induced: false, component: skill, disposition: fixed}
  - {id: Cm6, severity: Low, aim: deliverable, fix_induced: false, component: store-gate, disposition: fixed}
  - {id: Cm7, severity: Low, aim: deliverable, fix_induced: false, component: inventory, disposition: fixed}
```

Subject: `docs/superpowers/specs/2026-11-24-dashboard-retire-design.md` at `0487f068` (reviewed); fold at the
commit after `97e91a33`.

- Codex half: `docs/reviews/codex/dashboard-retire-spec-r1-codex.md` — 1 BLOCKER, 3 MAJOR, 1 MINOR (here XB1,
  XM1–XM3, Xm1). NOT CONVERGED.
- Claude half: `docs/reviews/claude/dashboard-retire-spec-r1-claude.md` — 5 MAJOR, 7 MINOR (here CM1–CM5,
  Cm1–Cm7). NOT CONVERGED.

**The owner's decisions are not reopened.** O1/O2 stand. §7's three questions were answered by the owner
2026-11-24 17:05–17:08 on selection cards (Q1 A, Q2 A, Q3 A) and are written into §7 as DECIDED in this fold.

**Method — what was run in the fold, not taken from a half:**
- XM1: `added_reference_errors(base, head)` on a two-entry store whose new answer is dated BEFORE its ask:
  returned `[]`; `unresolved` then still listed the ask. Codex's claim CONFIRMED.
- XM3: `header_error` on four headers: `[needs-you] [heads-up]` refused; `[heads-up] [resolved: …]`,
  `[needs-you] [resolved: …]`, a bare date all accepted. Codex's claim CONFIRMED for the heads-up + resolve case.
- Cm4: `parse_entries` skips a fenced `## Example` and makes `## Not a date` an error entry — so a parse-based
  "added" set is fence-correct.
- Cm5: `[resolved: a, b]` refused as one id (re-run).
- CM3: read `escape_diagnosis` (`scripts/check-merge-ready.py:2063`) — INVISIBLE and MISSPELLED need one marker.
- CM4: read the fixtures at `scripts/check-merge-ready.py:4171`–`:4185` (copy ONE file into `mkdtemp`) and
  `check-review-recorded.py:134` (`ROOT` from `__file__`). CONFIRMED.
- XB1/CM5: read `gen-dashboard.py:327` `_gate_module` (`with_name("check-dashboard-entry.py")`) and
  `brief-compose.py:609` `_contrast`. CONFIRMED.
- CM1's fix (K9) measured against history: over the last 80 first-parent master commits touching the store,
  15 would have been refused by a strict prefix rule (edits and mid-file inserts). Recorded in the spec as a
  deliberate tightening (after S2 a correction is a new entry), not hidden.

## Dispositions

| Finding | Severity | Disposition | Spec section changed |
|---|---|---|---|
| **XB1** S2's rename breaks `gen-dashboard.py`'s by-filename loader, and the goal-tree / compaction loaders S1 repointed | Blocking | FIXED: a by-filename loader table in §1.2; S2 repoints all five loaders in the same slice and proves it with the gen-dashboard, goal-tree, compaction-state, brief-compose and explainer-delivery self-tests green at the merge point | §1.2 new table; §4.2 new `gen-dashboard.py` S2 row; §5 S2 |
| **XM1** K2 accepts a forward reference that never resolves | Medium | FIXED: K2 tightened to "names an entry whose `_pos` is strictly earlier"; fixture: a backdated answer | §3 K2; §8 row |
| **XM2** S3 drops the only visible `decision_errors` diagnosis | Medium | FIXED: the goal tree runs `decision_errors` on each open ask and prints a warning, keeping the ask; three cases (valid, no Decide block, malformed choices) | §2.4; §5 S3 |
| **XM3** K3's predicate lets `[heads-up] [resolved: …]` through and accepts answers to narrative | Medium | FIXED: K3 over ADDED entries only; refuses no flag, any heads-up, and a resolve whose target is not an ask; allowed shapes listed; the S2 heads-up closure is an ordinary allowed shape (no exception); cases incl. mixed flags, narrative target, unchanged history | §3 K3 |
| **Xm1** K8's name grep misses links and loaders, and whole-path exclusions hide new executable references | Low | FIXED with CM2: K8 inspects executable loads and `/dashboard` links only; one allowed hit (`RETIRED_FILES`) | §3 K8 |
| **CM1** append-only unenforced; a deletion silently closes or reopens an ask | Medium | FIXED: new **K9** — merge-base entries' raws must be a prefix of HEAD's; header prose excepted; two mutations; history measurement recorded | §3 K9; §5 S2; §7 Q1; §8 row |
| **CM2** K8 fails on day one (74 files) or its exemption grows | Medium | FIXED: K8 matches executable references only (loads, hook commands, `run:` lines, mutation `file` fields, page-table keys, `key_link`/`href`); the frozen set is no longer an exemption list | §3 K8; §4.3 |
| **CM3** R4 would delete the INVISIBLE diagnosis of the real incident | Medium | FIXED: keep `escape_diagnosis`; drop only the two-marker branches; `GATE_ESCAPE` = `NO-REVIEW:` only; `ESCAPE_LOOKALIKE` narrowed | §3 R4; §4.2 merge-ready row |
| **CM4** moving `exemption_reason` into `check-review-recorded.py` breaks merge-ready's single-file fixtures | Medium | FIXED by the review's first option: `exemption_reason` STAYS in the renamed stdlib-only gate file; both consumers repointed; fixtures keep copying one file, renamed. No new module | §2.1; §4.2 rename, review-recorded, merge-ready rows; §5 S2; §7 |
| **CM5** inventory misses `check-explainer-delivery.py` `PAGE_SKILLS`, the gen-dashboard → brief-compose break, `check-publishability.py:1902`, `ci.yml:73` | Medium | FIXED for three; the `check-publishability.py:1902` point REFUTED: it is a synthetic fixture world (`:1893`), not a load of the real skill, and stays — recorded in the §4.2 grouped row | §1.2; §3 skill row and CI paragraph; §4.2 |
| **Cm1** counts 626/32 drift | Low | FIXED: frozen set stated as globs; counts marked as at `b02f0a25`, not bounds | §4 source; §4.3 |
| **Cm2** nothing marks the goal tree stale after an ask is added post-S3 | Low | FIXED: `PAGE_SOURCES["goal-tree"]` and `pages_for` gain the store | §4.2 explainer-serve, regen-pages rows |
| **Cm3** stale names after S3 (`ci.yml:968`, `check-plan-code.py:7860` case name, "four pages") | Low | FIXED: each named; the two different "four"s spelled out (`REGENERABLE` 5→4, CI-built 4→3) | §4.2 ci.yml, grouped row; §5 S3 |
| **Cm4** "added block" from `+##` lines is too loose and too strict | Low | FIXED: K1 uses the parse difference after K9's prefix | §3 K1 |
| **Cm5** the resolve grammar trap | Low | FIXED: the skill text states it; S2's closing entry uses the two-bracket form | §3 skill row; §5 S2; §7 |
| **Cm6** K1 does not refuse a needs-you without a Decide block | Low | FIXED: stated as K1's explicit bound (backlog #81, owner hold) and covered by XM2's visible warning | §2.4 |
| **Cm7** mutation bookkeeping for the moved contrast mutations | Low | FIXED: stated in the `expected_mutations.py` row; the plan computes each slice's arithmetic | §4.2 |

**Non-trivial fixes (why `fixes_nontrivial: true`):** K9 is a new check; K2 is tightened; K1 moves from the
patch to the parse; K3 is redefined; K8 changes from a grep to an executable-reference scan. Round 2 owes a
review of these.
