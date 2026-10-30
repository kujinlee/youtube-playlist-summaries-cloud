# Round 1 — `usage-pace` (PR #446, backlog #399) — coordinator — NOT CONVERGED (both halves)

Codex half: `docs/reviews/codex/usage-pace-r1-codex.md`. Claude half: `docs/reviews/claude/usage-pace-r1-claude.md`. Both reviewed `6fe44eb8`.

```yaml
round: 1
fixes_nontrivial: true
subject: usage-pace
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: verdict, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: false, component: cache-read, disposition: fixed}
  - {id: X3, severity: Low, aim: deliverable, fix_induced: false, component: verdict, disposition: fixed}
  - {id: X4, severity: Low, aim: instrument, fix_induced: false, component: display, disposition: fixed}
  - {id: M1, severity: High, aim: deliverable, fix_induced: false, component: scope, disposition: fixed}
  - {id: M2, severity: High, aim: deliverable, fix_induced: false, component: override, disposition: fixed}
  - {id: M3, severity: High, aim: deliverable, fix_induced: false, component: verdict, disposition: fixed}
  - {id: m1, severity: Low, aim: deliverable, fix_induced: false, component: override, disposition: fixed}
  - {id: m2, severity: Low, aim: instrument, fix_induced: false, component: display, disposition: fixed}
  - {id: m3, severity: Low, aim: deliverable, fix_induced: false, component: display, disposition: fixed}
  - {id: m4, severity: Low, aim: deliverable, fix_induced: false, component: hooks, disposition: fixed}
```

**Both halves confirmed:**
- the tool really is named `Agent`: 220 calls in the transcript, and the documented matcher;
- the prompt hook costs about 66–74 ms, which is acceptable;
- a broken checker cannot block.

**What they found:**
- **Verdict (X1, M3):** an unrepresentable `resets_at` crashes the time display, so a 95% reading lets the spawn through.
- **Cache read (X2):** a FIFO cache stalls every prompt, up to the 30-second hook timeout.
- **X3:** a slightly future cache reads OK.
- **Display (X4, m2, m3):** the reset time is ambiguous across a DST change, and the tests are tautological because they derive the expected text from the same formatter. A reading of 89.9999 shows as 90%.
- **Override (M2, m1):** it is printed to the agent it constrains, never expires, is not gitignored, and is not found from a worktree.
- **m4:** WARN and REFUSE reach only the model.

**M1 was a spec gap, and the OWNER decided it (2026-10-30, selection card, option A).** At 90% or more the hook ALSO gates waking an existing agent (`SendMessage`), not only new spawns. The measured cost lives there: about 70% of weighted usage, against about 4% for fresh spawns.

**Fold:**
- **Verdict:** any unrepresentable timestamp, and any cache written in the future, is CANNOT RUN.
- **Cache read:** only a regular file, opened non-blocking, under a byte bound. Switch to PR #440's shared reader once it merges.
- **Display:** the reset time carries its zone abbreviation, and the tests use fixed strings under a fixed `TZ`. The percentage is floored for display.
- **Scope:** a PreToolUse gate on `SendMessage` at REFUSE.
- **Override:** the file holds an EXPIRY (default two hours). It is gitignored and resolved from the main checkout. The model-facing denial does not describe how to bypass it; the bypass is told to the owner via `systemMessage`. WARN and REFUSE also reach the owner via `systemMessage`.
