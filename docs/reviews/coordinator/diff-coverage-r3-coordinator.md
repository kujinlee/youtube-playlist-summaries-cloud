# Round 3 — `diff-coverage` — coordinator — ⟳ NOT CONVERGED (bet LOST); SPLIT

```yaml
round: 3
fixes_nontrivial: true
subject: diff-coverage
halves:
  codex: skipped
  claude: ran
findings:
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: true, component: ci-surface, disposition: deferred}
  - {id: CM2, severity: Medium, aim: deliverable, fix_induced: false, component: decision-lines, disposition: fixed}
  - {id: CM3, severity: Medium, aim: deliverable, fix_induced: true, component: deletions, disposition: deferred}
  - {id: CM4, severity: Medium, aim: deliverable, fix_induced: false, component: diff-parse, disposition: fixed}
  - {id: CM5, severity: Medium, aim: deliverable, fix_induced: false, component: tests, disposition: fixed}
  - {id: CL1, severity: Low, aim: deliverable, fix_induced: false, component: diff-parse, disposition: fixed}
  - {id: CL2, severity: Low, aim: deliverable, fix_induced: false, component: decision-lines, disposition: fixed}
  - {id: CL3, severity: Low, aim: deliverable, fix_induced: false, component: coverage-rule, disposition: deferred}
  - {id: CL4, severity: Low, aim: deliverable, fix_induced: false, component: diff-parse, disposition: fixed}
  - {id: CL5, severity: Low, aim: deliverable, fix_induced: true, component: deletions, disposition: deferred}
  - {id: CL6, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

REVIEW GAP: codex — round 3 alternates to the Claude half (`review-method.md`, *The protocol*, step 4; backlog #339).

`C` = Claude, tree `263dfc28`. HELD — the r2-redesigned coverage rule: a re-created line counts as unedited and an
insertion edits nothing on every constructed edge case; 48/48; 24/24; 57 and 32 reproduce with
`check-hook-commands.py:80` among the 32; 3.5 s on an 87k-line diff.

- **CM1 (DEFERRED to backlog #370):** the PR-only warn step follows `check-review-recorded`, red on every draft round, so
  it never ran on this PR — the r1 annotations have never appeared; Actions also caps annotations at 10 per step.
- **CM3, CL5 (DEFERRED to backlog #370):** the deleted-lines path still clean-zeroes a rename that drops its manifest and a
  manifest-only deletion, and 31 of 110 deletion warnings over the last 40 merges were MOVED lines.
- **CM2 (fixed):** the `self_test` exemption matched any name containing it — 14 decision lines of real code skipped.
  Exact names now.
- **CM4 (fixed):** `git diff` was unpinned: `diff.external` gave a clean zero, `diff.srcPrefix` a wrong path. Now
  `--no-ext-diff --src-prefix=a/ --dst-prefix=b/`.
- **CL1 (fixed):** an added line starting `++ ` was read as a file header; headers are now read only inside a header block.
- **CL2, CL4 (fixed):** a lone CR shifted numbering (now NOT CHECKED); text came from `splitlines()` (now `split("\n")`); the
  working tree was read against a HEAD diff (now `git show HEAD:<path>`).
- **CM5 (fixed):** an unparseable HEAD source, a failed HEAD read and `while` had no case; each has one and a mutation.
- **CL3 (DEFERRED, Low):** difflib can align a repeated line to the wrong copy — constructed only; no real edit clears
  wrongly.
- **CL6 (fixed, prose):** "one mutation per round-2 finding", "each warning is an annotation" and "never a silent zero"
  overclaimed.

**Usefulness, measured by the reviewer:** up to 420 warnings per PR over the last 40 merges. At that volume a CI warning
is a census, not a pointer — the backlog #56 risk.

Route SPLIT (decision-log row written before round 4): ship the STABLE half — the core rule as a LOCAL tool, its
`--self-test` in CI, with its own correctness fixes above. The UNSTABLE half — CI delivery, annotations, volume, and the
deleted-lines path — is backlog #370. 45 cases; 24 mutations (7 retired with the code they guarded).
