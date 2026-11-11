# Round 2 — `trim-always-loaded` — coordinator — fold of the Codex half

```yaml
round: 2
fixes_nontrivial: false
subject: trim-always-loaded
halves:
  codex: ran
  claude: gap
findings:
  - {id: C1, severity: Medium, aim: deliverable, fix_induced: true, component: token-claim, disposition: fixed}
  - {id: C2, severity: Medium, aim: deliverable, fix_induced: false, component: plugins-spine, disposition: fixed}
  - {id: C3, severity: Low, aim: deliverable, fix_induced: false, component: token-claim, disposition: fixed}
```

REVIEW GAP: claude — alternation (round 2 is Codex only; round 3 is the Claude half).

| Finding (source) | Disposition |
|---|---|
| C1 Codex M1: published totals 25,676 / 21,701 disagreed with `len()` on HEAD; plugins.md line count wrong | FIXED re-measured with a script (47,377 → 26,661, −20,716, −44%; 5,179 raw, 518 cached-weighted, 6,474 fresh-write-weighted tokens); `docs/trim-floor-walkthrough.md` table, saving paragraph and line counts, and the `docs/dashboard-entries.md` entry |
| C2 Codex M2: wrapper `--self-test` after touching it; bounded fallback (one quick check / single re-run, full file access) dropped | FIXED `docs/plugins.md` Fallback paragraph and the wrapper bullet list |
| C3 Codex L: unsupported "162 KB covered more than those files" in the unrelated entry | FIXED reworded to say the two figures are different measurements to reconcile |

Line budget: `dev-process.md` stays at 214 / 220; `plugins.md` is 166 lines.

next: r3, Claude half, with a `REVIEW GAP: codex — alternation` line.
