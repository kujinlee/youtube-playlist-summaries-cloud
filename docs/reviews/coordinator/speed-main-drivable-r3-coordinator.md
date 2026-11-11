# Round 3 — `speed-main-drivable` (PR #449, backlog #401) — coordinator — CONVERGED (final tree)

REVIEW GAP: codex — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 3
fixes_nontrivial: false
subject: speed-main-drivable
halves:
  claude: ran
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - id: F1
    severity: Low
    aim: deliverable
    disposition: filed
    filed_as: "backlog #417"
    fix_induced: false
```

Claude reviewed the final tree `f0ea4f8b`: the DEFER fold `a3fc464b`, then the master merge.

**The fold is sound.** Both new cases build their own memo, so no earlier case can pre-populate them. Twelve hand mutants all went red: evict the newest, evict on `>=`, cap at `> MAX+1`, never touch on a hit, key by `type()`, key by `ast.dump`, evict the second, evict two, clear on overflow, drop args on a touch, MAX=0 and MAX=1. The merge changed no script. 447/447 cases; the live run gives D2 OK; the declared sum of 2,551 reconciles.

F1 (Info, filed as **backlog #417**): the cap's VALUE is unpinned. `_MEMO_MAX = 2` passes, about 35% slower, with identical output. The unit closes at 3 rounds.
