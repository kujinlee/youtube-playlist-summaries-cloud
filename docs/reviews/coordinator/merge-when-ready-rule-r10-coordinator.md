# Round 10 — `merge-when-ready-rule` — coordinator — ❌ NOT CONVERGED (1 Medium) — DEFER, CONFIRMATION ROUND NEXT

```yaml
round: 10
fixes_nontrivial: true
subject: merge-when-ready-rule
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: detector-scope, disposition: fixed}
```

REVIEW GAP: claude — round 10 alternates to the Codex half on the final tree (`review-method.md`, *The
protocol*, step 4; backlog #339).

`X` = Codex half, final tree `e83086d7`. 196/196; 72/73 mutations via named assertions in its own runner —
#54 made `main()` raise `IndexError` on a malformed list (the harness attributes it, but a crash is a
defect: fixed below). Replay sample: 3 HOLD / 7 READY, zero collection errors.

- **XM1 FIXED (HONEST-SYNTACTIC):** `sys.exit("invalid input")` -> `print(...)` was unseen; `FAIL_PATH` now counts
  `sys.exit(` with ANY argument except `0`, `None` or nothing (cases for all three negatives).
- **Hardening:** `main()` turns ANY collection error into CANNOT RUN (was `PathsDisagree` only), with a `main()`
  case on a malformed `ls-tree` reply that catches a crash itself, so a narrowed handler reads as a red case.

Decision log: detector scope's split bet LOST; next is **DEFER** (owner AFK, "apply your own
recommendation"): round 11 is a CONFIRMATION round — any further finding is FILED, not folded, and the loop
ends at r11. 199 cases; mutations 73 -> 75 (one rebound, two added), 75/75; replay 10 of 40.
