# Round 2 — `suite-cost-a` (PR #537, backlog #231) — coordinator — Codex NOT CONVERGED; both findings folded by making overlap unable to corrupt the goal-tree sibling cache

```yaml
round: 2
fixes_nontrivial: true
subject: suite-cost-a
halves:
  claude: gap
  codex: ran
findings:
  - {id: R2-F1-codex, severity: Medium, aim: deliverable, fix_induced: true, component: goal-tree-sibling-cache, disposition: fixed}
  - {id: R2-F2-codex, severity: Medium, aim: deliverable, fix_induced: true, component: goal-tree-sibling-cache, disposition: fixed}
```

REVIEW GAP: claude — alternation

Codex ran (`docs/reviews/codex/suite-cost-a-r2-codex.md`, NOT CONVERGED). Round 2 runs one half by alternation
(`docs/review-method.md` → *Round topology*). Both findings are in `scripts/goal-tree.py`'s sibling cache, and both
were caused by round 1's fold, which recorded reads into ONE module-level list (`_SIBLING_READS`) and saved the
bytecode settings in every import.

- **Codex R2-F1 (Medium):** a sibling that calls `_sibling("B")` during its own import. B replaced the shared list and
  then set it to `None`, so A's later reads were not in A's key. Reproduced by the reviewer: cached 1, fresh 2.
- **Codex R2-F2 (Medium):** two imports overlapping in two threads. T2's read was lost, and afterwards
  `dont_write_bytecode` was still on and `pycache_prefix` named T1's deleted temporary directory, because T2 saved T1's
  temporary values as the originals. Reproduced by the reviewer with thread events.

`fix_induced`: true for both. Each is a direct consequence of the r1 fold's shared recorder. The reviewer found no
current production caller that does either.

## The fold: overlap cannot corrupt the state, rather than one patch per interleaving

One more fix-caused round in this component would be THRASHING (two consecutive rounds), so the fold removes the
shared mutable state instead of guarding each ordering:

- **One `threading.RLock`** (`_SIBLING_LOCK`), held for the whole lookup, import and record. Two threads' imports
  serialise. A sibling that calls `_sibling` during its own import is the same thread, so it re-enters.
- **A stack of read-lists** (`_SIBLING_STACK`). Each import in progress pushes its own list, and `_note_open` adds each
  opened path to EVERY list on the stack, since an outer import depends on what its inner imports read. The pop is in
  `finally`.
- **The bytecode settings are saved and restored only by the outermost import** (stack depth 0 → 1 → 0), in `finally`,
  so no import can save another's temporary values as the originals.

Why every list, and not only the innermost: a SUCCESSFUL inner import builds its key by reading its files again after
it pops, while the outer list is on top, so the outer records them either way. An inner import that FAILS builds no key,
and if the outer catches the exception its list is the only record of that read. A mutation that notes reads only in
the innermost list survived the first version of the third case, which had a successful inner import. The case now uses
a failing one, and the mutation goes red on it.

A thread that is not importing but opens a file while another thread imports is noted too. That is an extra key entry,
so it can only cause a miss. The docstring states it.

## Cases (434 → 437), each red against round 1's fold

Measured by applying the three production hunks of the round-1 head to this tree (the cases kept): rc 1, and
`parse_fail_names` named exactly these three (434/437).

1. A re-entrant import (A calls `_sibling(B)`, then reads its own data file). The data file changes, and A must be
   re-imported: `(1, 1) → (1, 2)`.
2. A file only the INNER import read, where the inner import FAILS on it and the outer catches the exception. The file
   changes, and the outer must be re-imported: `'inner failed' → 2`.
3. Two threads, ordered by `threading.Event`s. T1 enters and waits (at most 0.2 s) for T2 to enter. T2 waits for T1 to
   finish, then reads its data file. Without the lock this is Codex's interleaving, and every wait returns at once.
   With the lock T2 cannot enter, so T1's bounded wait is the one that times out. The case asserts that T2 never
   entered while T1 ran, that no thread raised, that the bytecode settings equal the originals, and that a change to
   T2's data file is a miss.

## Mutations (333 → 337), each hand-checked by the harness's own rule

Each was applied to a staged copy of `scripts/` and `docs/` (no `__pycache__`, `PYTHONDONTWRITEBYTECODE=1`). The check
was suite rc 1 AND `parse_fail_names` (imported from `scripts/check-plan-code.py`) equal to the entry's `expect`.

| Mutation | rc | `parse_fail_names` |
|---|---|---|
| an inner import's exit clears every read-list (`del _SIBLING_STACK[:]`) | 1 | case 1 only |
| a read is noted only in the innermost list (`_SIBLING_STACK[-1:]`) | 1 | case 2 only |
| no lock (`with _SIBLING_LOCK:` → `if True:`) | 1 | case 3 only |
| the outermost import never restores the bytecode settings | 1 | case 3 only |
| (re-bound) the memo is never consulted: its anchor was orphaned by the new indentation | 1 | `the same sibling twice is ONE import` only |

Not registered: making every import "outermost". With the lock, imports are serial, so an inner import that saves the
outer's temporary settings and puts them back is correct. The mutation is equivalent.

## Measured (goal-tree suite, no `__pycache__`, `PYTHONDONTWRITEBYTECODE=1`, interleaved, load 5.8 → 6.7)

| Run | round-1 fold (HEAD) | this fold |
|---|---|---|
| 1 | 3.11 s | 2.49 s |
| 2 | 1.81 s | 2.06 s |
| 3 | 2.07 s | 2.43 s |

About 0.2 s of each run of this fold is the thread case's bounded wait. The lock keeps the saving: origin/master took
15.69–18.07 s under the same conditions in round 1.

## Decision log

A PROSPECTIVE `accrete` row for `suite-cost-a` is in `docs/reviews/decision-scheme/decision-log.jsonl`, written before
round 3. It predicts that no re-entrant, nested, failing or concurrent import leaves a key missing a file it opened, or
leaves the bytecode settings changed. A fix-caused finding here at round 3 is THRASHING, and Phase 6 fires.

## Next

Round 3 runs ONE half by alternation: the Claude half.
