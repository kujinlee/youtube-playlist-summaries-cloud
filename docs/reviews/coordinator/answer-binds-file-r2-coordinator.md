# Round 2 — `answer-binds-file` (PR #543, backlog #544) — coordinator — CONVERGED

REVIEW GAP: codex — alternation

```yaml
round: 2
fixes_nontrivial: false
subject: answer-binds-file
halves:
  codex: gap
  claude: ran
findings:
  - {id: C-F1, severity: Low, aim: adjacent, fix_induced: false, component: symlink-binding, disposition: filed}
```

Claude (`docs/reviews/claude/answer-binds-file-r2-claude.md`) reviewed `f547bcee` and reports CONVERGED. The round 1
fold holds: the new real-git case goes red under the `via` mutation (363/364, only its own case), and the fold changed
no binding behaviour.

**R2-F1 (Low) — filed as backlog #577.** A gate symlink whose target the branch deletes can never clear its answers. It
FAILS CLOSED: a permanent HOLD that goes to a human, never a loosening.

**Flagged lines.** There are 7 ids. 3 are answered `not a loosening`: the test-setup lines. 4 are answered `finding:`.
Those 4 are the `review_answers` signature, its docstring, and the two lines of the flipped "any doc edit voids" case.
They ARE the change the owner approved on 2026-11-08 at 11:33 PST, card A: "do A and create explain-topic page for
that". At merge time the coordinator verifies line by line that the HOLD lists those 4 and nothing else.
