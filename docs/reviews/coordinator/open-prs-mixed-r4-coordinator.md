# Round 4 — `open-prs-mixed` (backlog #518) — coordinator — CONVERGED

REVIEW GAP: claude — a capped confirmation of a mechanical manifest repair; the Codex half checked every anchor. Codex: `docs/reviews/codex/open-prs-mixed-r4-codex.md`, on `422cb386`.

```yaml
round: 4
fixes_nontrivial: true
subject: open-prs-mixed
halves:
  codex: ran
  claude: gap
findings: []
```

Round 3 approved a merge resolution that took master's copy of four mutation entries this branch had re-bound; CI's sweep then
refused three anchors as NOT FOUND (run 42203002896). Repaired by a per-entry three-way merge. Codex checked all 300 entries and 305
anchors (each occurs exactly once), found nothing lost, duplicated or taken from the wrong side; 310/310. The lesson: after merging a
manifest, check EVERY anchor, not the new entries — round 3 and my spot check both looked only at the new ones.
