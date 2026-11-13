# Round 2 — `goal-tree-recency` (backlog #497, PR #497) — coordinator — NOT CONVERGED (Codex half)

```yaml
round: 2
fixes_nontrivial: true
subject: goal-tree-recency
halves:
  codex: ran
  claude: skipped
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: true, component: bucket, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: refresh, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: false, component: goal-number, disposition: rebutted}
```

REVIEW GAP: claude — alternation (round 2 runs one half; Codex reviewed `c35f8296`).

**Held (Codex):** every round-1 `fixed` finding re-run on its original input passes; 261/261 and 231/231; clock-only
changes log nothing and each new snapshot field logs once; built pages parse with no duplicate ids or unbalanced
`<details>`; NEEDS YOU matches master.

- **X1 (fixed, induced by r1 C6):** a thread naming a PR merged 3 h ago AND an older closed PR is aggregated `closed`,
  and recency reads only `closed_at` — the recent merge is folded away. Fix: a thread is `recent` when ANY referenced
  PR merged or closed within the window, judged across all its refs independently of the aggregate state; an unread
  timestamp on any ref keeps the thread out of the fold. Codex's input becomes a case.
- **X2 (fixed):** two overlapping `/regenerate` clicks — the second waits for the lock and then gets a full 60 s of its
  own (Codex measured 79 ms / 159 ms at a 100 ms scale). Fix: take the deadline BEFORE the lock, bound the lock wait by
  it, and give the subprocess only the remainder; a click that cannot finish in time answers with the timeout, not late.
- **X3 (rebutted — documented limitation):** a goal prepended with the SAME first-request minute as an existing one
  renumbers the goals after it. Any rank computed from the file renumbers in one insertion direction on a tie; the only
  full fix is a persisted per-slug number, i.e. new state for a display aid. The owner asked for numbers "so that I can
  easily find them"; anchors are by slug and never move, equal-minute goals are rare (one owner request per goal), and
  the grammar note says which edits renumber. Not worth a new store.
