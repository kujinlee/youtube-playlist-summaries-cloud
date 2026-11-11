# Round 1 — `guards-cannot-run` (PR #440, backlog #357, backlog #331 part a) — coordinator — NOT CONVERGED (both halves)

Codex half: `docs/reviews/codex/guards-cannot-run-r1-codex.md`. Claude half: `docs/reviews/claude/guards-cannot-run-r1-claude.md`. Both reviewed `870f99ac`.

```yaml
round: 1
fixes_nontrivial: true
subject: guards-cannot-run
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: payload-path, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: false, component: ci-watched, disposition: fixed}
  - {id: X3, severity: Low, aim: instrument, fix_induced: false, component: mutation-manifest, disposition: fixed}
  - {id: M1, severity: High, aim: instrument, fix_induced: false, component: mutation-manifest, disposition: fixed}
  - {id: M2, severity: High, aim: instrument, fix_induced: false, component: mutation-manifest, disposition: fixed}
  - {id: m1, severity: Low, aim: deliverable, fix_induced: false, component: payload-path, disposition: fixed}
  - {id: m2, severity: Low, aim: deliverable, fix_induced: false, component: transcript-read, disposition: fixed}
  - {id: m3, severity: Low, aim: deliverable, fix_induced: false, component: transcript-read, disposition: filed}
  - {id: m4, severity: Low, aim: deliverable, fix_induced: false, component: transcript-read, disposition: filed}
  - {id: m5, severity: Low, aim: deliverable, fix_induced: false, component: handoff-path, disposition: fixed}
```

**Both halves agree on the shape:** the refusals are right where the suite looks, and wrong one step beside it.
- **Payload path (X1, m1):** a NUL byte, a non-string `transcript_path` and an undecodable payload still traceback into rc 1 in the three Stop-hook guards.
- **ci-watched (X2):** a row that is a dict but carries no readable status still WARNs as "CI running".
- **Mutation manifest (X3, M1, M2):** cases pass for an ambient reason (an unreadable HEAD masks the checks refusal), and `all`→`any` and a list-only refusal survive.

**Fold:**
- **Payload:** validate the payload's type and path once, at each guard's entry, and answer CANNOT RUN.
- **Rows:** refuse a row without a string `state`/`conclusion`.
- **Ambient case:** pin a readable HEAD in the checks case.
- **Survivors:** add cases that kill M1/M2's mutants and the non-list mutant over `true`, `1` and `"s"`.
- **m2:** skip an undecodable LINE as a bad JSON line is skipped, so one byte doesn't blind the whole transcript.
- **m5:** give the handoff refusal a true headline, and record the WARN→BLOCK change in the PR body.
- **Filed, not fixed (m3, m4):** partial corruption passing QUIET is backlog #331's open remainder. The pre-existing `splitlines()` record split is filed with it.

**Confirmed by Codex:** a guard's rc 2 maps to a non-blocking hook exit, so no CANNOT RUN can trap a Stop loop.
