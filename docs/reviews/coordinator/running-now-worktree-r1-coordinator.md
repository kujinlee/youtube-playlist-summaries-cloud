# Round 1 — `running-now-worktree` — coordinator — NOT CONVERGED (both halves), all folded

Both halves reviewed `11d0568d..a3290002` (backlog #672: the goal tree's Running now sees a building worktree).
Codex (`docs/reviews/codex/running-now-worktree-r1-codex.md`): 3 MAJOR, 1 MINOR. Claude
(`docs/reviews/claude/running-now-worktree-r1-claude.md`): 1 MAJOR, 5 MINOR. No BLOCKER. Two pairs are the same defect
found by both halves (XM1 = F1, XM2 = F5). Every finding is folded in `af7e905f`.

| Id | Severity | Finding | Fold (`af7e905f`) |
|---|---|---|---|
| XM1 / F1 | MAJOR | a build is judged against the SNAPSHOT's clock, so a replayed snapshot keeps a dead builder `building` | judged against the READER's clock (page build time; `owed_idle_lines`' run time) |
| XM2 / F5 | MAJOR / MINOR | the clock is read before `collect`'s network calls, so a slow fetch makes an active builder `ahead` | `main()` re-reads its clock after `collect()` and stamps the snapshot with it |
| XM3 | MAJOR | an open PR keeps its thread Running even when its declared worktree is quiet or gone | the open-PR rule stays (owner 11-05 15:45); a quiet / gone / unread worktree is shown on the Running line as a warning |
| Xm1 | MINOR | minute truncation moves the 30-minute window edge | change times measured and compared in seconds (`SECOND_FMT`) |
| F2 | MINOR | a NOT READ worktree still says `not started` | `not started` only when no worktree is declared |
| F3 | MINOR | four stated behaviours had no witness (hand mutants survived) | cases added: one-minute ahead tolerance, ahead in `started`, the waits gate in `_run_if_building`, the `_ledger_worktree` NOT-READ fallback |
| F4 | MINOR | a count note says `os.path.abspath` cannot be witnessed | corrected; a relative `--set-worktree` case witnesses it |
| F6 | MINOR | `--worktree` accepts the main checkout | `--worktree` / `--set-worktree` refuse the main checkout, a directory holding it, and its `.claude/` |

Verified at `af7e905f` by the coordinator: goal-tree 552/552, session-state 163/163, agent-watchdog 79/79,
check-shipping-sets 140/140. Mutations: goal-tree 454 → 466, session-state 155 → 157.

```yaml
round: 1
fixes_nontrivial: true
subject: running-now-worktree
halves:
  codex: ran
  claude: ran
findings:
  - {id: XM1, severity: Major, aim: deliverable, fix_induced: false, component: worktree-build-clock, disposition: fixed}
  - {id: XM2, severity: Major, aim: deliverable, fix_induced: false, component: worktree-build-clock, disposition: fixed}
  - {id: XM3, severity: Major, aim: deliverable, fix_induced: false, component: running-line, disposition: fixed}
  - {id: Xm1, severity: Minor, aim: deliverable, fix_induced: false, component: worktree-build-clock, disposition: fixed}
  - {id: F1, severity: Major, aim: deliverable, fix_induced: false, component: worktree-build-clock, disposition: fixed}
  - {id: F2, severity: Minor, aim: deliverable, fix_induced: false, component: worktree-state-label, disposition: fixed}
  - {id: F3, severity: Minor, aim: harness, fix_induced: false, component: goal-tree-cases, disposition: fixed}
  - {id: F4, severity: Minor, aim: harness, fix_induced: false, component: session-state-worktree, disposition: fixed}
  - {id: F5, severity: Minor, aim: deliverable, fix_induced: false, component: worktree-build-clock, disposition: fixed}
  - {id: F6, severity: Minor, aim: deliverable, fix_induced: false, component: session-state-worktree, disposition: fixed}
```

Round 2 runs ONE half (alternation): Codex, on the fold `a6ed26fc..af7e905f`.
