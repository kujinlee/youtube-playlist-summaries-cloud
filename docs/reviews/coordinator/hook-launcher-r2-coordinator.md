# Round 2 — `hook-launcher` — coordinator — ⟳ NOT CONVERGED; the ACCRETE bet LOST → SPLIT (REDESIGN skipped, reason recorded)

```yaml
round: 2
fixes_nontrivial: false
subject: hook-launcher
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XP1, severity: Medium, aim: deliverable, fix_induced: false, component: launcher, disposition: filed}
  - {id: XP2, severity: Medium, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: XP3, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
```

REVIEW GAP: claude — round 2 alternates to the Codex half (`review-method.md`, *The protocol*, step 4; backlog #339).

`X` = Codex, tree `7771adfe`. HELD: 72/72 under `env -i`, under dash with `LANG=C`, with hostile git config and `TMPDIR`
under a `.git`; 19/19 launcher mutants across EVERY world under `/bin/sh` and dash; 46/46 manifest mutations (both W10
precondition mutations included); exit codes 0/1/2/3/127/255 and binary streams exact; 14 command-only rewrites;
deleted cwd is NOT RUN.

- **XP1 (FILED, backlog #379) — the bet's named failure:** an inherited `BASH_ENV` that `cd`s to `$CLAUDE_PROJECT_DIR`
  made main's probe run through the exact registered command; `SHELLOPTS=xtrace` added stderr traces. Bash honours these
  before ANY script line runs, and the old relative form had the identical exposure — a property of how every hook is
  spawned. Stated as the launcher's limit L8.
- **XP2 (fixed):** the live-falsifier account omitted a PRECONDITION — `refs/remotes/origin/HEAD` must resolve to
  `master`. Codex's first reproduction (clones of a local repo made from this branch, origin/HEAD → `hook-launcher`)
  let BOTH pushes through; with origin/HEAD → master it reproduced exactly: this branch blocked, bare master unchanged,
  master's control pushed. The coordinator's run cloned from GitHub, whose HEAD is master. The row now states it.
- **XP3 (fixed):** the dashboard still said the live check had not run; the self-test docstring said each mutant
  "re-runs every world" (it runs the worlds it names); a case named "JSON-shaped stdout" emits plain text — renamed.

**Route SPLIT, skipping REDESIGN, with the reason in the decision-log row:** no launcher redesign can close a channel
bash consults before the launcher exists. The stable half ships; round 3 confirms the prose. 72 cases; 12 mutations.
