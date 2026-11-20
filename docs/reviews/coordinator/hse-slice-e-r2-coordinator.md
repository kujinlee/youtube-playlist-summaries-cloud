# Round 2 — `hse-slice-e` — coordinator — NOT CONVERGED (Codex half)

Codex (`docs/reviews/codex/hse-slice-e-r2-codex.md`) reviewed `137fa059`, the round 1 fold (`a0afc60d`, `137fa059`) of plan Tasks 13-15. It refuted none of the round 1 folds: the 33 matrix rows agree with the sidecar, the regrades loosen no pass condition, the tier-B count of 16 `RunRecord`s holds, backlog #674/#675 are accurate, and the new cost-table row follows the convention for a new target. One MINOR, caused by the round 1 fold.

REVIEW GAP: claude — alternation (rounds 2+ run one half; round 3 is the Claude half).

```yaml
round: 2
fixes_nontrivial: false
subject: hse-slice-e
halves:
  codex: ran
  claude: gap
findings:
  - {id: Xm1, severity: Medium, aim: instrument, fix_induced: true, component: mkt-seed-repo, disposition: fixed}
```

| Id | Finding | Fold |
|---|---|---|
| Xm1 | the new case `every typed fact is what the committed file it names says` ignores each fact's `source` and parses hard-coded paths, so `roadmap-status` re-pointed at `README.md` left 13/13 green | the case now also requires each fact's `source` to name the file its answer was parsed from, written as an independent literal map (`parsed_from`). Control on a scratch copy: the `README.md` source → `[FAIL] … got ['roadmap-status']`, 12/13; the real code 13/13. New mutation `a typed fact names the wrong source file` (manifest 7 → 8, `expected_mutations.py` pin 8); `--mutate . --only scripts/mkt_seed_repo.py` on a scratch worktree: 8 mutations, 8 killed, 0 survivors |
