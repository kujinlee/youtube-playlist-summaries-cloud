# Round 3 — `usage-pace` (PR #446, backlog #399) — coordinator — NOT CONVERGED (Claude); the route moves to SPLIT

REVIEW GAP: codex — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 3
fixes_nontrivial: true
subject: usage-pace
halves:
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
  claude: ran
findings:
  - {id: C1, severity: High, aim: deliverable, fix_induced: true, component: scope, disposition: filed}
  - {id: C2, severity: Medium, aim: instrument, fix_induced: true, component: cache-read, disposition: fixed}
  - {id: C3, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
  - {id: C4, severity: Low, aim: deliverable, fix_induced: true, component: scope, disposition: fixed}
```

The Claude half reviewed `ccc5ed79`, end to end on Claude Code 2.1.309.

**What it verified:**
- the main session's `SendMessage` has no top-level `agent_id`, and a subagent's does;
- an `agent_id` the model writes into its call is dropped, so the field cannot be forged.

**What it found:**
- **C1:** a SUBAGENT can wake an idle SIBLING at 95%, and the woken sibling ran a command. The fold had stated this as a bound, but the bet's wording ("no way to wake an agent") was broader, so the bet is refuted.
- **C2:** `daemon=True → False` survives; under a stall, `main()` returns at 1 s but the process lives 30 s.
- **C3:** the docstring overstates the deadline: it holds for the function, not the hook process.
- **C4:** at REFUSE the coordinator cannot send a `shutdown_request` or a plan approval, though shutting an idle agent down SAVES usage.

**SPLIT.** Closing C1 means telling a report upward from a sideways wake by the recipient's NAME, which is the hazard round 2 refuted. So this PR ships the gate on what THIS session spends: new spawns, and wake-ups FROM the main session, which is the measured expensive case. The sibling-wake path is FILED as a backlog row. In this process subagents report upward and, under *Agent lifetime*, are short-lived, so the path is rare.

**Fold:**
- **C2:** a case runs the checker as a CHILD process and bounds its wall time, which kills the daemon mutant.
- **C3:** the docstring is corrected.
- **C4:** structured control messages (`shutdown_request`, plan approval responses) are allowed at REFUSE, because they end or unblock work rather than restart it.
