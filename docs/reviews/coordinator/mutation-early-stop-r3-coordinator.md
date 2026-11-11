# Round 3 — `mutation-early-stop` (draft PR #476, backlog #405) — coordinator — NOT CONVERGED (Claude half)

Claude half: `docs/reviews/claude/mutation-early-stop-r3-claude.md`, which reviewed `a2821eb2` (the r2 fold merged
with master).
REVIEW GAP: codex — alternation (rounds 2+ run ONE half per round, `docs/review-method.md` → *Round topology*).

```yaml
round: 3
fixes_nontrivial: true
subject: mutation-early-stop
halves:
  codex: skipped
  claude: ran
findings:
  - {id: C3-M1, severity: Medium, aim: deliverable, fix_induced: false, component: stop-rule, disposition: fixed}
  - {id: C3-L1, severity: Low, aim: deliverable, fix_induced: true, component: changed-set, disposition: fixed}
  - {id: C3-L2, severity: Low, aim: deliverable, fix_induced: false, component: changed-set, disposition: fixed}
```

**Not thrashing.** C3-L1 comes from the r1 fold, not from r2's. Only C3-L1 is fix_induced, and its cause is two rounds
back, so the arming condition (two consecutive rounds whose findings came from the previous round's fix) does not hold.

- **C3-M1: fixed.** The per-file rule forced FULL only when the changed module's name appears in the target's OWN
  source. `check-live-schema.py` and `check-catalog-coverage.py` load `m4_base_db` through `m4_catalog`. The fold
  closes the changed set first: repeat until it stops growing, with any `scripts/**/*.py` whose source names a changed
  module counting as changed.
- **C3-L1: fixed.** A local run decided from the committed diff but tested the working tree. It now returns no early
  stop when the tree is dirty, untracked files included.
- **C3-L2: fixed.** Both diff commands get `--no-renames`, so a renamed file lists its old path too. The same cause in
  `sweep_needed` (a staged file renamed into `docs/` skips the sweep) is outside this PR and is filed as its own row.
