# Round 1 — `hook-args-shell` — coordinator — ⟳ NOT CONVERGED (both halves); ACCRETE

```yaml
round: 1
fixes_nontrivial: true
subject: hook-args-shell
halves:
  codex: ran
  claude: ran
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: field-policy, disposition: fixed}
  - {id: XL1, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: false, component: field-policy, disposition: fixed}
  - {id: CM2, severity: Medium, aim: deliverable, fix_induced: false, component: walk, disposition: fixed}
  - {id: CL1, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: CL2, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: CL3, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

`X` = Codex, `C` = Claude, both on `6120318e`, both against the installed Claude Code 2.1.309's schema text (neither ran a
hook end to end). Both: 33/33; 19/19 mutations killed by their named cases; malformed structures are CANNOT RUN; the
override scan never runs on a structure `hook_commands` rejected; non-command hooks stay accepted.

- **XM1 = CM1 (fixed):** `timeout`, `async`, `asyncRewake`, `if`, `once`, `onFailure`, `cloud` all passed. Claude's half
  sharpened it: on the live push gate, `async`/`once` make it LOOK as though it ran while it does not gate — worse than
  `args`. Now `FIELD_POLICY`, deny by default: refused `args`, `shell`, `async`, `asyncRewake`, `once`; any UNCLASSIFIED
  field refused; accepted the five in live use (`type`, `command`, `statusMessage`, `timeout` ×1, `if` ×3), with the bound
  that `timeout`/`if` values and a group's `matcher` are not checked — refusing them would be red from birth (#56).
- **CM2 (fixed):** a SECOND walk of the hooks block; `continue→break`, first-group-only and first-event-only regressions
  passed the suite. Now ONE `_walk()` serves `hook_commands` and `field_problems`, and a case puts the field in a second
  event, second group, after a non-command hook; a first-group-only mutation of the walk is killed by it.
- **XL1 = CL1 (fixed):** refusing `shell: "bash"` (the default) is a POLICY, now described as one; the row's Fix column
  said "other than the default" and now notes it shipped stricter.
- **CL2 (fixed):** the "INDEPENDENT copy of the schema's types" comment had drifted above the new loop; restored.
- **CL3 (fixed):** the dashboard entry sat under a `2026-10-26` heading — a hard-coded fallback in the local merge helper,
  which now uses today's date.

The fold's own first attempt crashed two #365 mutations (`h["type"]` where the old code had `.get`, and pure cases that
raised inside their arguments) — fixed before any push; the sweep went from 23/25 attributed to 25/25.
Route ACCRETE (decision-log row written before round 2). 38 cases; 25 mutations, each killed by its named case.
