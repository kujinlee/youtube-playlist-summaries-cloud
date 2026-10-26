# Round 8 — `merge-when-ready-rule` — coordinator — ❌ NOT CONVERGED (1 High, 2 Medium, all HONEST)

```yaml
round: 8
fixes_nontrivial: true
subject: merge-when-ready-rule
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XH1, severity: High, aim: deliverable, fix_induced: false, component: detector-scope, disposition: fixed}
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: detector-scope, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: false, component: detector-scope, disposition: declined}
```

REVIEW GAP: claude — round 8 alternates to the Codex half on the final tree (`review-method.md`, *The
protocol*, step 4; backlog #339).

`X` = Codex half, final tree `84c2b95e`, classified each finding HONEST/ADVERSARIAL as the stop rule asked:
all three HONEST, so the adversarial-only stop rule did not apply. 185/185; mutations 67/68 via named
assertions (#54 surfaced an `IndexError` in Codex's in-memory run; the harness attributes it — 68/68); replay
8 of 40, 313 calls, zero collection errors.

**Hunk ownership drew no finding** and is closed (decision log `defer`, held). The findings are DETECTOR SCOPE.
On the owner's card (A, r8):
- **XH1 FIXED:** a weakened helper module the gate imports — `GATE_CODE` is now every `scripts/*.py|sh`, not
  only `check-*`. Measured cost: 8 -> 9 of the last 40 merged PRs.
- **XM1 FIXED:** `sys.exit(3) -> 0` — `FAIL_PATH` counts any status 1-9 for `return`, `exit` and `sys.exit`.
- **XM2 DECLINED as a stated bound:** a condition removed 7 lines above its loop's `return 1` is a SEMANTIC
  loosening with no failure-path text in the window. The bound comment now says the detector is SYNTACTIC
  and review is the primary protection, and a case asserts the bound (if it goes red, the bound closed).
  The detector-scope bet for round 9 pre-commits that honest SEMANTIC findings of this kind are bounds too.

191 cases; mutations 68 -> 71 (one anchor rebound to `[1-9]`, three added), 71/71; replay 9 of 40.
