# Round 1 — `t4-warn-pending-327` — coordinator — ❌ NOT CONVERGED (2 Medium, 6 Low)

```yaml
round: 1
fixes_nontrivial: true
subject: t4-warn-pending-327
halves:
  codex: ran
  claude: ran
findings:
  - {id: CM1, severity: Medium, aim: records, fix_induced: false, component: suspension-end, disposition: fixed}
  - {id: CM2, severity: Medium, aim: deliverable, fix_induced: false, component: cli-cases, disposition: fixed}
  - {id: XL2, severity: Low, aim: deliverable, fix_induced: false, component: cli-cases, disposition: fixed}
  - {id: XL1, severity: Low, aim: records, fix_induced: false, component: explainer-page, disposition: fixed}
  - {id: XL3, severity: Low, aim: records, fix_induced: false, component: dashboard-text, disposition: fixed}
  - {id: CL1, severity: Low, aim: deliverable, fix_induced: false, component: docstrings, disposition: fixed}
  - {id: CL2, severity: Low, aim: records, fix_induced: false, component: backlog-row, disposition: fixed}
  - {id: CL3, severity: Low, aim: records, fix_induced: false, component: backlog-row, disposition: fixed}
```

`C` = Claude half, `X` = Codex half. Both halves independently found that nothing enforces the end of the
suspension (CM1; Codex as prose) and that the CLI cases did not protect "NOT a pass" (CM2, XL2 — each removed
it in a copy and kept 274/274). Both halves confirmed by execution: PR #397's head FAILs trigger 4 at exit 1
on `[4,7,4,5,4]`; master's window is empty; nothing else reads trigger 4's severity (the CLI exit code in
`ci.yml` is the only consumer, and t9 keys on the median). Neither re-ran the full 128-entry sweep.

Dispositions:
- **CM1 FIXED by stating it, not by a mechanism:** the `main()` comment, backlog #327 and the dashboard entry now
  say the end of the suspension is MANUAL and enforced by nothing, and that #327 may restore, rewrite or
  retire trigger 4 (the old "restore" contradicted the row's own retire option). A check reading #327's status
  was considered and not built: it would couple the gate to a prose row's markers, and #327's answer may be to
  retire the scheme that check would live in.
- **CM2 / XL2 FIXED:** the two CLI cases now isolate trigger 4's OWN line (exactly one) and assert its median,
  the pinned comparator, `backlog #327`, and that it ENDS with `NOT a pass`. One mutation added (suffix loses
  `NOT a pass`). A second (suffix only, losing the numbers) was dropped because its anchor repeats an earlier
  entry's; the new line assertions cover that shape. Scoped sweep **129/129** killed, each by its named case.
- **XL1 FIXED:** the decision-ladder explainer marks trigger 4 suspended in both its code excerpt and its table;
  recomposed (the recompose also carries master's backlog #105 shim comment and a new stamp — composer output).
- **XL3 FIXED:** the dashboard gives `4, 7, 4, 5, 4` and says MEDIAN.
- **CL1 FIXED:** t4's and t9's docstrings say t4 is suspended. **CL2 FIXED:** row #327 now OPENS with the
  reopening; `roadmap-to-launch.md`'s DEFER tick notes it. **CL3 FIXED:** the bias claim now names the
  measured cause (four 6–7-round subjects closed by a deferral after `continued` fall outside the window) and
  labels the split half as an inference.

Thrashing: no finding is fix-induced; this is round 1. Next: round 2 alternates to Codex on the final tree.
