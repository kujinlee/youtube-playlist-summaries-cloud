# Round 2 — `agenda-499` (backlog #499 slice 1, PR #502) — coordinator — NOT CONVERGED (Codex)

```yaml
round: 2
fixes_nontrivial: true
subject: agenda-499
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: true, component: scripts/goal-tree.py, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: true, component: scripts/goal-tree.py, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: true, component: scripts/goal-tree.py, disposition: fixed}
  - {id: X4, severity: Medium, aim: deliverable, fix_induced: true, component: scripts/goal-tree.py, disposition: fixed}
```

REVIEW GAP: claude — budget (weekly usage 91%, new agents refused at 94.6%) — it was the Claude half's turn by
alternation, so this round is Codex again.

All four are fix-induced: they are in the r1 fold's own code (the lent `waits`, the identity checks).

- **X1 (High, FIXED):** two declared threads naming the same refs, one waiting, made the step's answer depend on
  declaration order (the first match won). Defined policy: a step waits if ANY declared thread naming the same refs
  waits, and every distinct wait is said, joined with "; ". Cases in both declaration orders, and one with two distinct
  waits (a mutation keeping only the first now dies there).
- **X2 (High, FIXED):** refs were matched in ORDER (`backlog #2, backlog #1` missed `backlog #1, backlog #2`). Matched
  as a SET through one helper, `_refset`.
- **X3 (Medium, FIXED):** after an interrupted write (an agenda replaced with no successor) both writers still appended,
  and replay then refused the log. Both writers refuse that log first (`_open_or_refuse`) and append nothing.
- **X4 (Medium, FIXED):** a malformed agenda log took the whole snapshot down (exit 1 before the append). The snapshot is
  now logged; the agenda block reads `AGENDA — NOT READ: MALFORMED — …`; the exit code is still 1. Codex's measurement
  that the live main-checkout record already carries `id: 1` is right: it was re-recorded at 15:51 in the new format
  (the pre-fold copy is in the session scratchpad).

Codex also measured, unrefuted: the flock is held across read, validation, callback and append; four concurrent writers
produced 20 replayable agendas; a refused write leaves the bytes unchanged; exit codes 2 (missing file, a directory) and
1 (`--tick-agenda 0`, `-1`).

Measured after the fold: 287/287 self-test cases; 173 mutations, the 21 for backlog #499 each killed by its named case
with no crash; every anchor in the manifest occurs once and no two mutations share one.
