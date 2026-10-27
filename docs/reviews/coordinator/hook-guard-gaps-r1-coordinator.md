# Round 1 — `hook-guard-gaps` — coordinator — ⟳ NOT CONVERGED (both halves); ACCRETE

```yaml
round: 1
fixes_nontrivial: true
subject: hook-guard-gaps
halves:
  codex: ran
  claude: ran
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: known-types, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: false, component: known-types, disposition: fixed}
  - {id: XL3, severity: Low, aim: deliverable, fix_induced: false, component: registry, disposition: fixed}
  - {id: CL3, severity: Low, aim: deliverable, fix_induced: false, component: tests, disposition: fixed}
  - {id: CL5, severity: Low, aim: deliverable, fix_induced: false, component: args, disposition: filed}
```

`X` = Codex, `C` = Claude, both on `edf732e8`. Both: 25/25; 14/14 mutations killed by their named cases; the live check
green over 13 commands; r4's three probes 0/0/0 on master and 2/2/1 at head.

- **XM1 = CF1 (fixed):** `KNOWN_TYPES` held 2 of the 5 hook types in Claude Code 2.1.309's schema; `agent`, `http` and
  `mcp_tool` would have read as CANNOT RUN in CI. Now all five, with the version they were read from.
- **XM2 = CF2 (fixed):** a list or object `type` crashed with a TypeError (exit 1 — "a violation", not CANNOT RUN). The type
  must now be a string before the set test.
- **XL3 = CF4 (fixed):** a reason of `None`, `0` or `[]` passed through `str()`. It must now be a non-empty string.
- **CL3 (fixed):** removing `prompt` from the known set left every case green. A new case registers every known
  non-command type beside a canonical command and expects 0 — from an INDEPENDENT copy of the five types; the fold's
  first attempt derived the list from `KNOWN_TYPES` and the new mutation survived it.
- **CL5 (FILED as backlog #368, out of scope):** a canonical command with an `args` field (or a non-default `shell`) is
  run as an executable with no shell and launches nothing; the guard passes it.

Route ACCRETE (decision-log row written before round 2). 29 cases; 16 mutations.
