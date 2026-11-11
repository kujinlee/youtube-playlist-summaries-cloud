# Round 2 — `ci-time-limits` — coordinator — ❌ NOT CONVERGED (1 Medium)

```yaml
round: 2
fixes_nontrivial: true
subject: ci-time-limits
halves:
  codex: ran
  claude: "GAP: alternation (one-half-per-round reading; backlog #339, NEEDS-OWNER)"
findings: [timeout-without-kill-after]
```

REVIEW GAP: claude — alternation under the reading this repository uses; backlog #339 asks the owner which governs.

Codex re-ran the harness (lock held, download hang, install hang, healthy: each named the right phase), confirmed
the 12-shard partition (2,003 mutations, each exactly once) and the guards. One Medium: `timeout` sends SIGTERM
with no kill deadline, so a SIGTERM-resistant process defeats the bound and the step cap can cut the step before
the diagnostics print (reproduced). Not fold-induced — the round-1 version used `timeout` the same way.
Disposition: FIX — `--kill-after=10` on every operation, exit 137 classified and phase-named, budget
3×(130+160)+190 = 1,060 s inside a 20-minute step cap (140 s left for diagnostics); 12 cases on ubuntu:26.04
with real sudo-rs incl. SIGTERM ignored in download and install. FOLD: implementer subagent (`dfccc2b1`).
Round 3: a fresh Claude half.
