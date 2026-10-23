# banner-thread-armed — round 5 — Claude half

Range reviewed: `8f91292d..0ce62a5f` (the r4 fold: the byte-identical collapse removed; plan identity is (checkout, slug)). Context: the whole change is `cd7134f8..0ce62a5f`.

## What was executed

Everything ran against copies made with `git archive 0ce62a5f`, each with its own fresh `git init`. I made no writes to the worktree or the repo, and I did not run the Stop hook or `begin-plan.py` against the real `.claude/`.

| Run | Result |
|---|---|
| `gen-work-lines.py --self-test` @ 0ce62a5f | `56/56 self-test cases passed` |
| `begin-plan.py --self-test` @ 0ce62a5f | `122/122 self-test cases passed` (F5 and F5b PASS) |
| `check-banner-armed.py --self-test` @ 0ce62a5f | `236/236 self-test cases passed` |
| Control: same tree with `scripts/gen-work-lines.py` reverted to 894db579 (r3, collapse present) | begin-plan `[FAIL] F5b ... got False want True`, `121/122` — so F5b detects the r4 defect through the real `_banner_line` |
| Scoped `check-plan-code.py --mutate .`. The copy was pruned to `gen-work-lines.json` and `begin-plan.json`, `EXPECTED_MUTATIONS` was pruned to those two keys, and `node_modules/typescript` was symlinked in | `OK — delivered scripts mutated: 2 file(s), 85 mutation(s), 85 killed, 85 attributed to the case each names, 0 survivor(s)`, rc=0. That is 28 + 57, which matches the declared counts |

## Removal completeness (the round's focus)

- **Dead code: none found.** `hashlib` was imported only for the collapse and is removed. Nothing anywhere in `scripts/` or `.claude/hooks/` reads `rec["sha"]` from a plan record (grep: the only `["sha"]` hit is `gen-backlog-page.py:3043`, which is unrelated). The `groups`/`gs`/`held` machinery is fully gone.
- **Orphaned cases or mutations: none.** The retired entry (`g[1]["sha"] == r["sha"]`) is gone together with its subject. The two re-anchored entries (the `len(copies) > 1` labels and the `pathlib.Path(c).name for c, _ in copies` short labels) resolve and are killed by the cases they name. The new entry, which re-introduces a collapse via `c[1] == r`, is killed by WT10. WT4b and WT4c were inverted to assert the stated limit (two rows, counted twice) and were not deleted. The scoped run's 85/85 attribution is the evidence.
- **Pre-collapse behaviour restored.** Compared with fe08f438 (pre-collapse, r2 fold):
  - Each copy is one row.
  - A child's parent resolves to the copy in its own checkout, else the first copy (main first).
  - The resolver is now `row_for`, which keeps r3's improvements: short labels, absolute-path fallback on a folder-name clash, and the `d.parent.parent` fix.

  `found` order within a slug group is preserved, so "main first" still holds.
- **`row_for` (mandate c).** There are two production callers: `read_plans_noted` (parent re-pointing, `gen-work-lines.py:440`) and `begin-plan._banner_line` (`begin-plan.py:369`). No other caller resolves a slug its own way. `check-banner-armed.py` uses only `plan_dirs`, and `work_line` keys on the already-resolved slug. With `checkouts` now always a 1-tuple, `want in r["checkouts"]` is exact, and the main-first fallback is unchanged.
- **Docs.** The dashboard entry, the `read_plans_noted` docstring and the `EXPECTED_MUTATIONS` comment all describe the removal and the accepted limit consistently. The r3 sentence "Six are new: byte-identical copies collapse (F4)" (`check-plan-code.py:961`) is kept as history and is followed directly by the ⟳ r4 note. That is acceptable.

## Mandate items still applicable

- **a (thread check before the journal lookup):** not touched in this range. The 236/236 check-banner-armed suite still passes. No new evidence either way.
- **b (collapse):** moot, because the collapse is removed. The open-line count is now one per (checkout, slug). WT10 asserts both lines open, and WT4c asserts that an identical pair counts as 2.
- **d (`GIT_*` dropped):** not touched in this range. Both callers pass `ROOT` or the checkout root explicitly, and I found no caller that sets `GIT_DIR` on purpose.
- **e (mutations):** all 85 were killed and attributed to the cases their names give (above).

## Findings

**F1 — Nit — `scripts/gen-work-lines.py:422-436`: row order is now grouped by slug, not `found` order (UNVERIFIED rendering effect).**
- Input: rows `X@main, Y, X@side` in `found` order.
- What happens: `by_name` emits `X@main, X@side, Y`. Pre-collapse (fe08f438) code kept the `found` order. `build_forest` sorts roots and children by `touched` (a date) using a stable sort, so rows touched on the same day can appear in a different order than before the collapse.
- Impact: cosmetic only. Nothing asserts the order, and r3 already had this behaviour. I read the order change from the code; I did not render a page to observe it.
- Fix: none required. Optionally sort by `(touched, slug)` for determinism.

**F2 — Nit — `scripts/begin-plan.py:1864-1886`: F5b is named by no mutation.**
- F5b is the only case that exercises the r4 defect through `_banner_line`, and no begin-plan mutation names it. The defect class is still mutation-covered in `gen-work-lines.json` through WT10. My r3-revert control above shows F5b reddens on the real defect, so it is not a test that cannot fail.
- Fix: none required.

## Thrashing or prose floor?

**Neither, and the trend says this is converging.**
- r4's Major was caused by r3's fold (the collapse), which makes it a fix-caused finding. It was resolved by removal, not by another patch.
- This round finds no finding caused by the r4 fold. The removal restores pre-collapse identity semantics, and the scoped mutation run is fully attributed.
- A third consecutive fix-caused round, which would arm thrashing, did not occur.

VERDICT: CONVERGED
