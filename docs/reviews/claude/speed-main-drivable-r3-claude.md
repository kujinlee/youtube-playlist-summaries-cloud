# Round 3 — speed-main-drivable — claude

Final-tree round of PR #449 (backlog #401), route DEFER. Subject: worktree `wt-401` at head
`f0ea4f8b`. I reviewed the round-2 fold `a3fc464b` first, then the merge `a3fc464b..f0ea4f8b`.
The mandate was to REFUTE. All mutants were applied to a `git archive` copy of HEAD in the
scratchpad, never to the worktree. The runs used Python 3.14.4.

## The DEFER bet, tested

The bet: "no eviction-order or capacity-boundary mutant survives, and cached answers equal
uncached ones". **For order and boundary it HOLDS. It does not hold for the cap's VALUE (F1, Info).**

Hand mutants of `_memo_by_node` (`scripts/check-main-drivable.py:314-359`), each run through the full `--self-test`:

| Mutant | Result | Reddened by |
|---|---|---|
| evict the NEWEST (`next(reversed(memo))`) | 443/447 RED | entry-keeps-node, BOUNDED, both new cases |
| evict on equality (`>=`) | 445/447 RED | both new cases |
| cap one high (`> _MEMO_MAX + 1`) | 444/447 RED | BOUNDED, both new cases |
| never touch on a hit (`pass` for `memo[key] = memo.pop(key)`) | 446/447 RED | BOUNDED (the r1 `_kept` case) |
| key ignores the tree (`type(a)` for `id(a)`) | RED, crashes early with many FAILs | |
| key by content (`ast.dump(a)`) | 443/447 RED | BOUNDED, both new cases |
| evict the second (`list(memo)[1]`, manifest entry 1) | 445/447 RED | both new cases |
| evict two at once | 445/447 RED | both new cases |
| clear the whole memo on overflow | 445/447 RED | both new cases |
| entry drops its args on a touch | RED | several |
| `_MEMO_MAX = 0` | 444/447 RED | |
| `_MEMO_MAX = 1` | 446/447 RED | BOUNDED |
| **`_MEMO_MAX = 8`** | **447/447 GREEN** | — |
| **`_MEMO_MAX = 2`** | **447/447 GREEN** | — |

**Ambient-reason check:** both new cases (`:4564-4593`) build their own `_memo_by_node` instance.
Neither touches `note_globals_imports.memo`. Each holds every tree in a list for the case's
lifetime, so the `id` keys stay unique and `_held_by`'s `args[0] is t` test is exact. No earlier
case can pre-populate either memo, and the evict-the-second mutant, the one that survived round 2
by exactly that route, now reddens the FRESH-memo case. The `>=` mutant reddens the FULL-memo case
through `_edge_full` and `len(_edge.memo)`. That case is not masked: its second pass measures
`_edge_rebuilt == _MEMO_MAX`, which a cap that evicts at equality fails.

**Manifest:** both new entries' anchors occur exactly once in the source, and each `expect` names a
case that exists. My hand runs used the manifest's exact edit strings and confirm that each entry
reddens via the case it names. `EXPECTED_MUTATIONS["scripts/check-main-drivable.py"] = 196` equals
the manifest length (196). `check-plan-code.py --self-test` is 246/246 at `f0ea4f8b`, so the
declared sum of 2551 still reconciles after the merge. I did not run the `--mutate` sweep for this
file: 196 entries take about 30 minutes, which exceeds the deadline. CI's shards own that run.

## The merge

`git diff a3fc464b..f0ea4f8b -- scripts/` is **empty**. The master merge touched no script, so it
cannot have disturbed the cache, its cases, or the mutation manifest.

## Runs at f0ea4f8b, in the worktree, foreground

- `python3 scripts/check-main-drivable.py --self-test` → **447/447 passed**
- `python3 scripts/check-main-drivable.py` → **D2 OK**, rc=0 (55 on disk, 48 in population, 22 drive, 26 pinned)
- `python3 scripts/check-plan-code.py --self-test` → 246/246

## Findings

### F1 — Info: the cap's VALUE is unpinned, and `_MEMO_MAX = 2` survives every case

- `scripts/check-main-drivable.py:362`
- **Input:** `_MEMO_MAX = 64` → `2`, and separately → `8`. Both give 447/447 green.
- **Cost, measured** on the live run in the scratch copy, alternating runs: 64 → 5 s and 6 s; 2 → 7 s and 8 s, about +35%. The output was byte-identical (`cmp`).
- **Why the cases miss it:** every cap case is written in terms of `_MEMO_MAX`. The docstring's
  sizing claim, "at most 26 entries per helper over every real guard", has no case that pins
  `_MEMO_MAX >= 26`. A cap below the working set can throw away the reuse this PR exists for.
  Only 0 and 1 are caught, by the "builds once" and `_kept` cases.
- **Severity:** Info. The impact is performance only, answers are unaffected, and the measured cost
  is small next to the 140 s → 11 s gain. A one-line pin would close it, for example
  `case(..., _MEMO_MAX >= 26, True)`, or better, the measured peak entry count from one `assess()`
  pass over the live population. File it, do not fold it.

No correctness findings. No finding in the fold or the merge.

**CONVERGED** — the DEFER bet holds for eviction order and the capacity boundary. One Info
finding, on the cap's value, is to be filed.
