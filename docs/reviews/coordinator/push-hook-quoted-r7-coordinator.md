# Round 7 — `push-hook-quoted` (PR #542, backlog #428) — coordinator — CONVERGED

REVIEW GAP: codex — alternation

```yaml
round: 7
fixes_nontrivial: false
subject: push-hook-quoted
halves:
  codex: gap
  claude: ran
findings:
  - {id: C-F1, severity: Low, aim: deliverable, fix_induced: false, component: hook-adapter, disposition: filed}
  - {id: C-F2, severity: Low, aim: deliverable, fix_induced: true, component: detector-judge, disposition: filed}
```

Claude (`docs/reviews/claude/push-hook-quoted-r7-claude.md`) reviewed `9ac8a5d6`, the round 6 fold with master
merged in. **CONVERGED — no BLOCKER.** All 18 flagged ids are answered `not a loosening`, including `2d51171ccc52`,
which round 6 had answered as a finding.

- **The one-document read.** On 43 payload files, compared with master's hook: 0 looser, 17 the same, 26 stricter.
  Every malformed form is refused: empty, multi-document, non-string, truncated, a lone surrogate. Every
  single-document form is judged as round 5 judged it, including pretty-printed, unicode, 200 KB, BOM and
  duplicate-key payloads.
- **Self-tests:** 65/65 and 352/352, the latter at load averages of about 54 and 70. The new mutation was
  hand-checked and killed.
- **The round 6 flake was not reproduced.** Both ways it can happen end in a refusal: the floor runs past its
  ≈2.5 s share, or the 3.0 s deadline expires. Shrinking the deadline to 0.62 s in a copy reproduces the exact
  symptom.
  - **Measured:** the floor takes a median of 0.113 s per call at load ≈4, and 0.285 s at ≈30.
  - **CPU load does not explain it.** The guess, unmeasured, is a multi-second stall from memory pressure.
  - **Production:** a false refusal, cleared by re-running.
  - **CI:** the same stall reddens the self-test step until it is re-run. It cannot forge a mutation kill, because no
    mutation's expected case is an "is allowed" hook case. It can only make a mutant read as surviving, which goes
    red loudly.

**Filed as backlog #581:**
- **C-F1:** the hook cases compare only allow/deny, so the reason for a mismatch is never shown. And past 2.9 s,
  `max(0.1, …)` gives the floor more time than the deadline leaves.
- **C-F2:** the new mutation is also killed by two round 5 cases. A variant that skips the floor on `&&` is killed
  only by the new case; re-key the entry to that variant.
