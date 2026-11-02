# Round 2 — `hooks-absolute-path` — coordinator — ⟳ NOT CONVERGED (bet LOST); SPLIT

```yaml
round: 2
fixes_nontrivial: true
subject: hooks-absolute-path
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XH1, severity: High, aim: deliverable, fix_induced: true, component: hook-launch, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: true, component: hook-launch, disposition: fixed}
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: true, component: hook-launch, disposition: fixed}
  - {id: XL4, severity: Low, aim: deliverable, fix_induced: true, component: tests, disposition: fixed}
```

REVIEW GAP: claude — round 2 alternates to the Codex half (`review-method.md`, *The protocol*, step 4; backlog #339).

`X` = Codex, tree `6178e305`. 32/32; all six hand mutations of the launcher red via their cases; every round-1
bypass refused; round 1's plain linked-worktree plan-gate world now blocks; stdin intact, zero arguments forwarded;
a direct push-hook call from `scripts/` returned `permissionDecision: deny`. **The launcher half of the bet was LOST:**

- **XH1 (fold-induced, fixed by SPLIT):** the launcher scrubbed three `GIT_*` variables but not
  `GIT_CEILING_DIRECTORIES`; with it set, discovery failed and selection fell back to the project (main) checkout, so a
  worktree's pending plan gate was ignored (2 -> 0) — round 1's failure through a new door.
- **XM2 (fold-induced, fixed):** a submodule root selected the parent project (the common-dir test calls it
  unrelated), contradicting "behaviour at any checkout root is what the relative form gave".
- **XM3 (fold-induced, fixed):** hook existence took part in SELECTION, so a hook missing in the worktree ran MAIN's
  copy instead of reporting NOT RUN.
- **XL4 (fixed):** mutation "main() ignores the root" was killed by two other cases, not the one it names (the named
  case passed for an ambient reason: the real repo's deliberately unregistered hook also gives 1); the prose said 29
  cases where the suite has 32.

All three launcher findings share one root: selection ASKED GIT, and git's answer can be steered by the environment or
fail. Route SPLIT (decision-log row written before round 3): the guard, which held, is kept; selection walks up from the
physical cwd to the nearest directory with both `.git` and `run-hook.sh` and uses it, with no git process — the old
relative form extended to subdirectories. A missing hook there is NOT RUN. Measured cost in r2: about 14 ms per launch
before, 51–54 ms with three git probes; the git-free walk removes the probes.
