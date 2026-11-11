# Round 2 — `begin-plan-worktree` — coordinator — ⟳ NOT CONVERGED (bet LOST); SPLIT

```yaml
round: 2
fixes_nontrivial: true
subject: begin-plan-worktree
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XH1, severity: High, aim: deliverable, fix_induced: true, component: worktree-detection, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: true, component: worktree-detection, disposition: fixed}
```

REVIEW GAP: claude — round 2 alternates to the Codex half on the final tree (`review-method.md`, *The
protocol*, step 4; backlog #339).

`X` = Codex, tree `cc2aa5b6`. **The bet — no High, no way a linked worktree arms — is LOST**, by the redesign itself.

- **XH1 (fold-induced, fixed):** reading `.git` by its PATH SHAPE missed two valid layouts — `.git` a symlink to the
  worktree's admin directory (`is_file()` false) and a `gitdir:` through a symlinked alias (the parent is not named
  `worktrees`); a linked worktree armed. Git resolves both.
- **XM2 (fold-induced, fixed):** a `--separate-git-dir <x>/worktrees/<y>` MAIN checkout read as linked, refusing every
  state command.

Confirmed held by Codex: no git invoked, `GIT_DIR` both ways, moved main refuses, all eight commands refused before
any state, quoting round-trips.

Route: SPLIT (decision-log row written before the change) — git is the AUTHORITY (no `GIT_*` in its environment,
`--absolute-git-dir`, cwd = ROOT, exactly two absolute path lines), and the `.git` file is the FALLBACK, read only when
git cannot answer, refusing on a worktree `gitdir:`. Three cases over real git (symlinked `.git`, aliased `gitdir:`, a
separate-git-dir main) and three mutations (no env scrub, git never asked, no fallback), each red via its case.
Round 3 is the last, a confirmation round.
