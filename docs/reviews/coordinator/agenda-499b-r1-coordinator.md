# Round 1 — `agenda-499b` (backlog #499 slice 2, PR #503) — coordinator — NOT CONVERGED (Codex), all folded

```yaml
round: 1
fixes_nontrivial: true
subject: agenda-499b
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: scripts/goal-tree.py, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: scripts/goal-tree.py, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: false, component: scripts/goal-tree.py, disposition: fixed}
```

REVIEW GAP: claude — budget (weekly usage 92%, new agents refused at 94.6%).

- **X1 (High, FIXED):** a frozen `states` entry with `n: []` or a non-string `state` passed the record check and
  crashed `agenda_history` / `step_glyph`. `_agenda_records` now refuses any entry that is not `{n: int, state: str}`
  (bool excluded), so it is MALFORMED where it is read — the snapshot's existing handler says it. Case + mutation.
- **X2 (Medium, FIXED):** `changes()` took an agenda's identity to be its minute, so two agendas recorded in one
  minute produced a false "step moved" line. Identity is now `(id, at)`. Case + mutation; the earlier "recorded"
  mutation was re-anchored on the line that emits it (the old anchor was the line this fix rewrote).
- **X3 (Medium, FIXED):** a snapshot with NO `agenda` key (taken before agendas existed) said "none recorded". It
  now says "not captured in this snapshot"; only an explicit `None` says none. Case + mutation.

After the fold: 308/308; 194 mutations (pin 194); all 42 backlog #499 mutants killed by their named case without a
traceback; every anchor occurs once, none shared; fixture variation OK.
