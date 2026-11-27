<!-- codex-review: model=gpt-6.1-terra -->

1. **MINOR — PRIORITY-shaped prose is still falsely refused.** [scripts/check-features.py:517](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/node-tree-s3/scripts/check-features.py:517) treats `PRIORITY is "important" to the owner.` as an attempted priority declaration and reports a malformed line. This is a near-miss of F1’s prose input. Restrict attempt detection to a recognizable declaration shape, and add quoted prose as a regression case.

2. **MINOR — A malformed priority declaration can be silently ignored.** [scripts/check-features.py:573](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/node-tree-s3/scripts/check-features.py:573) accepts `PRIORITY tomorrow morning "do a" · a` as preamble prose: `thread_name_problems` returns no problems, and the priority reader ignores the line. The author receives no indication that the intended ordering was discarded. Detect declaration-shaped lines with malformed dates even when the date has multiple tokens, and report them. The regular expression for a valid PRIORITY line remains covered by the new detector.

C1, C2, F3, F4 and F5 held under the tested cases. Requestless goals absent from the tree sort after known nodes; rename history through `was: b, c` resolves both former names; an unknown historical slug remains unchanged; and `nodes=None` retains raw fingerprint comparison. Repeated handwritten slugs were refused, while repeated `--also` values were stored once in first-written order.

The self-tests passed: check-features **115/115**, goal-tree **639/639**, and session-state **184/184**. On scratch copies, all **17 changed or new mutations** killed their named cases, including the three re-bound anchors. All 107 mutation pins matched their manifest lengths. The worktree remained unchanged.

The removed request requirement and updated shipping-set pin are deliberate gate changes; the exact paths affected are recorded below.

## Loosening answers
LOOSENING-CHECK e024446e99d5: not a loosening
LOOSENING-CHECK 9db761b27f3c: not a loosening
LOOSENING-CHECK 2b4665a6f4f6: finding: the shipping-set self-test accepts the new 363-edge graph that the old 361-edge pin rejected.
LOOSENING-CHECK 5302c305c129: finding: a goal heading with no quoted request is now accepted, as required by the plan.
LOOSENING-CHECK c096c086d34b: finding: a goal heading with no quoted request is now accepted, as required by the plan.
LOOSENING-CHECK 23c951e99349: not a loosening
LOOSENING-CHECK 13b6956c8913: not a loosening
LOOSENING-CHECK 75bc2c1bce4a: not a loosening
LOOSENING-CHECK 41aa961b3cfa: not a loosening
LOOSENING-CHECK bfe5231772f9: not a loosening
LOOSENING-CHECK fcdfb41bb03e: finding: snapshot derivation now accepts a goal with no quoted request, as required by the plan.
LOOSENING-CHECK f9ff3755d377: not a loosening
LOOSENING-CHECK 73eecaea2ca7: not a loosening

VERDICT: NOT CONVERGED
