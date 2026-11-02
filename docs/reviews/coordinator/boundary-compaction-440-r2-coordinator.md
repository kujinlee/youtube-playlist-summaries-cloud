# Round 2 — `boundary-compaction-440` — coordinator — NOT CONVERGED (Claude half); all findings FOLDED

The Claude half reviewed `9f691861`, the fold of round 1 on PR #463 (backlog #440, the PreCompact boundary hook).

REVIEW GAP: codex — alternation (round cap: both halves in r1, then one half per round). It named no Q4c BLOCKER;
three Low findings, each fix-induced by the r1 fold. Under the round cap they are folded at every severity.

```yaml
round: 2
fixes_nontrivial: true
subject: boundary-compaction-440
halves:
  codex: gap-alternation
  claude: ran
findings:
  - {id: R2-1, severity: Low, aim: deliverable, fix_induced: true, component: agent-signal, disposition: fixed}
  - {id: R2-2, severity: Low, aim: deliverable, fix_induced: true, component: plan-signal, disposition: fixed}
  - {id: R2-3, severity: Low, aim: deliverable, fix_induced: true, component: ceiling, disposition: fixed}
```

## Dispositions

| # | Finding | Disposition |
|---|---|---|
| R2-1 | A completed foreground agent whose report QUOTES "agent launched" is read as a background launch and stays open | **FIXED** `scripts/check-compaction-boundary.py:217-219`: the result must BEGIN with `LAUNCHED` / `SPAWNED` (`:104-105`, the measured shapes, 65 of 65 and 189 of 189). ⚠ Making that true needed a second fix, found by the new case: `_strings` yielded each block's `"type": "text"` BEFORE its text, so no anchored test of a result's first characters could ever pass. `_result_text` (`:143`) takes the blocks' `text` only. |
| R2-2 | A cwd inside a NESTED repo (`.remember/` has its own `.git`) misses the live plan, and the log would land in `.remember/.claude/` | **FIXED** `:344` `session_checkout`: the cwd's checkout is used only when it is the project's own main checkout or a linked worktree of it (`main_checkout` equal); otherwise `CLAUDE_PROJECT_DIR`. `evaluate` (`:411`) and `log_path` both call it, so the log goes only to the main project's `.claude/`. ⚠ **Residual:** with no `CLAUDE_PROJECT_DIR` in the environment there is no project to fall back to, and a cwd in a nested repo still uses that repo. The hook is registered by the project's settings, which set it; not measured otherwise. |
| R2-3 | The ceiling falls BELOW W for W in (180k, 200k] and (900k, 1M], so the hook can never defer there and `--summary` reads 100% ceiling-forced | **FIXED** `:305` `ceiling`: `max(W, min(1.5W, 0.9L))`. A ceiling equal to W logs `ceiling_by: "no-headroom"` (`:430`). ⚠ **`--summary` does not read that field yet:** its share line still counts every `allow-ceiling`. The label is in the log so the rows can be separated; changing `summary` to exclude them was not asked for and is not done. |

An existing case moved with R2-3 and is named here so it is not read as a loosened test: "a 1M window at 999,999
tokens is past its ceiling" is now a **900k** window at 999,999. At W = 1M the ceiling is W, so 999,999 is below it
and defers by one token; that is the intended behaviour at no headroom, and the hard-limit property is still pinned
by the 900k case.

## Gates run (foreground, on the fold)

| Check | Result |
|---|---|
| `check-compaction-boundary.py --self-test` | 81/81 (+4) |
| `check-plan-code.py --mutate . --only scripts/check-compaction-boundary.py` | 45 killed, 45 attributed, 0 survivors (pin 41 → 45). Every fix reverted once by its mutation, red via the case it names |
| `check-docs.py`, `check-review-rounds.py`, `check-selftest-counts.py`, both plan-leak scans | see the commit's report |

## Next

Round 3 has ONE half, Codex, over the fold commit (`REVIEW GAP: claude — alternation`).
