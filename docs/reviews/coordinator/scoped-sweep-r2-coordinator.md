# Round 2 — `scoped-sweep` (backlog #330, PR #496) — coordinator — NOT CONVERGED (Codex half)

```yaml
round: 2
fixes_nontrivial: true
subject: scoped-sweep
halves:
  codex: ran
  claude: skipped
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: true, component: alert, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: selector, disposition: fixed}
```

REVIEW GAP: claude — alternation (round 2 runs one half; Codex reviewed `0845887c`).

**Held (Codex):** every round-1 `fixed` finding re-run on its original input passes; undetermined diffs, harness changes,
push and schedule select FULL; empty selection still reports through the required aggregate; `issues: write` stays
confined to the aggregate job; check-plan-code 305/305, check-merge-ready 256/256.

- **X1 (fixed, induced by r1 C4's auto-close):** a green RERUN of an older master commit A closes the `sweep-red` issue
  opened by its failing descendant B — reruns keep A's SHA. Fix: the red step records the failing SHA in the issue
  (body and each comment); the green step closes an open issue ONLY when the green run's SHA equals or descends from
  every failing SHA recorded on it (`git merge-base --is-ancestor`, with enough history fetched); otherwise it comments
  that an older commit went green and leaves it open. An unreadable SHA leaves the issue open. Cases: Codex's rerun
  input stays open; a descendant green closes.
- **X2 (fixed — the coordinator's r1-fold choice was wrong):** excluding `scripts/` as a walked root drops a guard that
  really walks it: a comment `# REMEMBER_HANDOFF` appended to `scripts/check-usage-pace.py` turns
  `check-canonical-source` 28/28 → 27/28, but the selector omits it. Fix: a guard that WALKS a root (listing/globbing
  it, not merely quoting a path under it) is selected for any change under that root — `scripts/` included. Detect the
  walk structurally, fail toward MORE, and report the measured median selection before/after. Codex's input becomes a
  case on the real tree.
