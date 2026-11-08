# Round 4 — `dirty-no-ci` (PR #539, backlog #545) — coordinator — CONVERGED on the final tree; four Lows filed

```yaml
round: 4
fixes_nontrivial: false
subject: dirty-no-ci
halves:
  claude: ran
  codex: gap
findings:
  - {id: R4-F1, severity: Low, aim: deliverable, fix_induced: true, component: stalled-work-dirty-pr, disposition: fixed}
  - {id: R4-F2, severity: Low, aim: deliverable, fix_induced: true, component: stalled-work-dirty-pr, disposition: filed}
  - {id: R4-F3, severity: Low, aim: deliverable, fix_induced: true, component: stalled-work-dirty-pr, disposition: filed}
  - {id: R4-F4, severity: Low, aim: deliverable, fix_induced: false, component: stalled-work-dirty-pr, disposition: filed}
```

REVIEW GAP: codex — alternation; this round was due to Codex, and a Claude adversarial review ran in its place. A Codex
run on this machine had just been stopped by Claude Code for low system memory (`docs/plugins.md` → the fallback for
an unavailable Codex).

This round reviews the Phase 6 fold `a6e07563` (`docs/reviews/architecture-review-2026-11-08-dirty-pr-states.md`). The
fold left the hook ONE PR state, DIRTY-NO-CI, raised only when "no `pull_request` run" was measured. Every unmeasured
read became one CLI-only UNMEASURED line.

Claude (`docs/reviews/claude/dirty-no-ci-r4-claude.md`):
- no false DIRTY-NO-CI, from crafted inputs or from 200,000 random suite pages;
- UNMEASURED cannot hide another state;
- the removals left no dangling reader, orphaned case or orphaned anchor;
- 6 of 6 spot-checked mutations are attributed by the harness's rule;
- self-test 225/225.

Dispositions:
- R4-F1 (backlog #545's status cell said both DONE and "Remaining: r4") is recording, and is corrected in this commit.
- R4-F2…F4 are FILED as backlog #569 (`review-method.md` §0 Q4c). Two are comment wording; the third is an unmeasured
  transient, which the redesign's stop rule holds back from becoming a new state.

The redesign held: no finding is in the hook's logic.
