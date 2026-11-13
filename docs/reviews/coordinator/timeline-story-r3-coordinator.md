# Round 3 — `timeline-story` — coordinator — 1 × P2, FIXED

REVIEW GAP: claude — weekly usage at 97% (stop 98.5%). Codex: `docs/reviews/codex/timeline-story-r3-codex.md`, on `916431fb`.

```yaml
round: 3
fixes_nontrivial: false
subject: timeline-story
halves:
  codex: ran
  claude: gap
findings:
  - {id: P2, severity: Medium, aim: deliverable, fix_induced: false, component: story, disposition: fixed}
```

`changes()`'s wording-only line ("no change a reader would see …") fell through to "1 change(s)." — six times in the
real log, the fallbacks counted at r0. Now a named constant `NO_READER_CHANGE`, shared by producer and story; story says
"No change a reader would see; only the wording moved." The case drives the REAL producer; a mutation fails it by name.
