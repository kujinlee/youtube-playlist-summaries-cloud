# Round 1 — `diff-coverage-zeros` — coordinator — ⟳ NOT CONVERGED (both halves); ACCRETE

```yaml
round: 1
fixes_nontrivial: true
subject: diff-coverage-zeros
halves:
  codex: ran
  claude: ran
findings:
  - {id: XP1, severity: Medium, aim: deliverable, fix_induced: true, component: manifests, disposition: fixed}
  - {id: CH1, severity: High, aim: deliverable, fix_induced: true, component: tests, disposition: fixed}
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: true, component: manifests, disposition: fixed}
  - {id: CM2, severity: Medium, aim: deliverable, fix_induced: false, component: diff-read, disposition: fixed}
  - {id: CM3, severity: Medium, aim: deliverable, fix_induced: true, component: tests, disposition: fixed}
  - {id: CM4, severity: Medium, aim: deliverable, fix_induced: true, component: tests, disposition: fixed}
  - {id: CL1, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
  - {id: CL2, severity: Low, aim: deliverable, fix_induced: true, component: manifests, disposition: fixed}
  - {id: CL3, severity: Low, aim: deliverable, fix_induced: false, component: report, disposition: fixed}
  - {id: CL4, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
```

`X` = Codex, `C` = Claude, both on `3d9ba10a`, git 2.49. Both: the three round-4 fixtures FIXED (lone CR NOT CHECKED;
textconv WARN; uncommitted manifest refused); 52/52; 30/30 mutations killed by their named cases; `diff.<drv>.command`,
`core.autocrlf`, `diff.noprefix`, `color.diff=always`, `diff.mnemonicPrefix`, source `eol`/filters and `core.attributesFile`
all preserved the warning.

- **XP1 = CM1 (fixed, by replacing the mechanism):** `git status` cannot see five working-tree states the loader reads —
  an ignored manifest, `assume-unchanged`, `skip-worktree`, a clean filter, a symlink — each reproduced as a clean zero.
  The manifests are now read from HEAD's OBJECT STORE (`snapshot_head_manifests`: blobs into a temp tree, handed to the
  same `load_manifests`), the revision the sources come from. CM4 (two `--untracked-files` mutations survived) and CL1/CL2
  (a wrong "status failed" message; a staged-then-reverted refusal) go with the status check.
- **CH1 (fixed):** the real-git fixtures inherited `GIT_DIR` — pointed at a victim repo, the suite committed six times into
  it and still passed. Fixtures now run isolated, AND `run_check` strips the redirecting variables from every git call
  (`unredirected()`); a case exports `GIT_DIR` at a victim and asserts it byte-identical. ⚠ The finding's aside was TRUE OF
  THE LIVE REPO: a 2026-09-14 `codex-review.py` fixture had written `user.name=t`/`t@example.com`, `gpgsign=false` and a temp
  `core.hooksPath` into `.git/config`, and **355 branch commits** since were authored as `t`. Repaired (backup kept); the
  class across five other fixtures is backlog #373.
- **CM2 (fixed):** the DIFF was still read with `text=True`; a lone CR on a deleted line forged a `diff --git` header and
  dropped the file's later hunks. One bytes helper now serves every call; a real-git case.
- **CM3 (fixed):** `commit.gpgsign=true` or a failing global hook crashed the suite — fixtures use `GIT_CONFIG_GLOBAL=/dev/null`.
- **CL3 (fixed):** a range changing no manifested script said "every one is edited"; it now says nothing was measured.
- **CL4 (fixed):** the PR body called a `show --no-textconv` mutation "equivalent"; the mechanism case would catch it.

The fold's own first attempt failed the harness CONTROL — its `REPO_ROOT` cases ran real `ls-tree` inside the harness's
staged copy, which is no repository; they now mirror the checkout, and the real-git path is the `world()` cases. One new
mutation (the snapshot reading the working tree via `cwd`) was EQUIVALENT by construction and was dropped, not bent to fit.
Route ACCRETE (decision-log row written before round 2). 56 cases; 30 mutations, each killed by its named case.
