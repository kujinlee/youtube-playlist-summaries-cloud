# Round 2 — `backlog-multi-tag` — coordinator — ⟳ NOT CONVERGED (Codex); REDESIGN (shape → schema)

REVIEW GAP: claude — round 2 alternates to the Codex half alone (rounds 2+ alternate, `review-method.md` → *Round topology*).

```yaml
round: 2
fixes_nontrivial: true
subject: backlog-multi-tag
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: true, component: parser, disposition: fixed}
```

Codex on `5395a82f` (fold `133d08b1` + master merge). ⚠ The first round-2 run was briefed with a superseded fold SHA
(`747b88d8`, amended by the implementer before push) and was STOPPED before it filed anything; this is the re-run on
the real tree. **Held:** every round-1 fix, each with a reverting probe that goes red; 59/59 mutations attributed;
2325 real; the 33-row retag ledger exact with 0 closed rows; 30 distinct open suite rows (status-pages 14,
feature-map 2, explainer-pages 19) matching #381, the dashboard and the PR body; the master merge preserves rows
380/381/382, both dashboard entries, both decision-log streams and the pin.

- **X1 (fix-induced by r1's XM2 fold):** moving `check-features` onto the shared parser removed its positional read,
  and the shared parser validates the table's SHAPE (cell count) but not its SCHEMA — a header that misspells
  `Bundle` yields `bundle=""` for every row, so the gate passes where master's fails. **Route: REDESIGN** (the accrete
  bet is lost): the parser validates headers against the declared column sets, so every reader inherits the check.
