# Round 3 — `agenda-499` (backlog #499 slice 1, PR #502) — coordinator — NOT CONVERGED (Codex)

```yaml
round: 3
fixes_nontrivial: true
subject: agenda-499
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: true, component: scripts/goal-tree.py, disposition: declined}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: scripts/goal-tree.py, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: false, component: scripts/goal-tree.py, disposition: fixed}
  - {id: X4, severity: Low, aim: deliverable, fix_induced: true, component: scripts/goal-tree.py, disposition: fixed}
```

REVIEW GAP: claude — budget (weekly usage 91%, new agents refused at 94.6%).

No Blocking or High. Round 3 is the last round whose findings are fixed rather than filed (review-method §0 Q4c).

- **X1 (Medium, DECLINED as a code change; the claim is narrowed):** "a step agrees with EVERY leaf naming its refs" is
  false when two leaves for one row disagree (one waits, one does not) — the tree itself then shows ⬜ and ❌. That
  claim was in MY prompt, wider than the r2 policy. The policy is ANY WAIT WINS, and Codex found no world where the
  step shows ❌ and no leaf does. `derive_agenda`'s docstring now states the bound.
- **X2 (Medium, FIXED):** a log whose last line had no newline was accepted, and the next append fused onto that line,
  which replay then refused. `_locked` writes the newline first. Case + mutation.
- **X3 (Medium, FIXED):** a record missing a field a reader indexes (e.g. an agenda with no `steps`) passed the record
  check and crashed the snapshot with `KeyError`. `_agenda_records` checks each kind's fields and types
  (`AGENDA_FIELDS`) and each step's shape, so it is MALFORMED and reaches r2's NOT READ path. The end-to-end case now
  uses exactly that record. Case + mutation.
- **X4 (Low, FIXED):** the joined waits followed declaration order; sorted. Case + mutation.

Measured after the fold: 290/290 self-test cases; 176 mutations, the 24 for backlog #499 each killed by its named case
with no crash (three cases now hold an unexpected exception as a value, so a mutant cannot crash the suite).
