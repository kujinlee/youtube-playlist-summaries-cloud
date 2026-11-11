# Round 4 — `ci-time-limits` — coordinator — ❌ NOT CONVERGED (1 Medium, message text)

```yaml
round: 4
fixes_nontrivial: false
subject: ci-time-limits
halves:
  codex: ran
  claude: "GAP: alternation (one-half-per-round reading; backlog #339, NEEDS-OWNER)"
findings: [exit137-overclaims-cause]
```

REVIEW GAP: claude — alternation under the reading this repository uses; backlog #339 asks the owner which governs.

Codex re-ran round 3's cases (M1 now names the 30 s timeout on all three attempts; M2 recovers after the pause;
healthy 30 s; held-lock, download-hang and install-hang all fail closed and name the phase) and the 12-shard
partition. One Medium: exit 137 still claimed a cause — "ignored SIGTERM at its bound and was SIGKILLed" — that
the status cannot establish (a process SIGKILLed for any other reason gives 137; reproduced with `kill -KILL $$`).
Disposition: FIX, text only — the 137 message and its comment now say "terminated by SIGKILL; the status alone
does not establish whether the bound and kill grace expired", and backlog #343 likewise. The step still fails
closed. FOLD: coordinator; round 5 (a fresh Claude half) reviews the final tree because `ci.yml` changed.
