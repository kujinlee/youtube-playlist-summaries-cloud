# Round 2 — `usage-pace` (PR #446, backlog #399) — coordinator — NOT CONVERGED (Codex); the route moves to REDESIGN

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 2
fixes_nontrivial: true
subject: usage-pace
halves:
  codex: ran
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: true, component: scope, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: false, component: verdict, disposition: fixed}
  - {id: X3, severity: High, aim: deliverable, fix_induced: false, component: cache-read, disposition: fixed}
  - {id: X4, severity: Low, aim: instrument, fix_induced: true, component: mutation-manifest, disposition: fixed}
```

Codex reviewed `791c4791`, the fold first.
- **X1 (fix-induced):** the wake gate exempts a message whose recipient NAME looks like the coordinator. A worker registered as `main [abcdef]` is woken through that exemption, because the installed resolver matches exact registered names first.
- **X2:** a `10**400` integer crashes `math.isfinite`, so prompt, spawn and wake all exit 1 with no verdict, and a valid weekly 95% no longer refuses.
- **X3:** a regular-file read has no time bound, so a slow disk stalls the prompt.
- **X4:** the hostile-input case never reaches five-hour validation, and a `GIT_WORK_TREE` survivor remains.
- Measured latency was 109–142 ms, not the claimed 76–94 ms. The PR states the measured figures.

**The round-1 bet is lost. X1 is the wall again:** a decision about WHO a message wakes was inferred from a NAME, which the input controls.

**Redesign:** decide by WHO IS SENDING, not by whom the message names. Claude Code gives a hook the CALLER's identity: a subagent's tool call carries agent identity fields, and the main session's does not.
- A `SendMessage` FROM a subagent is a report upward, so it is allowed.
- A `SendMessage` FROM the main session to any agent is the wake-up, and it is gated at REFUSE.
- The recipient string is never consulted.

**The other findings:**
- **X2:** numbers are parsed so that no integer can raise, and a failure in one window is that window's NOT RUN, never the whole verdict's.
- **X3:** the cache read runs under an enforceable deadline (`signal.alarm` or an equivalent), and a timeout is a loud CANNOT RUN.
- **X4:** the hostile cross-product runs against a VALID weekly 95%, plus relocation-variable cases.
