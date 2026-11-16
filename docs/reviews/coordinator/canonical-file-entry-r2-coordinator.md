# Round 2 — `canonical-file-entry` (PR #595, backlog #658) — coordinator — CONVERGED (Codex)

REVIEW GAP: claude — alternation (round 2 is Codex's turn; it raised the round-1 MAJOR on the identity case).

```yaml
round: 2
fixes_nontrivial: false
subject: canonical-file-entry
halves:
  codex: ran
  claude: gap
findings: []
```

Codex on `dc3c5a9b`. **Held:** the corrected wording is true (it quoted `_staged_root`, `check-plan-code.py:627-629`);
the separate comparison rejected all 35 tested moves, drops and duplications; all 16 mutations die by their named case;
self-test 33/33; guard OK. Noted, not a finding: classifying `HARNESS_TREE` entries by `is_file()` assumes they exist —
a missing file fails the identity case, and `check-plan-code.py` separately asserts every harness entry exists.
