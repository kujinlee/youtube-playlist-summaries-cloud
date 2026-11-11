# Round 9 — `merge-when-ready-rule` — coordinator — ❌ NOT CONVERGED (1 High, 1 Medium, HONEST-SYNTACTIC)

```yaml
round: 9
fixes_nontrivial: true
subject: merge-when-ready-rule
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XH1, severity: High, aim: deliverable, fix_induced: false, component: detector-scope, disposition: fixed}
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: detector-scope, disposition: fixed}
```

REVIEW GAP: claude — round 9 alternates to the Codex half on the final tree (`review-method.md`, *The
protocol*, step 4; backlog #339).

`X` = Codex half, final tree `b1c980e5`, classifying HONEST-SYNTACTIC / HONEST-SEMANTIC / ADVERSARIAL as the
stop rule asked. Both findings HONEST-SYNTACTIC, so the loop continued (owner AFK: "apply your own
recommendation"). 191/191; 71/71 mutations via named assertions; replay 9 of 40, zero collection errors.

- **XH1 FIXED:** a MOVE now compares a line WITH its indentation (`rstrip`, not `strip`): `return 1` pushed under a
  new `if verbose:` is a removal, not a move. The same line at the same indentation is still a move (case).
- **XM1 FIXED:** `FAIL_PATH` takes ANY non-zero integer for `return`, `exit` and `sys.exit` (3, 10, -1), plus `raise`
  and `assert`. Measured cost 9 -> 10 of the last 40 merged PRs (adds #384).

Decision log: detector scope's accrete bet LOST; next is a SPLIT (`redesign` declared skipped: it would mean
semantic analysis, which the owner's r8 ruling excluded). 196 cases; mutations 71 -> 73 (six anchors rebound,
two added — the indentation one edits BOTH sides of the move comparison, since stripping one alone breaks
every move rather than the rule), 73/73.
