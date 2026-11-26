Reviewed head: 344a35b2f29063362346729213518fb032cd7ddd

# PR #642 (backlog #737), review round 1, Claude half

Scope: `git diff origin/master...HEAD`, which changes `scripts/check-plan-code.py:7859-7866`, `scripts/mutations/check-plan-code.json:2315`, a backlog row and a dashboard entry.
Mandate: try to refute the claim that the retargeted real-tree case is not hollow, and check whether it is fragile.

## Method

I worked in a `git archive HEAD` copy under scratch (`.../scratchpad/b737r1/tree`, git-inited, with node_modules symlinked) and ran `python3 scripts/check-plan-code.py --self-test` after each edit. I reverted with `git checkout -- .` between runs. All runs were in the foreground, about 28 s each.

| # | Edit | Result | Real-tree case |
|---|---|---|---|
| 0 | none | 506/506 | green |
| A | backlog #498 mutation (`out \|= {f'"{stem}.py"', ...}` → `pass`) | 504/506 | **red**, got (True, False). The synthetic case is also red |
| B | sever the filename load in check-stalled-work (`with_name("goal-tree.py")` → `with_name("goal" + "-tree.py")`) | 505/506 | **red**, and it is the only red case |
| C | sever only goal-tree's stem import (`_sibling("agent-watchdog")` split) | 506/506 | green (see F1) |
| C2 | C plus removing the docstring mention `agent-watchdog.py:newest_change_ns` (goal-tree.py:594) | 505/506 | **red** |
| C3 | only the docstring mention removed | 506/506 | green |
| D | ambient path: check-stalled-work gets `# see "agent-watchdog"`, plus mutation A | 505/506 | green under the mutation, and only the synthetic case is red |

I also checked that the manifest entry now has 2 distinct `expect`s, and that the second one is exactly the case's concatenated name (`==` True).

## On the questions asked

- **If check-stalled-work stops loading goal-tree by filename**, the case goes red loudly (B). It does not pass vacuously.
- **If goal-tree stops linking to agent-watchdog**, the case also goes red loudly, but only once *both* of goal-tree's links are gone (C2). See F1.
- **Selected with the edge, not selected without it.** The case alone asserts only the positive. The negative, "not selected without the filename hop", is carried by the mutation entry, and runs A and B show it red. That is the right split.
- **Could it pass for an ambient reason?** In D I built an ambient second path. Under the mutation, the case then stays green. The harness rejects that: `rerun_kill` / the `unnamed` rule (check-plan-code.py around 2655 and 2873) requires every named `expect` to be red exactly once, so the entry would report a failure instead of passing silently. Bound: this fires only when the manifest runs, meaning a PR that selects it or the nightly full sweep. A PR that adds such a path to check-stalled-work would not run this entry unless it is selected. That is the usual bound for any mutation entry, not something this PR adds.

## Findings

**F1, NIT.** `scripts/check-plan-code.py:7859-7862`: the comment names only one link for the first hop, but there are two.
- The comment says goal-tree reaches agent-watchdog through "its quoted stem (`_sibling("agent-watchdog")`)".
- There is a second link: goal-tree's docstring at `scripts/goal-tree.py:594` spells `agent-watchdog.py`, and `_names_of` treats a file's basename as a reader spelling.
- Failing input: remove only `_sibling("agent-watchdog")` (run C). The case stays green at 506/506.
- This is harmless to what the case is for. The hop it guards (check-stalled-work → goal-tree by FILENAME) is single-linked, as B shows, and the comment's "Measured" sentence is about that literal and is true. But someone reading the comment and expecting C to break the case would be surprised.
- Fix (optional): say "goal-tree reaches agent-watchdog (stem import and a filename mention); check-stalled-work loads goal-tree only by FILENAME".

**F2, NIT, outside the diff, for information.** `docs/superpowers/specs/2026-11-24-dashboard-retire-design.md:393` still tells S2/S3 to re-point the case name "check-dashboard-entry.py reaches compaction-state through gen-dashboard.py" at `:7860`. This PR makes that instruction moot. The dated `docs/marketplace/scan-*.json` snapshots also quote the old name, but they are historical and correctly left alone. No action is needed here. The S2 plan should just not try to edit a case that no longer exists.

No BLOCKER, MAJOR or MINOR findings. I could not refute Codex's convergence: the case is red under its mutation, red when the filename literal is severed, red when the upstream link is fully removed, and an ambient path is caught by the exactly-once expect rule.

VERDICT: CONVERGED
