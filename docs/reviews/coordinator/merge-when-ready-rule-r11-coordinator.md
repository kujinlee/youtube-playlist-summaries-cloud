# Round 11 — `merge-when-ready-rule` — coordinator — ⏹ STOPPED (CONFIRMATION ROUND; 1 High FILED as backlog #354)

```yaml
round: 11
fixes_nontrivial: false
subject: merge-when-ready-rule
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XH1, severity: High, aim: deliverable, fix_induced: false, component: detector-scope, disposition: declined}
```

REVIEW GAP: claude — round 11 alternates to the Codex half on the final tree (`review-method.md`, *The
protocol*, step 4; backlog #339).

`X` = Codex half, final tree `444c7586`. 199/199; 75/75 mutations via named assertions, no crashes; replay 10 of 40,
313 git calls, zero collection errors; `main()` with real git reads confirmed exit 0 READY, 1 NOT READY, 2 CANNOT
RUN (an actual failed git command) and 3 HOLD; **no defect introduced by the round-10 fold**.

**XH1 — HONEST-SYNTACTIC, High:** TypeScript gates are outside `GATE_CODE` (`.py|.sh` only) and `process.exit(…)`
is outside `FAIL_PATH`, so `scripts/check-service-confinement.ts`'s `process.exit(1) -> 0` printed READY.

**DECLINED HERE and FILED as backlog #354**, as the DEFER row written BEFORE this round committed: a confirmation
round's findings are filed, not folded, and the loop stops at r11. The line was fixed in advance so that it
could not be moved after seeing a result — and this result is exactly the kind that tempts moving it: a small,
correct fix. The PR HOLDs under its own rule, so the merge is the owner's, and the owner sees #354 with it.

Over eleven rounds: r1 accreted; r2 redesigned onto one parser; r3-r4 split and deferred path identity, which
the owner reversed; r5-r7 replaced the path source with git's machine format and hunks with exact blob diffs
after three false READYs; r8-r10 widened detector scope under two pre-committed stop rules; r11 confirmed.
