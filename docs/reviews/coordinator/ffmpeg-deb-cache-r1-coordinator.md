# Round 1 — `ffmpeg-deb-cache` — coordinator — ⟳ NOT CONVERGED (both halves); ACCRETED

```yaml
round: 1
fixes_nontrivial: true
subject: ffmpeg-deb-cache
halves:
  codex: ran
  claude: ran
findings:
  - {id: XP1, severity: High, aim: deliverable, fix_induced: false, component: cache-integrity, disposition: fixed}
  - {id: XP2, severity: High, aim: deliverable, fix_induced: false, component: cache-steps, disposition: fixed}
  - {id: XP3, severity: Medium, aim: deliverable, fix_induced: false, component: cache-key, disposition: fixed}
  - {id: XP4, severity: Medium, aim: deliverable, fix_induced: false, component: budget, disposition: fixed}
  - {id: CF1, severity: Medium, aim: deliverable, fix_induced: false, component: cache-integrity, disposition: fixed}
  - {id: CF2, severity: Medium, aim: deliverable, fix_induced: false, component: budget, disposition: fixed}
  - {id: CF3, severity: Low, aim: deliverable, fix_induced: false, component: cache-steps, disposition: fixed}
  - {id: CF4, severity: Low, aim: deliverable, fix_induced: false, component: cache-key, disposition: fixed}
  - {id: CF5, severity: Low, aim: deliverable, fix_induced: false, component: cache-key, disposition: declined}
```

`X` = Codex (P1/P2 = High/Medium), `C` = Claude; both on the first PR #407 tree. Claude read CI: run 40397292037 missed
and saved; run 40400167030 restored 81 files, `Need to get 0 B/66.4 MB`. The cache WORKS; two of its claims were false.

- **XP1 = CF1 (fixed):** "apt still verifies every package" is false — apt accepts a cached .deb by SIZE (both halves,
  in containers: a forged/random same-size file passed `--download-only`). Now the key step writes a SHA256 manifest
  from the signed index and only matching restored files are copied in. Verified in `ubuntu:26.04`: 194 listed, a
  forged file rejected and re-downloaded.
- **XP2 = CF3 (fixed):** a hung `--print-uris` or a restore error could fail a step and SKIP the install; all three
  cache steps are now `continue-on-error` with timeouts, and `--print-uris` is bounded and its status checked.
- **XP3 = CF4 (fixed):** the key was built from MD5 lines and the install's second `apt-get update` could drift from
  it; now `ForceHash=SHA256`, and the install reuses the key step's index.
- **XP4 = CF2 (fixed):** the budget omitted restore and save; restated per path (28.3 / 26.0 of 30 min).
- **CF5 (declined):** a changed package set is still a full cold download (no `restore-keys`). A fallback key is
  safe now that every file is hash-checked, but it is an optimisation, not a defect — left for backlog #358's
  20-run observation to justify.
- Also fixed: the save copied every `.deb` in the archive dir; it now copies only manifest files.

Route: ACCRETE (decision-log row written before this fold). Round 2 is a confirmation round.
