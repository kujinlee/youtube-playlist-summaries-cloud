# Round 1 — `tmp-pile` (PR #535, backlog #512) — coordinator — Codex NOT CONVERGED, Claude CONVERGED; all folded

```yaml
round: 1
fixes_nontrivial: true
subject: tmp-pile
halves:
  claude: ran
  codex: ran
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: false, component: fixture-tmp, disposition: fixed}
  - {id: C1, severity: Low, aim: deliverable, fix_induced: false, component: fixture-tmp, disposition: fixed}
  - {id: C2, severity: Low, aim: deliverable, fix_induced: false, component: fixture-tmp, disposition: fixed}
```

Codex (`docs/reviews/codex/tmp-pile-r1-codex.md`, its R1-F1 = X1 here): a refused block changed an unset cache.
- X1: with `tempfile.tempdir is None`, `isolated(GIT_DIR="x")` filled the cache in the scratch `mkdtemp`, and `env()`
  then raised before the inner `finally` that restored it. Fixed: `scripts/fixture_git.py` `isolated()` now restores
  `tempfile.tempdir` and `os.environ` (so `TMPDIR`) in the OUTERMOST `finally`, so a failed `mkdtemp` or a refused
  block restores too. Cased from `TMPDIR` unset and set, with a `None` cache, on the normal, raising and refused paths
  (6 cases); the mutant that moves the restore back to the inner `finally` reds the two refused ones.

Claude (`docs/reviews/claude/tmp-pile-r1-claude.md`, its R1-F1 and R1-F2 = C1 and C2 here):
- C1: a restore to `None` in place of the saved value passed 52/52. Fixed: a case enters from a cache naming a
  directory other than `TMPDIR` and asserts it comes back; the `= None` mutant reds it. Two more mutants: the cache
  restored from the saved `TMPDIR` (reds the `TMPDIR`-set, `None`-cache normal case) and `os.environ` restored by
  `update` (reds the `TMPDIR`-unset normal case).
- C2: `check-selftest-counts.audit`'s docstring said TMPDIR is "deliberately NOT redirected". Reworded: the parent
  does not redirect it, each suite's `isolated()` nests its own scratch under it.

`fixture_git` 52 -> 60 cases; mutations 19 -> 23 (6 existing anchors re-bound to the restructured block), 23 killed,
23 attributed, 0 survivors. The fix changes behaviour on the refused path, so `fixes_nontrivial: true` and round 2
runs on the fold.
