# Round 1 — `agenda-499` (backlog #499 slice 1, PR #502) — coordinator — NOT CONVERGED (Codex)

```yaml
round: 1
fixes_nontrivial: true
subject: agenda-499
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: scripts/goal-tree.py, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: false, component: scripts/goal-tree.py, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: false, component: scripts/goal-tree.py, disposition: fixed}
  - {id: X4, severity: Medium, aim: deliverable, fix_induced: false, component: scripts/goal-tree.py, disposition: fixed}
  - {id: X5, severity: Medium, aim: deliverable, fix_induced: false, component: scripts/goal-tree.py, disposition: fixed}
  - {id: X6, severity: Low, aim: deliverable, fix_induced: false, component: scripts/goal-tree.py, disposition: fixed}
```

REVIEW GAP: claude — budget (weekly usage 91%, new agents refused at 94.6%; the Codex half does not draw on it).

- **X1 (High, FIXED): a step dropped a leaf's declared `waits`.** Row #12 with a thread `waits on PR #20` read ❌ in
  the tree and ⬜ in the agenda. `derive_agenda` now takes the declared threads and gives a step the `waits` of the
  thread naming the same refs; `main()` passes them on both the record and the snapshot path. Cases: the pure one in two
  distinct worlds, and an end-to-end one (`--print` shows the fixture's `waits on the owner (declared)` on step 2).
- **X2 (High, FIXED): replay ignored identity.** A `tick`/`replaced` before any agenda vanished; `[A, B, replaced(A)]`
  closed B; a late tick for A attached to B; two recorders could interleave. Each agenda now carries a sequence `id`,
  `tick` and `replaced` carry `of`, and `agendas()` refuses as MALFORMED an orphan, a record naming a closed or other
  agenda, an id out of sequence, and an agenda that follows an unclosed one. Read-and-append runs under one `flock`.
- **X3 (Medium, FIXED):** a missing `--record-agenda` file was a traceback; it is CANNOT RUN, exit 2.
- **X4 (Medium, FIXED):** a closed agenda could be ticked (now impossible: a tick names the open agenda, and replay
  refuses one that does not) and a step could be ticked twice (refused).
- **X5 (Medium, FIXED):** `--tick-agenda 0` fell through to the default run; the flag is tested with `is not None`.
- **X6 (Low, FIXED):** a second `window:` (or `change-if:`) line silently overwrote the first; refused.

Measured after the fold: 283/283 self-test cases; 169 mutations, of which the 17 for backlog #499 were each run by hand on
a temp copy of `scripts/` and killed by the case they name, with no crash (two cases were made to catch a refusal as a
value so a stricter guard cannot crash the suite). Three earlier anchors re-bound after the code moved.
