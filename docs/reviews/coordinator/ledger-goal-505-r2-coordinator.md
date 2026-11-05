# Round 2 — `ledger-goal-505` (PR #505, backlog #505) — coordinator — NOT CONVERGED (Codex half)

REVIEW GAP: claude — alternation (rounds 2+ run one half) and weekly usage at 94%. Codex half:
`docs/reviews/codex/ledger-goal-505-r2-codex.md`, on `243cf639`.

```yaml
round: 2
fixes_nontrivial: true
subject: ledger-goal-505
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: true, component: ledger-threads, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: true, component: timeline, disposition: fixed}
  - {id: X3, severity: Medium, aim: instrument, fix_induced: true, component: mutations, disposition: fixed}
  - {id: X4, severity: Low, aim: deliverable, fix_induced: false, component: timeline, disposition: fixed}
```

- **X1** (from r1's first-wins) — the winner followed FILE order, and a re-`--add` moves an entry to the end, so a
  refresh moved the thread and logged a false move. The winner is now the id that sorts first.
- **X2** (from r1's hand-off pairing) — pairing on ANY shared ref took a sibling sharing only a backlog row for the
  successor, and hid a real removal. It now pairs on the ledger thread's PR when it names one, else its backlog row.
- **X3** (from the `parse_thread_line` extraction and r1's fix) — five mutations, three of them older than this PR,
  anchored on moved lines and matched zero times. Re-anchored; a scan of all 3,687 anchors in the repo finds 0
  unresolved. My per-mutation check had run only the NEW mutations — a refactor orphans the old ones.
- **X4** — `changes` ignored `ledger_problems`; a problem appearing or clearing read as "no change". Two timeline
  lines now say it.

Cases from Codex's reproductions (324/324); 3 new mutations; all 18 mutations on this work fail their named case
(by hand, temp copies). Pin 214.
