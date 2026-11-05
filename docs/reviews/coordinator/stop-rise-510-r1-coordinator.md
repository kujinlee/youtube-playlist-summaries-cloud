# Round 1 — `stop-rise-510` (PR #508, backlog #510) — coordinator — NOT CONVERGED (Codex half)

REVIEW GAP: claude — weekly usage at 95% of the cap; the Codex half ran alone. Codex half:
`docs/reviews/codex/stop-rise-510-r1-codex.md`.

```yaml
round: 1
fixes_nontrivial: true
subject: stop-rise-510
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: false, component: rise-curve, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: mutation-manifest, disposition: fixed}
  - {id: X3, severity: Low, aim: deliverable, fix_induced: false, component: stop-prose, disposition: fixed}
```

- **X1** — a wrong DST start (`local_midnight(resets) - 24 h`) passed every case. A spring-forward case now pins the
  rise for a Mon 00:30 PDT reset: 97 at Sat 00:00 PST, 97 + 2 × 12/46.5 at Sat 12:00, 99 at Sun 23:30. That wrong start
  is a new mutation, which fails the case (temp copy).
- **X2** — `#500: the verdict ignores the computed stop` still expected the case name this PR renamed. Re-bound to the
  new name; it fails it (temp copy).
- **X3** — the hook comments, `process-checklists.md` and the `RESERVE_PER_DAY` comment said "never above 97%". Each now
  says the cap rises to 99% an hour before the reset on the last day. The owner's pace line is unchanged; it is a guide.

311/311; pin 133. Codex's other checks need no work: 245,586 sampled points stay within [97, 99] and never above the
reserve; 00:30 and 23:00 resets, both DST changes, exact start and end, and under an hour left behaved correctly; no
reader parses the changed message. The six pre-existing groups of shared find-strings ACROSS manifests are not this
change's and are not refused by the loader (it de-duplicates within one manifest).
