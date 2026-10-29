# Round 4 — `retire-work-lines` (PR #434, backlog #389) — coordinator — NOT CONVERGED (Codex); DEFER: one certain fix, then stop

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 4
fixes_nontrivial: false
subject: retire-work-lines
halves:
  codex: ran
  claude: gap
findings:
  - {id: W1, severity: Medium, aim: deliverable, fix_induced: true, component: retirement, disposition: fixed}
```

Codex on `1d6091d0` (review text leak-scanned before reading: 0). **W1 (fix-induced)** `GET /alias` classifies the existing
DIRECTORY `alias/` as live, then `resolve_page()` serves the `.html` fallback `alias.html` — a hard link to the retired
page — so stale content serves; classification and serving chose DIFFERENT candidates. Held: Codex's chain and longer
ones, relative/absolute/`..` targets, 16-link live chains served, 17-link, loop and out-and-back chains refused, symlinked
directory components bounded as stated, index and `/latest` clean, leak scan 0 over 2,036 added lines, 353 scoped
mutations at their named cases, 2,509 real.

**Route: DEFER — terminal.** One certain fix: classification inspects exactly the candidate `resolve_page()` will
serve (one shared selection, preserving its unresolved path for the chain walk). Then a final-tree round and stop.
