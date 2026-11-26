# Round 2 — `b731-one-tokenizer` — coordinator — Claude: CONVERGED with 2 LOW; one fixed, one accepted

REVIEW GAP: codex — alternation (rounds 2 and later run one half; round 2 is Claude's).

The Claude half reviewed head `8c2e5880`. All five self-tests passed. Its random sweeps found that round 1's fixes hold:
- 30,000 ADR texts and 2,000 ADR directories read identically on master and the branch, so L is fixed;
- over 6,000 trees, master never refuses a tree the branch passes. The 68 trees where the branch is stricter are all the declined P.

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| R2-1 | Low | `adr_anchors` restated check-anchors' ADR read. If its window fell back to the default, an ADR anchored past line 10 (live: 0013–0015) would not be read and the L loosening would return, and no case would fail. | fixed: it now calls `ca._header(text, True)`, the one ADR read. A new case puts an ADR's anchor past line 18 naming `nonexistent` (rc 1). Reading with the default window fails that case (50/51); the fix passes 51/51; the `--only` mutation slice kills 16/16. |
| R2-2 | Low | A non-UTF-8 spec or ADR made master crash (rc 1); the branch reads it with `errors="replace"` and gives rc 0. | accepted: check-anchors still crashes on the same file, so the gates as a whole stay red, and master's own document reader already reads with replacement. |

```yaml
round: 2
fixes_nontrivial: false
subject: b731-one-tokenizer
halves:
  codex: gap
  claude: ran
findings:
  - {id: R2-1, severity: Low, aim: deliverable, fix_induced: true, component: check-goal-status, disposition: fixed}
  - {id: R2-2, severity: Low, aim: deliverable, fix_induced: true, component: check-goal-status, disposition: declined}
```

Claude's review: `docs/reviews/claude/b731-one-tokenizer-r2-claude.md`.
