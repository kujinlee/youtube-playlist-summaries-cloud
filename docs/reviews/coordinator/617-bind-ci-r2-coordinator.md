# Round 2 — `617-bind-ci` (backlog #617 part 1) — coordinator — ⟳ NOT CONVERGED; all three folded

REVIEW GAP: claude — alternation (round 2 is Codex's half; round 3 is Claude's).

```yaml
round: 2
fixes_nontrivial: true
subject: 617-bind-ci
halves:
  codex: ran
  claude: gap
findings:
  - {id: XM1, severity: Major, aim: deliverable, fix_induced: false, component: contract-parser, disposition: fixed}
  - {id: Xm2, severity: Minor, aim: deliverable, fix_induced: false, component: contract-parser, disposition: fixed}
  - {id: Xm3, severity: Minor, aim: deliverable, fix_induced: true, component: contract-parser, disposition: fixed}
```

Codex on `f40a45e5` (46/46, 34/34 re-run by the reviewer).

- **XM1** `env:` named the index, but the script could reassign it (`SHARD_INDEX=$SHARD_TOTAL` before the `grep`) — 46/46
  green while every shard wrote `shard-38.txt`. Fixed: any `VAR=` in the writing step's lines RAISES.
- **Xm2** `"…/shard-$SHARD_INDEX.txt".bak` matched. Fixed: the match must end at `.txt` (an optional closing quote, then
  whitespace, `;|&)` or end of line).
- **Xm3** (fix-induced: r1 Cm3's step scoping read only `lines[st:wi]`) an `env:` written below `run:` was a false red.
  Fixed: the whole step, to the next line at the step's indent. Pinned by a synthetic two-job workflow (ok, and red with
  `job-total`).

After: 49/49; mutation slice 37/37 killed by named cases (pin 34 → 37; the r1 step-scope mutant re-bound to `[st:end]`).
THRASHING check: one fix-induced finding in r2, none in r1 → not armed.
