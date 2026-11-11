# Round 3 — `trim-always-loaded` — coordinator — fold of the Claude half

```yaml
round: 3
fixes_nontrivial: false
subject: trim-always-loaded
halves:
  codex: gap
  claude: ran
findings:
  - {id: F1, severity: Medium, aim: deliverable, fix_induced: true, component: token-claim, disposition: fixed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: true, component: token-claim, disposition: fixed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: true, component: walkthrough, disposition: fixed}
  - {id: S1, severity: Low, aim: deliverable, fix_induced: false, component: plugins-spine, disposition: fixed}
  - {id: S2, severity: Low, aim: deliverable, fix_induced: false, component: plugins-spine, disposition: fixed}
  - {id: S3, severity: Low, aim: deliverable, fix_induced: false, component: plugins-spine, disposition: fixed}
  - {id: S4, severity: Low, aim: deliverable, fix_induced: false, component: plugins-spine, disposition: fixed}
  - {id: S5, severity: Low, aim: deliverable, fix_induced: false, component: dev-process-spine, disposition: fixed}
```

REVIEW GAP: codex — alternation (round 3 is the Claude half only).

| Finding (source) | Disposition |
|---|---|
| F1 `CLAUDE.md`+`AGENTS.md` row 1,371 vs 1,367; table did not sum | FIXED re-ran `measure_trim.py` (extended with CLAUDE.md / AGENTS.md rows and the on-demand growth in `wc -c` bytes). Now 47,377 → 27,037 chars, −20,340 (−43%); every row sums; tokens 5.1k raw / 510 cached-weighted / 6.4k fresh-write; walkthrough and dashboard entry updated |
| F2 on-demand growth +17,073 / +14,423 B stale | FIXED +17,142 / +14,485 / +930 bytes (`wc -c`, labelled as bytes) |
| F3 bracketed relocation notes undeclared | FIXED walkthrough now lists THREE text changes |
| S1 bounded wait | FIXED clause in the `plugins.md` Bounded wait bullet |
| S2 re-attempt Codex before merge | FIXED clause in the Fallback paragraph |
| S3 `--verdict` retired, rc=2 | FIXED parenthetical on the rc=2 line of the exit-code block |
| S4 lagging check `handoff-XXXXXX.md` | FIXED sentence in the handoff summary |
| S5 python-pin "or is exempt with a reason" | FIXED `dev-process.md` row, same line, no line added |

Line budget: `dev-process.md` stays at 214 / 220; `plugins.md` is 166 lines.

next: r4, Codex half, BLOCKER-only per `docs/review-method.md` §0 Q4c.
