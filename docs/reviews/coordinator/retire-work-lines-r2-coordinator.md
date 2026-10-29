# Round 2 — `retire-work-lines` (PR #434, backlog #389) — coordinator — NOT CONVERGED (Codex); REDESIGN retirement to identity

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 2
fixes_nontrivial: true
subject: retire-work-lines
halves:
  codex: ran
  claude: gap
findings:
  - {id: Y1, severity: High, aim: deliverable, fix_induced: true, component: public-content, disposition: fixed}
  - {id: Y2, severity: Medium, aim: deliverable, fix_induced: true, component: retirement, disposition: fixed}
  - {id: Y3, severity: Medium, aim: deliverable, fix_induced: false, component: retirement, disposition: fixed}
  - {id: Y4, severity: Medium, aim: deliverable, fix_induced: false, component: retirement, disposition: fixed}
```

Codex on `4b8dda56`. **Y1** a real plan objective survives in tracked text — the round-1 Claude review quotes
[a plan objective — redacted pending backlog #194], the `serving:` line of a gitignored plan; the scrub compared
WHOLE strings, so an excerpt passed. **Y2 (fix-induced)** a symlink NAMED `work-lines.html` pointing at a live page is
served, because the round-1 fold decides on the resolved target only. **Y3** `/WORK-LINES.html` is served on the
case-insensitive filesystem. **Y4** a symlink alias of the retired file is listed by the index. Held: round-1
reproductions, nine suites, 344 scoped mutations at their named cases, 2,500 real, the archive's claims.

**Route: REDESIGN to identity** — Y2–Y4 are the alias wall the memory-budget hook met this afternoon. A request or a
listing candidate is retired if its normalised, CASEFOLDED requested name is a retired name, OR the file it resolves to
is the SAME FILE (inode) as a retired page. Y1 needs a different instrument: a substring scan (any 6-word run of plan
text) over every added tracked line, review documents included.
