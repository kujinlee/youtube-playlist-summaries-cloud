# Round 4 — `idle-stop-guard` — coordinator — ⟳ NOT CONVERGED (Codex half) — one BLOCKER, fixed by removing signal (b)

Codex (`docs/reviews/codex/idle-stop-guard-r4-codex.md`) reviewed `11178c55`: 1 BLOCKER, NOT CONVERGED. Self-test
78/78 quoted. The removal audit found no remaining reader of the transcript or `.claude/paused`.

REVIEW GAP: claude — alternation (rounds 2+ run one half; Claude reviewed round 3).

```yaml
round: 4
fixes_nontrivial: true
subject: idle-stop-guard
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XB1, severity: Blocking, aim: deliverable, fix_induced: false, component: worktree-signal, disposition: fixed}
```

## Is XB1 a BLOCKER by this round's own definition?

Yes. The r4 brief defined a BLOCKER as an announcement-only first stop that exits 0 with nothing running and no
forged signal. Codex's input: a builder that FINISHED 120 s ago (its final write is real, not forged), no live
background task, CI idle, last message "Now starting backlog #657." → `main()` exit 0. That is the most common
shape of the incident the guard exists for: a completion notification arrives, the orchestrator announces the next
item, and stops. Signal (b) reads evidence that work HAPPENED as evidence that it IS HAPPENING — the same defect
r1 XM1/CM2 narrowed and could not remove, because recency cannot tell "still writing" from "just finished".

## Disposition: REMOVE signal (b), do not narrow it

- **(a) already sees a builder.** Measured 2026-11-16 05:07 (docstring, r1 CM3): a background Agent is
  `{"type": "subagent", "status": "running"}` in `background_tasks` while it runs and leaves the list when it
  finishes. Every builder this orchestrator launches is its own background task, so (b) only ever adds a builder
  that is NOT running — XB1 — or one another session owns, which is no reason for this session to stop idle.
- **Narrowing fails.** A shorter window keeps the class (a builder that finished 30 s ago); a longer settle hides
  real builders. No window separates "last write" from "finished".
- **It dissolves backlog #664** (one `touch` in a builder worktree allows a stop for ten minutes): the forgeable
  signal is the one removed. Its row is closed as dissolved.
- ⚠ **Bound kept in the docstring:** the interactive `in_process_teammate` entry is still not captured; if it stays
  `running` while idle, (a) over-allows. That over-allows; it never blocks a real builder.

Same principle as Phase 6 option D: an ALLOW reads state that says work IS running, from the harness, not a proxy.
This is round 4, so after the fold the next round files every non-BLOCKER.
