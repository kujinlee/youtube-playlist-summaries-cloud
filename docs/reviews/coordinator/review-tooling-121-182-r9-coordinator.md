# Round 9 — `review-tooling-121-182` (PR #439, backlog #121) — coordinator — CONVERGED (Codex), scoped to a tests-only fix

REVIEW GAP: claude — the final-tree round is Codex because the rounds gate reads only Codex verdicts (backlog #403).

```yaml
round: 9
fixes_nontrivial: false
subject: review-tooling-121-182
halves:
  codex: ran
  claude: "GAP: the final-tree round is Codex because the rounds gate reads only Codex verdicts (backlog #403)"
findings: []
```

After round 8 converged, CI's full mutation sweep found one SURVIVOR on Linux: the r6 clause (compare each checkout's RESOLVED `docs/reviews`) was redundant for its test's layout there, because master's verbatim lexical rule also refused it. On macOS, `/var` versus `/private/var` had hidden that.

The fix, `006cc8d7`, is tests only: a case where the checkout is reached through an ALIAS, which only the r6 clause refuses, and a guard case asserting that master's rule alone accepts it. Run by hand, the mutant reddens exactly that case on Linux (Python 3.12, docker) and on macOS.

Codex reviewed `95d778af`. It confirmed:
- the refusal logic is unchanged;
- the case cannot pass for an ambient reason;
- the merge of origin/master changed nothing under `scripts/`;
- 213/213 cases, and 71/71 mutations killed and attributed.
