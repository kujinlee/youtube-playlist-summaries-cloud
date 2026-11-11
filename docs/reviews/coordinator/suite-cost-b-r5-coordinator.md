# Round 5 — `suite-cost-b` (PR #538, backlog #558) — coordinator — the merge gate's eight flagged lines, answered on the final tree

```yaml
round: 5
fixes_nontrivial: false
subject: suite-cost-b
halves:
  claude: ran
  codex: gap
findings: []
```

REVIEW GAP: codex — alternation; this round has one narrow purpose and needs a single review half.

`check-merge-ready.py --pr 538` HELD on 8 lines of `scripts/check-plan-code.py`: `run_suite`'s timeout, its test stub,
and the sweep's call and failure report. No round had answered them. The reviewed head `4a732790` is round 4's tree plus
a merge of master that touched only append-only logs and backlog row #231's status notes.

Claude (`docs/reviews/claude/suite-cost-b-r5-claude.md`) found all 8 "not a loosening":
- a suite that times out is still CANNOT RUN / NOT CHECKED (rc 2) and counts as a survivor, so a hung mutant cannot
  count as killed;
- every way the budget can stop the sweep exits 1 and names the unfinished and unreached mutants;
- every failure line master printed is still printed.

What changed is intended (backlog #558): a mutant that takes 120–600 s now gets a real verdict instead of NOT CHECKED.

Self-test: `check-plan-code` 418/418.
