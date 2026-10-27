# Round 1 — `begin-plan-worktree` — coordinator — ⟳ NOT CONVERGED (both halves); REDESIGN

```yaml
round: 1
fixes_nontrivial: true
subject: begin-plan-worktree
halves:
  codex: ran
  claude: ran
findings:
  - {id: XH1, severity: High, aim: deliverable, fix_induced: false, component: worktree-detection, disposition: fixed}
  - {id: XH2, severity: High, aim: deliverable, fix_induced: false, component: worktree-detection, disposition: fixed}
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: false, component: worktree-detection, disposition: fixed}
  - {id: XM4, severity: Medium, aim: deliverable, fix_induced: false, component: refusal-message, disposition: fixed}
  - {id: XL5, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: false, component: refusal-message, disposition: fixed}
  - {id: CM2, severity: Medium, aim: deliverable, fix_induced: false, component: tests, disposition: fixed}
  - {id: CM3, severity: Medium, aim: deliverable, fix_induced: false, component: worktree-detection, disposition: fixed}
  - {id: CL1, severity: Low, aim: deliverable, fix_induced: false, component: worktree-detection, disposition: fixed}
  - {id: CL2, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: CL3, severity: Low, aim: deliverable, fix_induced: false, component: refusal-message, disposition: fixed}
```

`X` = Codex, `C` = Claude, both on the first PR #406 tree. Both: 131/131; each of the three mutations red via its case.

- **XH1 = CL1, XH2, XM3 = CM3 — fixed by REDESIGN:** asking `git` failed three ways, each executed — git < 2.31
  echoes `--path-format=absolute` as an output line (the main checkout then refused everything); `GIT_DIR`/
  `GIT_WORK_TREE` override `git -C` (a worktree armed, or the main checkout refused); a moved main checkout made
  discovery fail into the same None as a real main checkout (fail open). `linked_worktree_main` now reads
  `ROOT/.git` itself and runs no git: a directory is the main checkout, a FILE `gitdir: …/worktrees/<n>` is linked
  whether or not its target exists, a submodule (`…/modules/…`) or a staged copy is not.
- **XM4 = CM1 (fixed):** the printed command was `' '.join(argv)` — `--pause "waiting on CI"` became `paused:
  waiting`, and `title|doing|why` became a shell pipeline. Now `shlex.join`, with a round-trip case.
- **CM2 (fixed):** only the slug arm was witnessed; exempting `--plan` passed 131/131. A case now drives all seven
  state commands from a linked worktree (with a RESOLVED root, so `--plan` would really arm) and a mutation exempts
  `--plan`.
- **CL3 (fixed):** a bare repository's worktree (or a moved main) was pointed at a script that does not exist; the
  refusal now says no main checkout was found.
- **CL2, XL5 (fixed):** the stated reason for refusing over resolving was false (both record the main checkout's
  branch); the reason is that refusal makes the problem visible. The dashboard's counts were stale.

Route: REDESIGN (decision-log row written before this fold). Round 2 is a confirmation round.
