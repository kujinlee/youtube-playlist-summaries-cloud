# Round 3 — `boundary-compaction-440` — coordinator — NOT CONVERGED (Codex half); all findings FOLDED

The Codex half reviewed `24a6a63f`, the fold of round 2 on PR #463 (backlog #440, the PreCompact boundary hook).

REVIEW GAP: claude — alternation (round cap: both halves in r1, then one half per round). It named no Q4c BLOCKER;
one High and one Low, each reproduced, neither a live model failure or data loss. Under the round cap they are
folded at every severity.

```yaml
round: 3
fixes_nontrivial: true
subject: boundary-compaction-440
halves:
  codex: ran
  claude: gap-alternation
findings:
  - {id: R3-1, severity: High, aim: deliverable, fix_induced: true, component: ceiling, disposition: fixed}
  - {id: R3-2, severity: Low, aim: deliverable, fix_induced: false, component: log-failure, disposition: fixed}
```

## Dispositions

| # | Finding | Disposition |
|---|---|---|
| R3-1 | Flooring the ceiling at W (r2 R2-3) removed the safety margin: at W = 1M the hook blocked at ctx 999,999 with an Agent outstanding | **FIXED** `scripts/check-compaction-boundary.py:304` `ceiling`: `min(1.5W, 0.9L)`, never floored, so it is never above 90% of the limit. `decide` (`:310-319`) allows whenever that ceiling is not above W (`top <= w`), so a window with no headroom never defers; `evaluate` (`:433`) logs `ceiling_by: no-headroom` for `top <= w`. W = 1M, 950k and 200k all allow just below W. Sibling searched: the only other reader of `ceiling` is the log record. |
| R3-2 | A log write error (FIFO, directory, unwritable) left the block decision standing with zero snapshots, refuting "fails open on every error path" | **FIXED** `:466-483` `hook`: any logging failure (now `Exception`, not only `OSError`) turns a `block-*` verdict into `allow-log-failed`, and the snapshot runs once. |

Two existing cases moved with R3-1 and are named here so they are not read as a loosened test: the ceiling table
now reads 180,000 (not 200,000) at W = 200k and 900,000 (not 1,000,000) at W = 1M; the "never below W" case became
"never above 90% of the limit"; the `no-headroom` log case expects 180,000.

## Gates run (foreground, on the fold)

| Check | Result |
|---|---|
| `check-compaction-boundary.py --self-test` | 83/83 (+2) |
| `check-plan-code.py --mutate . --only scripts/check-compaction-boundary.py` | 47 killed, 47 attributed, 0 survivors (pin 45 to 47). Two entries added; the exclusive-ceiling, floor, unclamped, and label entries re-anchored to the new text |
| `check-docs.py`, `check-review-rounds.py`, `check-selftest-counts.py`, `check-fixture-variation.py`, both plan-leak scans | see the commit's report |

## Next

Round 4 is BLOCKER-only (Q4c), then the owner's live dry-run.
