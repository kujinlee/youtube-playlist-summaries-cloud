# Round 1 — `ledger-goal-505` (PR #505, backlog #505) — coordinator — NOT CONVERGED (Codex half)

REVIEW GAP: claude — weekly usage at 94% of the cap; the Codex half ran alone. Codex half:
`docs/reviews/codex/ledger-goal-505-r1-codex.md`.

```yaml
round: 1
fixes_nontrivial: true
subject: ledger-goal-505
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: false, component: ledger-threads, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: timeline, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: false, component: ledger-numbers, disposition: fixed}
```

- **X1** — two ledger entries could hang one PR under two goals. `ledger_threads` keeps the refs each ledger thread
  claims: the FIRST wins, and a later entry sharing a ref is a named problem on the page.
- **X2** — the merge hand-off (ledger `fix · PR #30` under g → tracked `side · backlog #11, PR #30` under h) logged a
  false `added` and a false `removed`. `changes` pairs a vanished LEDGER thread with an appearing tracked thread
  sharing a ref and writes ONE `declared on master` line.
- **X3** — `_ledger_numbers` read the whole `thread` string, so `depends on PR #777` attached the entry to PR #777's
  thread. It now reads the thread's STRUCTURED refs through `parse_thread_line`.

Each has a case (Codex's own reproductions) and a mutation that fails it (by hand, temp copies). 320/320; pin 211.
Codex's other checks need no work: a 234-input parser differential identical to master, messages included; 317/113/125
suites; the 8 earlier mutations; tracked order kept; extra keys survive every ledger reader; parked stays parked.
