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

## Fold

Folded by Claude (Fable) on `f0527646`. **All 11 findings fixed; none declined**, so the YAML dispositions above
stand. Each case below was written from the reviewer's concrete input and seen red on the pre-fold code before its
fix; each also has a mutation that re-creates the red (`scripts/mutations/check-shipping-sets.json`, 106 → 159;
`scripts/mutations/mkt_stage.json`, 95 → 96).

| Id | What changed | The case that witnesses it (`check-shipping-sets.py --self-test` unless said) |
|---|---|---|
| CB1 | A Python reader (`_Loads`, an AST walk) counts a sibling loaded BY PATH as an edge: `spec_from_file_location`, `SourceFileLoader`, `runpy.run_path`, `import_module`/`__import__`, an interpreter's argv in `subprocess`, through a module constant, a local wrapper, or a table of sibling names. The map gained 10 components (libraries that shipped entry points load by path — for `comprehensibility`: `session-state`, `gen-work-lines`, `check-dashboard-entry`, `check-goal-status`, `check-features`, `check-docs`, `check-anchors`; `check-rc-contract` and `check-ratchet-contract` for `recall`; `sweep-red-alert` for `ci-layer`), 35 → 45; the `session-state.py` governance exclusion is removed. The declaration was regenerated by `mkt_stage.py --declare`, not edited. | "CB1: a sibling loaded by path is an executable edge — …"; "CB1: a generator that loads its gate at import time, and a declaration without the gate → closure red" with its adjacent negative; "CB1: the live tree — each of the six shipped entry points has an edge to the sibling it loads by path" |
| XM1 | The closure's roots and file lists come from the component map (`components.json` beside the declaration, or a second argument). The declaration is compared with the map before anything is walked. | "XM1: an entry point deleted from the declaration, its component dropped and the counts kept honest → red: the roots are the map's, never the declaration's own"; "XM1: a declaration with no map beside it is CANNOT RUN" |
| XM2 | `EXEC_RE` skips interpreter options, with and without a value, and accepts a versioned interpreter and `sh`. | "XM2: `python3 -u scripts/secret.py` in a mapped skill, secret.py unmapped → a map gap"; "XM2: ...and a closure gap when the declaration omits it"; the options table case with its negatives |
| XM3 | A read instruction that names no path lends its verb to the next paragraph (one paragraph, no further); a sentence may break across lines. | "XM3: `Read the following file:` with the path in the next paragraph reaches it"; "XM3: a sentence that says Follow on one line and names the path on the next reaches it"; the adjacent-negative case |
| XM4 | A channel outside `plugin` / `reusable-workflow` is CANNOT RUN, rc 2. | "XM4: a misspelled channel (`plguin`) is CANNOT RUN, rc 2 — never SKIPPED as a reusable workflow" |
| XM5 | A plugin package with no installed files is CANNOT RUN, rc 2. | "XM5: a plugin package with no installed files is CANNOT RUN, rc 2" |
| XM6 | A tracked candidate that is not on disk is CANNOT RUN, rc 2, and named. | "XM6: a tracked candidate missing from disk is CANNOT RUN, rc 2 — never dropped from the candidates"; "XM6: ...and candidates() names it" |
| XM7 | `declare()` walks with an `onerror` that raises; the closure's own walk does the same. | `mkt_stage.py --self-test`: "declare: a directory of the installed tree that cannot be listed is CANNOT RUN — …"; here: "XM7: an installed directory the closure cannot list is CANNOT RUN, never a tree missing what is under it" |
| CM1 | Every empty or mis-shaped input is CANNOT RUN: no packages, a list for packages, a list for the document, a non-object entry, no components, a component with no files, a channel in another case, a missing channel. With XM1, removing every skill is a gap. | the five "CM1: …" cases |
| CM2 | The agreement check IS the tie, and it needs no `claude`: per package, the declaration's components, files and channel must equal the map's, in both directions. A stale declaration is red whatever the component's role, including a data directory that gained a file. The existing CI step (`--closure`) runs it. | the eight "CM2: …" cases, among them "the map gains a component and loses one, the declaration is unchanged → both are gaps" and "a file a directory component gained since the declaration (a new memory file) is a gap" |
| Cm1 | The dashboard entry now says what the review found, that the reader has stated blind spots, and the counts the suites print. | `docs/dashboard-entries.md`, the 2026-11-16 marketplace entry |

**Decisions the next round should look at.**

- **One edge is waived in the map, not proven optional.** `optional_edges` in `components.json` holds
  `scripts/regen-pages.py` → `scripts/check-plan-code.py`: only that script's `--self-test` loads it, behind an
  existence check. The check takes the reason on trust; it does not prove the guard. The alternative was to ship the
  mutation harness inside `comprehensibility`.
- **A stale declaration is red, with no tolerance for data directories.** Measured 2026-11-16: 1 of the last 60
  commits on master adds or deletes a file under `docs/memory/`. Such a commit must re-run `mkt_stage.py --declare`,
  which needs a local `claude`.
- **`bash -c x.sh` is now an edge.** The lookahead that skipped `-c` and `-m` was removed: it protected no case and
  hid that form. `python3 -m pkg` names no file and stays unread.
- **Governance scripts newly reached by the reader** (six: `begin-plan.py`, `codex-review.py`,
  `install-git-hooks.sh`, `check-usage-pace.py`, `codex-frontier-model.py`, `check-review-rounds.py`) are excluded
  with the reason that only excluded governance scripts load them.

**Bounds — what the edge reader still does not see** (the full list is the script's docstring): a path computed at
run time; a script run with no interpreter word; `$PY x.py`; `python3 -m`; a shell command inside a Python string
(`os.system`, `shell=True`); `exec(open(…))`; interpreters other than python, bash, sh and source; YAML; a loader
reached through another module's function; an attribute or class constant; a name table mixing siblings with other
strings. Read instructions: a verb is lent to one following paragraph only.

**Verification** (the sweeps ran on a copy of the tree, with `claude` off PATH):

| Check | Result |
|---|---|
| `python3 scripts/check-shipping-sets.py --self-test` | `117/117 self-test cases passed` (was 79), rc 0 |
| `python3 scripts/mkt_stage.py --self-test` | `119/119 self-test cases passed` (was 118), rc 0 |
| `check-plan-code.py --mutate . --only scripts/check-shipping-sets.py --allow-long-local` | `OK — delivered scripts mutated: 1 file(s), 159 mutation(s), 159 killed, 159 attributed to the case each names, 0 survivor(s)`, rc 0 |
| `check-plan-code.py --mutate . --only scripts/mkt_stage.py --allow-long-local` | `OK — delivered scripts mutated: 1 file(s), 96 mutation(s), 96 killed, 96 attributed to the case each names, 0 survivor(s)`, rc 0 |
| `check-shipping-sets.py --map docs/marketplace/components.json` | `0 gaps`, rc 0 |
| `check-shipping-sets.py --closure docs/marketplace/shipping-sets.json` | `0 gaps`, rc 0 |
| `mkt_stage.py --declare` re-run after the code commit | only `measured_at` changed: the committed file lists are the derived ones |

Both sweeps are `--only` slices, which the harness calls diagnostic, not the gate: the full sweep is CI's. The
`mkt_stage.py` sweep ran before one last edit to `check-shipping-sets.py` (a duplicate seeding line in
`candidates()` removed after the first sweep found its mutation surviving); `mkt_stage.py` and its manifest did not
change after it. The first `check-shipping-sets.py` sweep had that 1 survivor; the line was removed, the mutation
re-bound to the remaining line, and the sweep re-run in full: 0 survivors.
