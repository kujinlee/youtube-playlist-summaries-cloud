# Round 1 — `suite-cost-a` (PR #537, backlog #231) — coordinator — Codex NOT CONVERGED, Claude CONVERGED; all four folded by re-keying the goal-tree sibling cache on what the import READ

```yaml
round: 1
fixes_nontrivial: true
subject: suite-cost-a
halves:
  claude: ran
  codex: ran
findings:
  - {id: R1-F1-codex, severity: Medium, aim: deliverable, fix_induced: false, component: goal-tree-sibling-cache, disposition: fixed}
  - {id: R1-F2-codex, severity: Medium, aim: deliverable, fix_induced: false, component: goal-tree-sibling-cache, disposition: fixed}
  - {id: R1-F1-claude, severity: Low, aim: deliverable, fix_induced: false, component: goal-tree-sibling-cache, disposition: fixed}
  - {id: R1-F2-claude, severity: Low, aim: deliverable, fix_induced: false, component: goal-tree-sibling-cache, disposition: fixed}
```

Both halves ran: Codex (`docs/reviews/codex/suite-cost-a-r1-codex.md`, NOT CONVERGED) and Claude
(`docs/reviews/claude/suite-cost-a-r1-claude.md`, CONVERGED). All four findings are about one key:
`scripts/goal-tree.py`'s `_sibling_at`, keyed on `(name, path, mtime_ns, size)`.

- **Codex R1-F1 (Medium):** a same-size rewrite with the mtime put back was served stale. Reproduced by the reviewer.
- **Codex R1-F2 (Medium):** the key left out files the sibling reads during its import (`gen-backlog-page` loads
  `check-docs.py` for `CELL_SPLIT`; `gen-dashboard` loads `check-dashboard-entry.py`). Reproduced by the reviewer.
- **Claude R1-F1 (Low):** mtime and size were each untested on their own. Both one-part mutants survived.
- **Claude R1-F2 (Low):** the docstring promised a fresh import after a rewrite, but Python's `__pycache__` check
  (mtime in seconds plus size) can serve stale bytecode. This is older than the PR.

`fix_induced`: false for all four. They are round 1 findings on the PR's own change, so no earlier round's fix caused
them.

## The fold: one class fix, not four instance fixes

The class is *"the key does not cover what the cached import read"*. The fold is option (a) of the brief:

- An audit hook (`sys.addaudithook`, the `open` event) records every path opened while a sibling imports.
- The memo is keyed on the PATH. A lookup is a hit only if the sibling's bytes AND every recorded file's bytes equal
  what the import read, compared byte for byte. So stamps (mtime, size) are no longer part of the key at all. That
  settles Codex R1-F1 and makes Claude R1-F1 moot: what used to be keyed on mtime and size is now keyed on content.
- The import runs with `sys.pycache_prefix` set to an empty directory and `sys.dont_write_bytecode` on. The sibling,
  and every module it loads by path, is therefore compiled from source (Claude R1-F2).
- The docstring now states its bound: files OPENED during the import. A directory listing, an environment variable,
  the clock, a module served from `sys.modules`, and a dependency rewritten DURING the import are not covered.

Cases (434, from 431): a same-size rewrite with the mtime put back and an old `.pyc` planted; a change only in the
file the sibling loads, with the same stamp and an old `.pyc`; one name in two directories. The first two are RED
against the round-1 head's implementation (measured: 432/434). Mutations go 327 → 333, and each new or re-bound one was
hand-checked red on its named case.

## Measured (goal-tree suite, interleaved, harness conditions: no `__pycache__`, `PYTHONDONTWRITEBYTECODE=1`)

| Run | origin/master | round-1 head | this fold (a) | option (b): every `scripts/*.py` |
|---|---|---|---|---|
| 1 | 18.07 s | 2.55 s | 2.27 s | 5.35 s |
| 2 | 17.34 s | 1.95 s | 2.25 s | 4.51 s |
| 3 | 15.69 s | 1.79 s | 1.81 s | 5.60 s |

Load average (1 min) fell from 20.9 to 14.5 over the runs. Option (a) keeps the round-1 head's saving. Option (b)
re-reads 7.6 MB per lookup and costs two to three times as much as (a). With a warm `__pycache__` (a local run, not
the harness), (a) took 2.28 / 3.59 / 3.65 s against master's 2.50 / 2.39 / 2.98 s. That is the price of never reading
bytecode, and it does not apply to the mutation sweep, which stages its trees without `__pycache__`.

## Next

Round 2 runs ONE half, by alternation (`docs/review-method.md` → *Round topology*); the coordinator picks which.
