# Round 3 — `subject-status-386` — coordinator — CONVERGED (Claude); one MINOR and one NIT filed

Claude reviewed the folds of rounds 1 and 2 on `9db23306` (`git diff 3b924595 9db23306`), on python3.12 (CI's
pin) and the default python3 (3.14.4).

What held: both self-tests pass on both interpreters (176/176, 18/18); each of the three new mutations reddens
exactly the case its `expect` names on both; the UNSHIPPED fixture catches both a mutant counting altered-only
and one counting referenced-only tables; the pin of 220 equals the manifest.

- **E1 (Claude MINOR).** The 200,000-level case checks only the shared `CANNOT RUN` prefix, so a mutant that
  swaps the parse message for the walk's survives; no manifest entry deletes the `except RecursionError` clause.
- **E2 (Claude NIT).** `subject_status.py:9` still says "Two of them exit 1" in the present tense.

Both **filed** as backlog #747 under the round cap (§0 Q4c): round 3 is the last full round, neither is a
BLOCKER, and a fold would put an unreviewed change on the converged tree.

REVIEW GAP: codex — alternation (round 3 is Claude's).

```yaml
round: 3
fixes_nontrivial: false
subject: subject-status-386
halves:
  codex: gap
  claude: ran
findings:
  - {id: E1, severity: Minor, aim: deliverable, fix_induced: true, component: check-shipping-sets, disposition: filed}
  - {id: E2, severity: Nit, aim: deliverable, fix_induced: false, component: subject_status, disposition: filed}
```

Review: `docs/reviews/claude/subject-status-386-r3-claude.md`.
