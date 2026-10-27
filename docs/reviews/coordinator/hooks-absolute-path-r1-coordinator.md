# Round 1 — `hooks-absolute-path` — coordinator — ⟳ NOT CONVERGED (both halves); REDESIGN

```yaml
round: 1
fixes_nontrivial: true
subject: hooks-absolute-path
halves:
  codex: ran
  claude: ran
findings:
  - {id: XH1, severity: High, aim: deliverable, fix_induced: false, component: hook-launch, disposition: fixed}
  - {id: XH2, severity: High, aim: deliverable, fix_induced: false, component: guard-rule, disposition: fixed}
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: false, component: guard-rule, disposition: fixed}
  - {id: XL4, severity: Low, aim: deliverable, fix_induced: false, component: guard-rule, disposition: fixed}
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: false, component: guard-rule, disposition: fixed}
  - {id: CM2, severity: Medium, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: CL1, severity: Low, aim: deliverable, fix_induced: false, component: guard-rule, disposition: fixed}
  - {id: CL2, severity: Low, aim: deliverable, fix_induced: false, component: guard-rule, disposition: fixed}
  - {id: CL3, severity: Low, aim: deliverable, fix_induced: false, component: tests, disposition: fixed}
  - {id: CL4, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: CL5, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

`X` = Codex, `C` = Claude, both on tree `3f861b99`. Both: 19/19; each of the six mutations red via its case.

- **XH1 — fixed by REDESIGN:** anchoring every command at `$CLAUDE_PROJECT_DIR` ran the MAIN checkout's hooks from a
  linked worktree (the variable names the checkout the session started in). Codex executed it: a pending plan gate
  in the worktree, exit 2 under the old command, exit 0 under the new one. Claude ran the same world and called it a
  behaviour change, not a regression. The halves disagree on the label, not on the fact. Every hook is now launched
  by `.claude/hooks/run-hook.sh <name>.sh`, which runs the hook from the checkout CONTAINING the cwd when that checkout
  shares this repo's `--git-common-dir`, and the project dir otherwise. Behaviour at any checkout root is what the
  relative form gave; a subdirectory now works. Witnessed by real-git cases (a linked worktree's subdirectory with the
  project dir naming main runs the WORKTREE's hook; an unrelated repo with the same hook runs the PROJECT's).
- **XH2 = CM1, XM3 = CL1, XL4 = CL2 — fixed by the same REDESIGN:** the denylist of relative tokens was bypassed by
  `sh -c`, `"$PWD"/`, `cd … &&`, `FOO=… $FOO`, `||true` and `$CLAUDE_PROJECT_DIRX`, missed a dangling absolute path, and
  refused harmless argument mentions. The guard is now an ALLOWLIST of exactly one command shape; every listed
  bypass is a case, each refused.
- **CM2 (fixed):** "`check-ratchet-contract`'s caller rule is covered" was false — `check-memory-index-budget.sh` is in
  `.claude/hooks/` and registered nowhere. The guard now refuses an unregistered hook file without a written reason
  (`UNREGISTERED`, which names that one and why), and refuses a stale entry.
- **CL3 (fixed):** two cases passed for a reason other than their name, and a top-level JSON array is now a CANNOT
  RUN case.
- **CL4, CL5 (fixed, prose):** `surface-recall.sh`'s comment quoted the old command form; the backlog #223 row now
  names PR #409, and the PR body no longer claims the live check is impossible before merge.

⚠ The mutation runner runs `python3 <file> --self-test`, so it cannot mutate `run-hook.sh`. Six launcher mutations
were applied BY HAND (round-1 design "always the project dir"; no common-dir check; arguments passed through;
path-shaped names accepted; git toplevel never consulted; a missing hook exits 0), and each turned its named case red.
The Python guard has 13 mutations in the manifest, 13 killed and attributed (scoped run).
