# Round 1 — `held-pins-head` (PR #541, backlog #538) — coordinator — NOT CONVERGED (both halves)

```yaml
round: 1
fixes_nontrivial: true
subject: held-pins-head
halves:
  codex: ran
  claude: ran
findings:
  - {id: X-F1, severity: High, aim: deliverable, fix_induced: false, component: head-extract, disposition: fixed}
  - {id: X-F2, severity: Medium, aim: deliverable, fix_induced: false, component: isolation, disposition: fixed}
  - {id: C-F1, severity: High, aim: deliverable, fix_induced: false, component: display-source, disposition: fixed}
  - {id: C-F2, severity: Medium, aim: deliverable, fix_induced: false, component: isolation, disposition: fixed}
  - {id: C-F3, severity: Low, aim: deliverable, fix_induced: false, component: suite-cost, disposition: fixed}
```

Codex (`docs/reviews/codex/held-pins-head-r1-codex.md`) and Claude (`docs/reviews/claude/held-pins-head-r1-claude.md`)
both reviewed `a4177e28`.

- **C-F1 (High).** The DISPLAY side is still parsed by the working tree's `pin_display`. A dirty harness on disk still
  turns an honest pin fall into READY; this is reproduced. The fold takes `pin_display` and the held pins from ONE
  module, built from HEAD, for both reads.
- **X-F1 (High).** `git archive` applies export attributes (`export-subst`, `export-ignore`), so HEAD's harness can be
  rewritten in the extract. Claude reports ruling out export rules. Codex reports a reproduction. Per house rule, the
  half that reports a finding wins until it is traced. The fold sidesteps the dispute: it materialises HEAD's
  `scripts/` from raw blobs (`git ls-tree` + `git cat-file`), which no attribute or filter can rewrite. It keeps
  Codex's repro as a case.
- **X-F2 and C-F2 (Medium).**
  - Modules without a file escape the isolation and survive a failed import.
  - The restore is untested: deleting the whole `finally` body survives the suite, because the test's own
    snapshot masks it.

  The fold adds a case asserting that `sys.path` and `sys.modules` are unchanged after a successful read and after a
  failing one, with mutations on the restore, and handles modules that have no file.
- **C-F3 (Low).** Most of the added +8 s is recompiling the 523 KB harness 62 times. The fold caches the compile by
  source hash, which keeps every case and makes no coverage change.
