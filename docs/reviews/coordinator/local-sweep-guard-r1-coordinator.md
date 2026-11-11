# Round 1 — `local-sweep-guard` — coordinator — ❌ NOT CONVERGED (2 High, 1 Medium, 4 Low)

```yaml
round: 1
fixes_nontrivial: true
subject: local-sweep-guard
halves:
  codex: skipped
  claude: ran
findings:
  - {id: CH1, severity: High, aim: deliverable, fix_induced: false, component: suite-cost, disposition: fixed}
  - {id: CH2, severity: High, aim: instrument, fix_induced: false, component: manifest-anchors, disposition: fixed}
  - {id: CM1, severity: Medium, aim: instrument, fix_induced: false, component: only-wiring, disposition: fixed}
  - {id: CL1, severity: Low, aim: deliverable, fix_induced: false, component: ci-detection, disposition: fixed}
  - {id: CL2, severity: Low, aim: deliverable, fix_induced: false, component: budget-order, disposition: fixed}
  - {id: CL3, severity: Low, aim: deliverable, fix_induced: false, component: only-help, disposition: fixed}
  - {id: CL4, severity: Low, aim: deliverable, fix_induced: false, component: dashboard-text, disposition: fixed}
```

REVIEW GAP: codex — round 1's Codex half was not run concurrently (Codex was serving another PR's rounds);
round 2 runs the Codex half on the final tree.

`C` = Claude half, on `39dfb308`/`6f9d1688`. It confirmed: CI is never refused (the only `--mutate` caller
runs on GitHub runners, which set `CI`); every whole-manifest check still runs under `--only`; `CI` and the
budget are restored on every path; all 11 new mutations die by their named case with `CI` set and unset.

- **CH1 FIXED, and the reviewer's MECHANISM was wrong while its ATTRIBUTION was right.** The new
  `main(["--mutate", …])` cases pushed `check-main-drivable --self-test` from 50s to 2m+ (past the 120s
  `SUITE_TIMEOUT`), so every CI shard's control failed. The review inferred the `globals()` rebind; passing
  the budget as a parameter left it at 209s (measured on a quiet machine). The real cost:
  `check-main-drivable` analyses each `main()` call site against its ENCLOSING function, and the call sat
  inside the long `_self_test`. One call, in a small module-level `_budget_wiring()`, driven from a table:
  **52.2s vs master 50.7s**, same machine.
- **CH2 FIXED:** four existing anchors this branch orphaned (the tally/not-measured slice lines, the refusal
  print, the reporter call) plus two of its own, REBOUND to the same mutation each. ⚠ I never ran the anchor
  check on this branch, though I ran it every round on the other one.
- **CM1 FIXED:** `main()`'s `--only` wiring now has a case on its PRINTED verdict line; three mutations added
  (slice never passed, tally line without it, `CI=false` counted as CI), each killed by its named case.
- **CL1 FIXED:** only `CI=true` is CI (an exported `CI=false` is not). **CL2 FIXED:** the budget is consulted
  only after a control proved green. **CL3 FIXED:** `--only`'s help says it takes the manifest's `file`
  form. **CL4 FIXED:** the dashboard count.

237 cases; 131 mutations (117 -> 128 -> 131), the 9 affected checked in memory over a green control.
