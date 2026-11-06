# Round 1 — `timeline-story` — coordinator — 3 × P2, all FIXED

REVIEW GAP: claude — weekly usage at 97% (stop 98.5%). Codex: `docs/reviews/codex/timeline-story-r1-codex.md`, on `8833035d`.

```yaml
round: 1
fixes_nontrivial: true
subject: timeline-story
halves:
  codex: ran
  claude: gap
findings:
  - {id: P2a, severity: Medium, aim: deliverable, fix_induced: false, component: story, disposition: fixed}
  - {id: P2b, severity: Medium, aim: deliverable, fix_induced: false, component: story, disposition: fixed}
  - {id: P2c, severity: Medium, aim: deliverable, fix_induced: false, component: story, disposition: fixed}
```

- P2a false landings: the transition is parsed from its slot (`: A → GLYPH B — `); a landing needs A ≠ merged; a
  detail-only change is told as "detail changed". Case + mutation.
- P2b hand-off: the ref ends at " (was in the ledger"; the case runs the REAL `changes()` hand-off fixture.
- P2c plans: newly owing / no longer owing / progress are three words. Case + mutation.
