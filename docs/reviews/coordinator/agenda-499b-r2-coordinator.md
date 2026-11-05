# Round 2 — `agenda-499b` (backlog #499 slice 2, PR #503) — coordinator — NOT CONVERGED (Codex), all folded

```yaml
round: 2
fixes_nontrivial: true
subject: agenda-499b
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: scripts/goal-tree.py, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: true, component: scripts/goal-tree.py, disposition: fixed}
  - {id: X3, severity: Low, aim: deliverable, fix_induced: true, component: scripts/goal-tree.py, disposition: fixed}
```

REVIEW GAP: claude — alternation (r2 runs ONE half) and budget (weekly usage 92%, new agents refused at 94.6%).

**Why this fold is a redesign, not a third patch.** r1 patched each reader of `snap["agenda"]` where Codex found it;
r2 found the same class (a value assumed to be a dict, an identity assumed present) in the readers r1 had not
touched. Two consecutive rounds on one class in one component is the thrashing shape, so the fold removes the class:
`snap_agenda(snap)` is now the ONE reader, returning `absent` / `none` / `malformed` / `ok`, and `ok` means the id, time,
window, `change_if` and every step field a reader indexes were checked. `snap_history` does the same for
`agenda_history`. `agenda_lines`, `agenda_html`, `goal_agenda_steps` and `changes()` read only through them.

- **X1 (High, FIXED):** an older snapshot's `"agenda": true` (or `["bad"]`) crashed `changes()` and the page. Now
  MALFORMED, said by `--print` and the page, tags no goal. Cases: nine malformed shapes → `malformed`; three values
  rendered without a crash; six timeline worlds without a crash.
- **X2 (Medium, FIXED; induced by r1's fix):** a step move was emitted when either agenda lacked its identity.
  `changes()` compares steps only when BOTH sides are `ok` with the same `(id, at)`; a valid new agenda is
  "recorded", anything else says nothing about steps. Case: the six worlds above, including both-sides-missing-id.
- **X3 (Low, FIXED; induced by r1's fix):** "the next snapshot will carry one" was a promise the code does not keep.
  Removed.

Mutations: 3 anchors the redesign orphaned re-pointed, 7 new (id/time/step checks, one-side-valid comparison, history
shape check, `--print` and page silence on unreadable history). 312/312; 201 mutations; all 49 backlog #499 mutants
killed by their named case with no traceback; every anchor unique.
