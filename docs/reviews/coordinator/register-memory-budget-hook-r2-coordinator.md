# Round 2 — `register-memory-budget-hook` (PR #430) — coordinator — NOT CONVERGED (Codex); folded

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 2
fixes_nontrivial: true
subject: register-memory-budget-hook
halves:
  codex: ran
  claude: gap
findings:
  - {id: Q1, severity: Medium, aim: deliverable, fix_induced: true, component: hook, disposition: fixed}
  - {id: Q2, severity: Low, aim: deliverable, fix_induced: false, component: hook, disposition: fixed}
```

Both round-1 reproductions now fail (the harness alias reports OVER BUDGET; all 34 mutations at their named cases).
**Q1 (fix-induced)** the resolved path was discarded whenever the original ALREADY matched the index suffix, so an alias
`x/docs/memory -> B/docs/memory` measured x (NOT MEASURED) or another checkout's checker. Fixed: the resolved path is
used whenever resolution succeeded. **Q2** `$(dirname …)` and command substitution strip trailing newlines, so a
checkout named `nl<newline>` measured its sibling `nl`. Fixed: the parent walk is in Python and returns with a sentinel,
and a relative path still resolves against `$PWD` as before. Measured end to end, six inputs: lexical alias into B,
newline checkout, harness alias and B directly → OVER BUDGET; healthy sibling and `OTHER.md` → silent. Self-test 16/16.
