# Round 4 — `stalled-work` (PR #452, backlog #410) — coordinator — NOT CONVERGED (Codex); the fold is done

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 4
fixes_nontrivial: true
subject: stalled-work
halves:
  codex: ran
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: F1, severity: Major, aim: deliverable, fix_induced: false, component: gh-validation, disposition: fixed}
```

Codex reviewed `ade9855b` against synthetic repositories. **The uncached check held:** octopus and second-parent merges, an empty commit, a submodule change, a rename, a deleted upstream and a detached HEAD all reported unique work as STALLED; a garbage or empty `gh` reply gave a framed CANNOT RUN; no operational cache code, stale BOUNDS line or dangling mutation remained. **One finding, not fix-induced:**

| ID | Severity | Finding | Fold (TDD: the cases were red first, 9 failed against the old `own_prs`) |
|---|---|---|---|
| F1 | Major | `own_prs` DROPPED a node it could not read, so the hook exited 0 with no output: a `null` node, a PR with no `isCrossRepository`, and an own-repo PR with no `isDraft` (read as non-draft) | `pr_node_problem` holds EVERY node to its shape (object, integer `number`, boolean `isCrossRepository` and `isDraft`, string `headRefName`) BEFORE any is filtered; a malformed one raises `CannotRun`. A node that says `isCrossRepository: true` is still excluded. A non-list is refused too (it was an empty list) |

**The same pattern elsewhere:** `own_prs` was the only drop-instead-of-refuse site among `gh`-derived structures. `gh_prs` already refuses a missing envelope, a non-list `nodes` and a `totalCount` mismatch. Two sites are left as they are, on purpose: `headRefOid` that is not a hex id is emptied (it becomes a git argument; the head's age then comes from the local store, else UNKNOWN, which a draft shows), and `head_commit_ts` returns no date for an unparseable one (the same UNKNOWN). Both end in a visible line, not silence. Git-derived parsers (`parse_refs`, the `local_ts` loop) skip blank lines, which is their output format.

**Cases:** 175 -> 183 (two old drop cases became refusals; eight added or changed, including one end to end through the real `gh` wrapper with a `null` node). **Mutations:** 80 -> 84 for this file, declared sum 2645 -> 2649. Two entries whose subject (the drop-based filter) is gone were replaced, not orphaned; two were re-bound to the new text. The six new or re-bound entries were each run against the suite and went red via the case they name. The harness pre-check (`--mutate . --only`) accepts the manifest with a green control; the full run is refused locally on time, as expected.

**Timing.** The real hook, three runs, in this worktree: 1.51, 1.09, 1.06 s; Codex measured 2.0-2.8 s. The machine's load average read 48 over fifteen minutes and 6.4 now, so the gap is LOAD, not a regression: the earlier 0.8-1.65 s and these agree once load falls. The time is waiting, not computing: the profile's top cumulative entries are the thread pool's `result`/`join` waits (2.6 s summed across threads), then `collect` (0.90 s wall) and `git` subprocess calls (33 calls, 0.64 s). Python's own work is small: `names_in` (216 calls, 0.08 s) is the largest pure-Python cost. The repo has 73 worktrees and 132 branches.
