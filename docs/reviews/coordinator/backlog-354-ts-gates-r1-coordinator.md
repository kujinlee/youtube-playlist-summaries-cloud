# Round 1 — `backlog-354-ts-gates` — coordinator — ⟳ NOT CONVERGED (both halves); ACCRETED

```yaml
round: 1
fixes_nontrivial: true
subject: backlog-354-ts-gates
halves:
  codex: ran
  claude: ran
findings:
  - {id: XH1, severity: High, aim: deliverable, fix_induced: false, component: node-fail-path, disposition: fixed}
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: node-fail-path, disposition: fixed}
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: false, component: detector-scope, disposition: declined}
  - {id: CM2, severity: Medium, aim: deliverable, fix_induced: false, component: gate-caller, disposition: fixed}
  - {id: CL1, severity: Low, aim: deliverable, fix_induced: false, component: comment-rule, disposition: fixed}
  - {id: CL2, severity: Low, aim: deliverable, fix_induced: false, component: node-fail-path, disposition: declined}
  - {id: CL3, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

`X` = Codex, `C` = Claude; both on the first PR #402 commit. Both halves: 206/206, the
seven new mutations and three re-bound ones each red via their named cases, replay 11 of 40 confirmed.

- **XH1 (fixed):** `process.exit (1)` -> `process.exit (0)` — a space before the bracket — read READY. `\s*` allowed.
- **XM1 (fixed):** `process.exitCode === 0` matched as an assignment, a false HOLD beside a comparison. `(?!=)`.
- **CM2 (fixed):** the npm call site was unguarded — `run: npm run check:confinement` dropped from `ci.yml`, or the
  `package.json` script rewritten to `true`. `GATE_REF` += `npm run check:`, `GATE_CALLER` += `package.json`.
- **CL1 (fixed):** Node `//` and `/* */` comments were code to the comment rule — false holds only. `is_comment(node=)`.
- **CL2 (part fixed, rest declined):** `exitCode ||= 1` now read; `reject()`, `Promise.reject()`, `bad++` are the
  SYNTACTIC bound the owner ruled at merge-when-ready-rule r8, stated rather than chased.
- **CM1 (declined, STATED BOUND + asserted case):** a failure block wrapped in `/* */` ADDS lines and removes none,
  so the removal rule cannot see it — the same class as Python's `if False:`, which was always outside it. The
  dashboard sentence that overclaimed is reworded.
- **CL3 (fixed):** the last 40 merges contain no TS/JS edit, so "11 of 40" could not measure the new half; the
  400-merge replay is now quoted: 109 of 400 before and after; one PR gains a TS reason and was already held.

Route: ACCRETE (decision log row written before this fold). Round 2 is a CONFIRMATION round on the final tree.
