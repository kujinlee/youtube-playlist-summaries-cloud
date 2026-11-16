# Round 1 — `hse-slice-c` — coordinator — ⟳ NOT CONVERGED (both halves)

Both halves reviewed `eb52ecdd` (branch `harness-ships-elsewhere`, marketplace slice C, plan Tasks 5–7, PR #598):
Codex (`gpt-6.1-sol`, `docs/reviews/codex/hse-slice-c-r1-codex.md`, 7 MAJOR) and Claude (Opus,
`docs/reviews/claude/hse-slice-c-r1-claude.md`, 1 BLOCKER, 2 MAJOR, 1 MINOR). Both NOT CONVERGED.
Baseline both quote: `check-shipping-sets.py` 79/79, `mkt_stage.py` 118/118.

```yaml
round: 1
fixes_nontrivial: true
subject: hse-slice-c
halves:
  codex: ran
  claude: ran
findings:
  - {id: CB1, severity: Blocking, aim: deliverable, fix_induced: false, component: edge-reader, disposition: fixed}
  - {id: XM1, severity: Major, aim: deliverable, fix_induced: false, component: closure-roots, disposition: fixed}
  - {id: XM2, severity: Major, aim: deliverable, fix_induced: false, component: edge-reader, disposition: fixed}
  - {id: XM3, severity: Major, aim: deliverable, fix_induced: false, component: edge-reader, disposition: fixed}
  - {id: XM4, severity: Major, aim: deliverable, fix_induced: false, component: closure-input, disposition: fixed}
  - {id: XM5, severity: Major, aim: deliverable, fix_induced: false, component: closure-input, disposition: fixed}
  - {id: XM6, severity: Major, aim: deliverable, fix_induced: false, component: map-candidates, disposition: fixed}
  - {id: XM7, severity: Major, aim: deliverable, fix_induced: false, component: declare-walk, disposition: fixed}
  - {id: CM1, severity: Major, aim: deliverable, fix_induced: false, component: closure-input, disposition: fixed}
  - {id: CM2, severity: Major, aim: deliverable, fix_induced: false, component: map-declaration-tie, disposition: fixed}
  - {id: Cm1, severity: Minor, aim: deliverable, fix_induced: false, component: dashboard-entry, disposition: fixed}
```

## Findings, merged

| Id | Finding | Overlap |
|---|---|---|
| CB1 | a sibling loaded through `importlib.util.spec_from_file_location` is no edge; six shipped entry points fail with FileNotFoundError when materialised (gen-dashboard, gen-goals-page, gen-features-page, gen-backlog-page, goal-tree → `session-state.py`, which the map wrongly excludes as governance, recall's check-surface-recall); both gates print 0 gaps | — |
| XM1 | `--closure` takes its roots from the declaration it checks: delete an entry point and its check goes with it | — |
| XM2 | an interpreter option (`python3 -u scripts/x.py`) hides the script from both gates | edge-reader, with CB1 and XM3 |
| XM3 | a Read instruction whose path is on a later line loses its dependency | edge-reader |
| XM4 | a misspelled channel (`plguin`) is SKIPPED as reusable-workflow, 0 gaps | = CM1's "Plugin" case |
| XM5 | a plugin package with no installed files passes | = CM1's empty case |
| XM6 | a tracked candidate missing from disk is dropped from `--map` | — |
| XM7 | `declare()` swallows a permission error on a directory and derives a short `expected_count` | — |
| CM1 | `closure_main` fails open on `{"packages": {}}`, `[]`, an empty plugin, a bad channel, every skill removed — the Global Constraint wants CANNOT RUN rc 2 | XM4, XM5 |
| CM2 | nothing ties `shipping-sets.json` to `components.json`: either can change and both gates stay green; CI cannot regenerate the declaration (it needs `claude`) | — |
| Cm1 | the dashboard entry says the scan finds nothing missing (false, CB1) and 78/78 (the suite prints 79/79) | — |

**Dispositions are the fold's to confirm.** All are marked `fixed`; the fold report says which were, and any it
declines it declines with a reason here.

## The CI defects found before round 1

CI on `317a2361` failed twice, both fixed before the reviews: `check-main-drivable` D2 (`main()` not driven
over a built world, `60eebe96`) and the `--declare` case needing a real `claude` on PATH (`eb52ecdd`).
