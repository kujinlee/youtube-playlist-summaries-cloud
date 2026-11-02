# Round 8 — `stalled-work` (PR #452, backlog #410) — coordinator — CONVERGED (Codex); two stale mutation expects

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 8
fixes_nontrivial: false
subject: stalled-work
halves:
  codex: ran
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings: []
```

CI's mutation sweep went red on two shards of `scripts/mutations/check-stalled-work.json`: the R2-3 whitespace entry named a case its mutant does not
turn red, and the r4 F1 isDraft entry carried a truncated case name. Both `expect`s were corrected, and every one of the 84 entries was then checked by
applying its mutant and comparing against the printed failing case names (each `expect` equals exactly one). Round 8 (Codex), scoped to the one
manifest-only commit, re-applied both mutants: each changed `expect` equals one printed case, the named cases are about their mutants, and the dropped
R2-3 expect covered nothing distinct. No findings.
