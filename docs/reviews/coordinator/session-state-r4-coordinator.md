# Round 4 — `session-state` — coordinator — ⟳ NOT CONVERGED (stable half); DEFER: filed, merge on READY

```yaml
round: 4
fixes_nontrivial: false
subject: session-state
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XP1, severity: High, aim: deliverable, fix_induced: true, component: ledger, disposition: filed}
  - {id: XP2, severity: Medium, aim: deliverable, fix_induced: false, component: enumeration, disposition: filed}
  - {id: XL3, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

REVIEW GAP: claude — round 4 alternates to the Codex half (`review-method.md`, *The protocol*, step 4; backlog #339).

`X` = Codex, tree `fb8ade4a`. HELD: no cross-PR attribution in any valid `gh` response (same-named branches keep their
own heads, mergeability and checks); every Unicode scalar swept with no added line; all 9 check conclusions, 6 statuses
and 5 context states classified and failing ones named; the real hook timed out at 30.18 s with "timed out" and the END
marker; a held-open stdin finished in 0.57 s; 100 PRs say MAY BE TRUNCATED; 36/36; 17/17 mutations real.

- **XP1 (High, fold-induced, FILED as backlog #369):** the r3 size cap makes an oversized ledger read as nothing, so the
  next successful `--add`/`--done` atomically replaces it with only the new entry — two recorded jobs erased, exit 0
  throughout, and the block then read "none RECORDED".
- **XP2 (Medium, FILED as backlog #369):** a `gh` element missing `statusCheckRollup` (or `{}`) reads as `NO CHECKS`,
  an affirmative claim; shown by fault injection, not observed from the real `gh`.
- **XL3 (fixed, prose):** the PR body still promised a STALE flag for a fetch the split removed, and the ledger and
  every-session claims were unqualified; the script's docstring said "nothing is ever dropped".

Route DEFER, pre-committed in the split row: findings filed, not folded. PR #410 merges on READY — it is additive
(nothing on master behaves differently) and XP1 needs a ledger past 64 KiB, a gitignored local file. The loop stops.
