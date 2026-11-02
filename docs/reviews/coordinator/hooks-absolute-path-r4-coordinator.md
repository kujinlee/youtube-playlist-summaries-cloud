# Round 4 — `hooks-absolute-path` — coordinator — ⟳ NOT CONVERGED (guard half); DEFER: filed, merge on READY

```yaml
round: 4
fixes_nontrivial: false
subject: hooks-absolute-path
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: guard-rule, disposition: filed}
  - {id: XL2, severity: Low, aim: deliverable, fix_induced: false, component: guard-rule, disposition: filed}
  - {id: XL3, severity: Low, aim: deliverable, fix_induced: true, component: tests, disposition: filed}
  - {id: XL4, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

REVIEW GAP: claude — round 4 alternates to the Codex half (`review-method.md`, *The protocol*, step 4; backlog #339).

`X` = Codex, tree `872cabcc`, the true split. HELD: `.claude/` byte-identical to `origin/master` (tree
`60253417…` on both sides), so no hook behaviour changes; 13 live commands accepted; 22/22; 12/12 mutations killed by
their named cases; totals 2138 -> 2150 right; backlog #223 (PARTLY, defect not fixed) and backlog #364 accurate.

- **XM1 (FILED, backlog #365):** an entry with no `type` or an unknown one (`{}`, `"commmand"`) is skipped, not refused.
- **XL2 (FILED, backlog #365):** an `UNREGISTERED` entry with an empty reason is accepted.
- **XL3 (FILED, backlog #365):** two divergence cases still pass with the shape diagnostic suppressed, through a second
  violation (`x.sh` unregistered) — they should assert the line, not the exit code.
- **XL4 (fixed, prose):** the CI step was named for the deferred launcher; renamed. The guard's docstring now states
  what it does not check.

Route DEFER, pre-committed in the split row: findings filed, not folded. PR #409 merges on READY — the guard is
additive (a new CI check, no hook changed), so a gap in it is missing protection, not a regression.
