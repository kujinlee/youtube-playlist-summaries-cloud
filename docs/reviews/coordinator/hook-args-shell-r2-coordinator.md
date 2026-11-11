# Round 2 — `hook-args-shell` — coordinator — ⟳ NOT CONVERGED; the ACCRETE bet LOST → REDESIGN

```yaml
round: 2
fixes_nontrivial: true
subject: hook-args-shell
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: field-policy, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: true, component: tests, disposition: fixed}
  - {id: XL1, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

REVIEW GAP: claude — round 2 alternates to the Codex half (`review-method.md`, *The protocol*, step 4; backlog #339).

`X` = Codex, tree `396a7578`. HELD: all 14 command-hook schema fields read from the installed 2.1.309 binary; every
refused and unclassified one refused (`onFailure`, `rewakeMessage`, `rewakeSummary`, `cloud` as UNCLASSIFIED); the group
schema exposes only `matcher` and `hooks`; old-vs-new walk identical over 52 shapes; no structure crashed `check()`.

- **XM1 (fixed by REDESIGN):** `statusMessage: {}` passed while Claude Code refused to LOAD the settings file — "nothing in
  them is in effect, including hooks" (executed). An accepted field now carries its EXACT type (`type(v) in`, so
  `timeout: true` is refused too); wrong-typed `statusMessage`, `if` and `timeout` are refused.
- **XM2 (fixed, fold-induced):** the r1 fold's `fp()` wrapper turned a raise into one finding, and the traversal case
  counted to one — a walk rejecting every SECOND group passed 38/38. The table cases now compare the exact
  `(event, field)` list; Codex's mutation is a manifest entry and is killed. Skipping a non-list event value and skipping
  a non-string command also survived; each is now a case BESIDE a valid command, raise-safe.
- **XL1 (fixed):** "the row's falsifier is two cases" was imprecise — the row names `powershell`, the suite uses `bash`.

**The bet lost on its named failure observation (a case passing for an ambient reason), so the route escalates to
REDESIGN** (decision-log row written before round 3). 42 cases; 30 mutations, each killed by its named case.
