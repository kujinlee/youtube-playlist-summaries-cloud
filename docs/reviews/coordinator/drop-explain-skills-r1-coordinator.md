# Round 1 — `drop-explain-skills` (PR #627) — coordinator

```yaml
round: 1
fixes_nontrivial: false
subject: drop-explain-skills
halves:
  codex: ran
  claude: ran
findings:
  - {id: R1-1, severity: Minor, aim: deliverable, fix_induced: false, component: components-map, disposition: fixed}
  - {id: R1-2, severity: Minor, aim: deliverable, fix_induced: false, component: inventory, disposition: fixed}
  - {id: F1, severity: Major, aim: deliverable, fix_induced: false, component: inventory, disposition: fixed}
  - {id: F2, severity: Minor, aim: deliverable, fix_induced: false, component: components-map, disposition: fixed}
  - {id: F3, severity: Minor, aim: deliverable, fix_induced: false, component: check-publishability, disposition: fixed}
  - {id: F4, severity: Minor, aim: deliverable, fix_induced: false, component: inventory, disposition: fixed}
  - {id: F5, severity: Minor, aim: deliverable, fix_induced: false, component: roadmap, disposition: fixed}
  - {id: F6, severity: Nit, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

Reviewed head `b5047031`. Codex: CONVERGED. Claude: NOT CONVERGED on F1 (Major), which is the same defect as Codex R1-2.

## Folds

- **F1 / R1-2 — the shared template-repository cost lost its owner.** 29 inventory rows priced "+4 h the template
  repository (shared; owned and described in skill-brief's row)", and that row is deleted. The description moves
  into `skill-explain-topic`'s row, which now owns it; the other 28 rows point there.
- **R1-1 / F2 — `components.json` said the skills "stay installed" and counted 42.** Both wrong: they are removed,
  and the map holds 43 (46 on master before the drop). The dashboard entry's `45 -> 42` is now `46 -> 43`.
- **F3** — `check-publishability.py` said 10 live-tree cases are skipped under the mutation harness; 7 remain.
- **F4** — `contract-explainer-delivery` said "five page skills"; it now says two remain (explain-topic and dashboard,
  the only SKILL.md files that cite the delivery doc), and that the measurement stands as recorded.
- **F5** — the roadmap's "Judge explain-diff in the next prune" checkbox is ticked with the owner's 11-23 decision.
- **F6** — the two regen hooks, `mkt_seed_repo.py` (re-pointed to the frozen copy in
  `scripts/fixtures/check-publishability/brief-SKILL-2f5e3f3d.md`) and two memory files no longer name the removed
  skills as current.

`fixes_nontrivial: false` — every fold is prose or a count in a data file; no executable logic changed.

## Run after the fold

`check-publishability --self-test` 177/177, `mkt_seed_repo --self-test` 14/14, `check-docs` OK, `check-inventory`
rc 3 (the D1 checkpoint CI accepts), memory index within budget.
