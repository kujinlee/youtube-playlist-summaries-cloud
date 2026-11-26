# Round 1 — `b730-post-cutover` — coordinator — both halves NOT CONVERGED; 6 distinct findings, all to be fixed

Both halves reviewed head `2afc4e28` (PR #643, backlog #730). Self-test 139/139 + 42/42 cannot-run in both; Codex
hand-applied 3 of the new mutations and Claude all 13, each turning exactly its named case red.

| Id | Raised by | Severity | Finding | Disposition |
|---|---|---|---|---|
| F1 | Codex HIGH, Claude M1 | High | `_master_ci` skips a run whose `ask store (push)` step is not `success`/`failure`. In the real `verify` job any earlier red step marks that step `skipped`, so a red post-squash run is passed over and an older green run answers: **a false rc 0**. The rc 7 case feeds a shape GitHub cannot produce (self-test `failure` + L1 `success`); an L1 `failure` skipped to the next run survives the self-test. | fix: decide "post-squash" from the run's COMMIT (ancestry of the squash, or the gate marker at `headSha`), judge the NEWEST completed post-squash run, require both steps `success`; cases in GitHub's real shapes |
| F2 | Claude M2 | Medium | Error paths with no case: `gh pr list` failing or a full page under `--post-cutover`, `gh run view` failing, A1/L1 git errors — each mutated to "no error" survives 139/139, and the first two give rc 0. | fix: cases + mutations for `gh pr list` and `gh run view` failing → rc 2; the A1/L1 git-error paths filed with a stated bound if not drivable |
| F3 | Codex MEDIUM, Claude M3 | Medium | Task 13 Step 1's `cd … && git fetch && git checkout && python3 …` returns 1 from a failed `cd`/`checkout`, read as "master's store moved" — backlog #730's own M1 again; before the squash it ends in rc 2, so rc 3 is unreachable through it. | fix: run in a fresh `git worktree add --detach`, and read the status from the script's last `post-cutover rc N` line |
| F4 | Codex MEDIUM | Medium | `gh pr diff --name-only` with rc 0 and empty stdout is taken as "this PR does not edit the store". | fix: an empty answer is CANNOT RUN (rc 2), with a case |
| F5 | Claude L1 | Low | The fetch updates `origin/master` only through the clone's default refspec. | fix: explicit refspec `+refs/heads/<b>:refs/remotes/<r>/<b>` |
| F6 | Claude L2 | Low | Steps are merged across jobs by name. | fix: key on the `verify` job's steps |

**Loosening answers.** Every flagged id Codex answered as a finding names PR #640's retirement of the dashboard-entry
rule (now merged, `e1b13c15`), the owner-approved goal (selection card A, 2026-11-24 09:57 and 10:03). None names this PR's diff.

```yaml
round: 1
fixes_nontrivial: true
subject: b730-post-cutover
halves:
  codex: ran
  claude: ran
findings:
  - {id: F1, severity: High, aim: deliverable, fix_induced: false, component: check-ask-store, disposition: fixed}
  - {id: F2, severity: Medium, aim: deliverable, fix_induced: false, component: check-ask-store, disposition: fixed}
  - {id: F3, severity: Medium, aim: deliverable, fix_induced: false, component: dashboard-retire-plan, disposition: fixed}
  - {id: F4, severity: Medium, aim: deliverable, fix_induced: false, component: check-ask-store, disposition: fixed}
  - {id: F5, severity: Low, aim: deliverable, fix_induced: false, component: check-ask-store, disposition: fixed}
  - {id: F6, severity: Low, aim: deliverable, fix_induced: false, component: check-ask-store, disposition: fixed}
```

Reviews: `docs/reviews/codex/b730-post-cutover-r1-codex.md`, `docs/reviews/claude/b730-post-cutover-r1-claude.md`.
