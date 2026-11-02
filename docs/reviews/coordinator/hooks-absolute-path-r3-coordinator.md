# Round 3 — `hooks-absolute-path` — coordinator — ⟳ NOT CONVERGED (bet LOST); THRASHING → true SPLIT + architecture review

```yaml
round: 3
fixes_nontrivial: true
subject: hooks-absolute-path
halves:
  codex: skipped
  claude: ran
findings:
  - {id: CH1, severity: High, aim: deliverable, fix_induced: true, component: hook-launch, disposition: deferred}
  - {id: CL2, severity: Low, aim: deliverable, fix_induced: true, component: hook-launch, disposition: deferred}
  - {id: CL3, severity: Low, aim: deliverable, fix_induced: true, component: hook-launch, disposition: deferred}
  - {id: CL4, severity: Low, aim: deliverable, fix_induced: true, component: tests, disposition: fixed}
  - {id: CL5, severity: Low, aim: deliverable, fix_induced: false, component: tests, disposition: deferred}
  - {id: CL6, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

REVIEW GAP: codex — round 3 alternates to the Claude half (`review-method.md`, *The protocol*, step 4; backlog #339).

`C` = Claude, tree `19880062`. 36/36; all 13 manifest mutations killed by their cases; a 300 KB binary payload
intact through `exec`; `GIT_CEILING_DIRECTORIES` inert; cwd inside `.git/`, a symlinked cwd and spaces handled.

- **CH1 (fold-induced, deferred to backlog #364):** the walk required `run-hook.sh` as a marker, so a linked worktree
  of a branch made BEFORE the launcher existed — every branch open today — was skipped and MAIN's hook ran: a
  pending plan gate 2 -> 0, at the worktree root and under `.claude/worktrees/`. "The old relative form extended to
  subdirectories" was false.
- **CL2, CL3 (deferred to backlog #364):** `dirname` failing past 1024 characters, and command substitution dropping a
  trailing newline, could each pick another checkout.
- **CL4 (fixed):** "main() over the shipped defect exits 1" exited 1 with the defect removed, through a stale default
  registry entry; the case now passes `unregistered={}` and says why.
- **CL5 (deferred):** the seven hand mutations of the launcher were not recorded, and 4 of the reviewer's 12 survived.
  The launcher leaves this PR, so they go with it to backlog #364.
- **CL6 (fixed):** stale prose (title, dashboard, "from anywhere", "at any checkout root").

**Q5, answered here as the method asks:** rounds 2 and 3 both carried findings CAUSED by the previous round's fold, in
ONE component (`hook-launch`). That is THRASHING → architecture review. ⛔ And the ladder was mis-stated in the
round-2 record: the row labeled SPLIT kept both halves together, so it was a second REDESIGN; the owner caught it
("if only 'defer' has left why B suggest architecture review?"). Owner's choice A (2026-10-26): a TRUE split — PR #409
ships the guard half with `.claude/` byte-identical to master; the launcher is backlog #364, designed after the
architecture review. Round 4 reviews the shrunken PR.
