# Round 2 — `stub-gaps-and-fg-cycle` — coordinator — ❌ NOT CONVERGED (1 Medium)

```yaml
round: 2
fixes_nontrivial: true
subject: stub-gaps-and-fg-cycle
halves:
  codex: ran
  claude: "GAP: alternation (one-half-per-round reading; backlog #339, NEEDS-OWNER)"
findings:
  - {id: M1, severity: Medium, aim: instrument, fix_induced: true, component: stub-page, disposition: fixed}
```

REVIEW GAP: claude — alternation under the reading this repository uses; backlog #339 asks the owner which governs.

Codex M1, fix-induced: the r1 fold re-read the reserve after a resize whose stimulus left the bar's box unchanged, so a
script that kept its FIRST height forever passed 233/233 — in Chromium a 44.4px reserve under a 130.6px bar at 320×568.
FIXED by changing the stimulus, not the assertion: the stub bar grows 43.109375 → 130.5625px across the resize and both
published values must follow; Codex's survivor is a manifest entry. Scoped run 112/112. Everything else held (8 entries
bound and killed, pages reproduce, six states clean, min bold 7.79:1). ⚠ Thrashing watch: fix-induced in `stub-page`.
Round 3: a fresh Claude.
