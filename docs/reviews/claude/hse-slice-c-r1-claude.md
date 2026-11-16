Reviewed head: eb52ecdd5c5d9205f65b3624e0b75831eb251027

# Marketplace slice C (plan Tasks 5-7), round 1, Claude half

Scope: `scripts/check-shipping-sets.py` (`--map`, `--closure`), `scripts/mkt_stage.py --declare`,
`docs/marketplace/{components,shipping-sets}.json`, manifests, the `ci.yml` steps, the dashboard entry.
The mandate was to refute that the checks are correct.

Baseline, measured at eb52ecdd (2026-11-16 12:25 PST):
- `python3 scripts/check-shipping-sets.py --self-test` prints `79/79 self-test cases passed`
- `python3 scripts/mkt_stage.py --self-test` prints `118/118 self-test cases passed`, plus FS ok and LIVE ok lines
- `--map docs/marketplace/components.json` prints `0 gaps`, rc 0
- `--closure docs/marketplace/shipping-sets.json` prints `0 gaps`, rc 0
- `mkt_stage.py --declare` re-run into the scratchpad reproduces the committed `packages` exactly (`packages equal: True`,
  3.9 s). The declaration is derived, not hand-shaped.

## Findings

- **BLOCKER — scripts/check-shipping-sets.py:125-157 (`import_paths`/`exec_edges`) and :327-358 (`closure_edges`):**
  a sibling loaded through `importlib.util.spec_from_file_location` is not an edge, so both checks miss
  dependencies that five of the shipped entry points load **at import time**. The plan's FAILS IF for Task 5 is met:
  a page skill invokes a file, transitively, that is in no component and no written exclusion, and the identity case
  stays green. Here is what the shipped code loads that is not declared:
  - `scripts/gen-dashboard.py:329` `with_name("check-dashboard-entry.py")`, called at module level (`_GATE = _gate_module()`, :338)
  - `scripts/gen-goals-page.py:73,99` `ROOT / "scripts" / "check-goal-status.py"`
  - `scripts/gen-features-page.py:74-81` `_load("check-features")` at module level
  - `scripts/gen-backlog-page.py:91` `check-docs.py` (`CELL_SPLIT = _cell_split()` at module level)
  - `scripts/goal-tree.py:210-214` loads `session-state.py`. That file is EXACTLY excluded with the reason
    "governance: reached from a governance hook, an excluded skill, or the prose of a data document", which is false.
    A shipped entry point loads it.
  - `scripts/check-surface-recall.py:322` loads `check-rc-contract.py` (recall package)

  None of `check-dashboard-entry`, `check-goal-status`, `check-docs`, `check-rc-contract` appears in
  `components.json` (grep count 0), and none is in an exclusion.
  **Input:** I materialised each plugin package from the committed declaration with the script's own `materialize`
  into the scratchpad, then ran each entry point with `--help`.
  **Observed:** `gen-dashboard.py` raised FileNotFoundError on `scripts/check-dashboard-entry.py`. `gen-goals-page.py` did the same on
  `check-goal-status.py`, `gen-features-page.py` on `check-features.py`, `gen-backlog-page.py` on `check-docs.py`,
  `goal-tree.py` on `session-state.py`, and recall's `check-surface-recall.py` on `check-rc-contract.py`. The
  same declaration gives `--closure` → `0 gaps`, rc 0, and `--map` → `0 gaps`. The docstring's BOUND (:24-28)
  covers "a path held in a Python string literal". It justifies that bound by the 153-file blow-up of treating every
  literal as an edge. But `spec_from_file_location(<literal or with_name(literal)>)` is a narrow, recognisable
  import form, and the plan's Task 7 edge list ("Python `import` of a sibling module") covers it. Without it the
  closure validates a package where 5 of its 11 `.py` entry points cannot start, and the dashboard entry's "Today it
  finds nothing missing" is false.

- **MAJOR — scripts/check-shipping-sets.py:423-451 (`closure_main`):** the closure fails open on an empty or
  malformed declaration. The plan's Global Constraint says an empty file set or an unparseable declaration is
  `CANNOT RUN`, rc 2. **Inputs and observed (each printed `0 gaps`, rc 0):** `{"packages": {}}`; `{"packages": []}`; a
  plugin entry with `"installed_files": [], "components": {}`; an entry whose channel is missing or misspelled
  (`"Plugin"`), which prints `comprehensibility: SKIPPED — reusable-workflow channel, no installed tree` (:433 treats
  every non-`plugin` value as a reusable workflow); and the real declaration with every `skills/*` file and its
  components removed (`0 gaps`, because no SKILL.md seeds the walk and an absent seed is not a gap). A declaration
  that ships no package, or a package with no skill, is reported closed.

- **MAJOR — scripts/check-shipping-sets.py:423-451, docs/marketplace/shipping-sets.json:** nothing ties the
  declaration to the map. `--closure` never reads `components.json`, and `--declare` needs `claude`, so CI cannot
  regenerate the declaration. **Input:** a copy of `components.json` that adds `scripts/check-dashboard-entry.py` as a
  comprehensibility component (the natural fix for the BLOCKER), drops the `goal-tree` component and excludes
  `scripts/goal-tree.py`. **Observed:** `--map <copy>` → `0 gaps`, rc 0, and `--closure` on the unchanged declaration
  → `0 gaps`. The map and the declaration now disagree about two files of a shipped package, and both gates are
  green. Task 6's FAILS IF ("lists a file under a `plugin` package that is not in its installed tree") is then
  undetectable after any map edit. The declaration's `measured_at` (b1532f27) already differs from the map's (80a08164),
  and no check reads either one. Two minimum checks are missing: the declaration's package set and its per-component
  ids must equal the map's plugin packages and the components each carries, and a stale declaration must be red.

- **MINOR — docs/dashboard-entries.md (the 2026-11-16 entry):** "Today it finds nothing missing" is false (see the
  BLOCKER). The entry also says `78/78 cases` for `check-shipping-sets.py`, but the suite prints
  `79/79 self-test cases passed` and the module docstring says 79.

## Checked and not refuted

- `--declare` reproduces the committed declaration byte-for-byte in `packages` (re-run, `packages equal: True`).
- The `ci-layer` entry carries no `installed_files`, and `--closure` prints its SKIPPED line.
- Both plan-named mutations are red on the real declaration: `brief-compose.py` dropped and `explainer-delivery.md` dropped.
- An unreadable map is CANNOT RUN, and an unparseable Python file is CANNOT RUN.

VERDICT: NOT CONVERGED
