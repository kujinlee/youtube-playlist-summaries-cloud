# Round 1 — `scoped-sweep` (backlog #330, PR #496) — coordinator — NOT CONVERGED (both halves)

```yaml
round: 1
fixes_nontrivial: true
subject: scoped-sweep
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: selector-names, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: master-backstop, disposition: rebutted}
  - {id: C1, severity: Medium, aim: deliverable, fix_induced: false, component: selector-names, disposition: fixed}
  - {id: C2, severity: Medium, aim: deliverable, fix_induced: false, component: selector-dirs, disposition: fixed}
  - {id: C3, severity: Medium, aim: deliverable, fix_induced: false, component: selector-outside-tree, disposition: fixed}
  - {id: C4, severity: Medium, aim: deliverable, fix_induced: false, component: alert, disposition: fixed}
  - {id: C5, severity: Low, aim: deliverable, fix_induced: false, component: selector-names, disposition: fixed}
  - {id: C6, severity: Low, aim: deliverable, fix_induced: false, component: alert, disposition: filed}
```

Both halves on `f6c77074`. **Held (both):** every "cannot determine" path selects FULL; whole-manifest checks run in every
shard before selection; `mutation-sweep-complete` reports correctly on an empty selection; `issues: write` is scoped to the
aggregate job; the docs-only master push and the scheduled `verify` only add runs. Suites: check-plan-code 291/291,
check-merge-ready 256/256 (both halves).

**Root cause of X1/C1/C2/C3/C5 — one component:** the selector links a guard to a path only by a NAME it quotes, and four
real kinds of dependency carry no quotable name in the expected form: a hyphenated sibling loaded by bare stem
(`_sibling("gen-work-lines")`), a reader that walks a whole directory (`docs/`), a dependency installed from a lock file
(`node_modules/typescript` from `package-lock.json`), and an indirect import. Each is fixed toward MORE, the approved
direction.

- **X1 = C1 (fixed):** Codex REPRODUCED a surviving mutation — changing `gen-work-lines.py:138` lets goal-tree's mutant
  *"#389: a finished plan inside an open line is listed as owing"* survive while the selector picks 7/87 without goal-tree.
  Fix: match the extensionless stem for every script, hyphenated or not.
- **X2 (rebutted):** a pending master run replaced by the next merge (backlog #482). The newer run sweeps a tree that
  CONTAINS the replaced commit, so a defect it introduced is still swept; Claude's half (L2) reached the same reading. #482
  stays filed for the soundness record.
- **C2 (fixed):** a directory walker is selected by ANY change under the directory it walks, even when some other file
  names the changed path. `docs/memory/MEMORY.md` → 5 of 87, dropping 46 `docs/` readers.
- **C3 (fixed):** `package.json` / `package-lock.json` change → FULL (they change staged `node_modules`).
- **C4 (fixed):** nothing read the `sweep-red` issue. Fix: `session-state.py` (printed at every SessionStart) lists open
  `sweep-red` issues, and a green full sweep on master closes the open one with a comment, so a later red opens a fresh
  issue instead of commenting on a stale one.
- **C5 (fixed):** follow imports transitively (closure), so `m4_base_db.py` reaches `check-live-schema` and
  `check-catalog-coverage` through `m4_catalog`.
- **C6 (filed, not fixed):** a manually cancelled master or schedule run raises no alert. A manual cancel is a deliberate
  act by a person; filed as a note on backlog #482's row.
