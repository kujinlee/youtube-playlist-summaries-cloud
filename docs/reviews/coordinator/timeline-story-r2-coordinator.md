# Round 2 — `timeline-story` — coordinator — 1 × P2, FIX-INDUCED, FIXED

REVIEW GAP: claude — weekly usage at 97% (stop 98.5%). Codex: `docs/reviews/codex/timeline-story-r2-codex.md`, on `c65524ac`.

```yaml
round: 2
fixes_nontrivial: true
subject: timeline-story
halves:
  codex: ran
  claude: gap
findings:
  - {id: P2, severity: Medium, aim: deliverable, fix_induced: true, component: story, disposition: fixed}
```

Round 1's fold dropped the ": " cut from the shared `ref()`; an added line ("added [rel] KEY: GLYPH detail") then kept
its state. My cases used a synthetic " · what" key the producer never emits, which masked it. Fixed: an added line's
key ends at the first ": " (a key is refs only). The new case runs the REAL `changes()` on two derived snapshots, with
a colon in the thread's text; a mutation reverting the cut fails it by name.
