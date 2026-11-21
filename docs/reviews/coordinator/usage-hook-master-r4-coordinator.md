# Round 4 — `usage-hook-master` — coordinator — NOT CONVERGED (Codex), no BLOCKER: both findings FILED at the round cap

Codex reviewed the Phase 6 redesign (`3d806aa6`, PR #610, backlog #513) at `7220d426` in
`docs/reviews/codex/usage-hook-master-r4-codex.md`. Its verdict is NOT CONVERGED, with one MAJOR and one MINOR and no
BLOCKER. The Claude half is a gap by alternation, because round 3 was Claude's.

REVIEW GAP: claude — alternation.

```yaml
round: 4
fixes_nontrivial: false
subject: usage-hook-master
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: false, component: locate-main, disposition: filed}
  - {id: X2, severity: Minor, aim: deliverable, fix_induced: false, component: walk-root, disposition: filed}
```

The round cap applies (`docs/review-method.md` §0 Q4c): from round 4 on, a finding is FILED unless it is a BLOCKER.
Neither finding was caused by the r3 fold, so the redesign did not thrash.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| X1 | MAJOR | A worktree whose `.git` file is rewritten to `gitdir: <other>/.git` runs `other`'s usage hook (`.claude/hooks/run-hook.sh:105`). | **FILED** as backlog #688. This is the bound the r3 doc already states for B2 and OTHER: whoever can rewrite `.git` or `commondir` chooses git's repository. `.git` is not a tracked file, so an unmerged BRANCH, which is what backlog #513 guards against, cannot write it. Only a process with write access to the worktree's metadata can, and that process could also edit main's copy. |
| X2 | MINOR | With the cwd outside every checkout and `CLAUDE_PROJECT_DIR` unset, a usage-pace launch exits 1 with an empty stdout, not the fixed NOT RUN JSON line with exit 0 (`.claude/hooks/run-hook.sh:64`). | **FILED** as backlog #688. The walk-root exit predates this branch and applies to every hook. The harness always sets `CLAUDE_PROJECT_DIR`. |

Evidence: Codex quoted `163/163 self-test cases passed`, and the coordinator re-ran it at `7220d426` with the same
result. Codex built X1 with a real `git worktree add` and a separate repository named `other`.
