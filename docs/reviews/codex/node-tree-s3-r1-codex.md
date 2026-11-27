<!-- codex-review: model=gpt-6.1-terra -->

**Round 1: two findings remain.** The branch also intentionally removes the requirement that every goal quote a request, as the approved plan specifies.

1. **MINOR — Requestless goals use heading order instead of tree order.** [scripts/goal-tree.py:2457](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/node-tree-s3/scripts/goal-tree.py:2457) sorts requestless goals by their position in `goal-threads.md`. With features-tree order `a, b` and thread headings `b, a`, both without requests, it assigns `b` number 1 and `a` number 2. Task 14 and the spec require tree order. Pass the node ordering into the numbering calculation and test headings in the reverse order.

2. **MINOR — A rename alone appends a duplicate snapshot.** [scripts/goal-tree.py:1804](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/node-tree-s3/scripts/goal-tree.py:1804) fingerprints the raw previous snapshot before resolving its former slugs. A log whose latest goal is `dev-speed-first`, followed by an otherwise identical snapshot for `dev-speed`, appends a second record. Rendering resolves both, but the log still grows and reports a snapshot logged for a rename alone. Resolve both snapshots before comparing their fingerprints, excluding historical display metadata such as `then`, and test the actual append path.

The former-slug, prefix-slug, `also` self-reference and former-slug heading probes were refused as expected. An empty features file caused CANNOT RUN in the goal-tree and session-state readers; P8 accepted four empty texts because the shared parser reports no error for them.

All six relevant self-test suites passed. In scratch copies, all 31 new mutations failed their named cases. All mutation pins matched their manifest lengths. The worktree was left unchanged.

## Loosening answers
LOOSENING-CHECK e024446e99d5: not a loosening
LOOSENING-CHECK 9db761b27f3c: not a loosening
LOOSENING-CHECK 2b4665a6f4f6: finding: the shipping-set self-test accepts the new 363-edge graph that the old 361-edge pin rejected.
LOOSENING-CHECK 5302c305c129: finding: a goal heading with no quoted request is now accepted, as required by the approved plan.
LOOSENING-CHECK c096c086d34b: finding: a goal heading with no quoted request is now accepted, as required by the approved plan.
LOOSENING-CHECK 23c951e99349: not a loosening
LOOSENING-CHECK 41aa961b3cfa: not a loosening
LOOSENING-CHECK bfe5231772f9: not a loosening
LOOSENING-CHECK fcdfb41bb03e: finding: snapshot derivation now accepts a goal with no quoted request, as required by the approved plan.
LOOSENING-CHECK 73eecaea2ca7: not a loosening

VERDICT: NOT CONVERGED
