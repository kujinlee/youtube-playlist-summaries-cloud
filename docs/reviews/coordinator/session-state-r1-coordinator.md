# Round 1 — `session-state` — coordinator — ⟳ NOT CONVERGED (both halves); ACCRETE

```yaml
round: 1
fixes_nontrivial: true
subject: session-state
halves:
  codex: ran
  claude: ran
findings:
  - {id: CB1, severity: High, aim: deliverable, fix_induced: false, component: records, disposition: fixed}
  - {id: CB2, severity: High, aim: deliverable, fix_induced: false, component: ledger, disposition: fixed}
  - {id: XP1, severity: High, aim: deliverable, fix_induced: false, component: ledger, disposition: fixed}
  - {id: XP2, severity: High, aim: deliverable, fix_induced: false, component: ledger, disposition: fixed}
  - {id: XP3, severity: High, aim: deliverable, fix_induced: false, component: deadline, disposition: fixed}
  - {id: XP4, severity: High, aim: deliverable, fix_induced: false, component: records, disposition: fixed}
  - {id: XP5, severity: Medium, aim: deliverable, fix_induced: false, component: records, disposition: fixed}
  - {id: XP6, severity: Medium, aim: deliverable, fix_induced: false, component: enumeration, disposition: fixed}
  - {id: XP7, severity: High, aim: deliverable, fix_induced: false, component: untrusted-text, disposition: fixed}
  - {id: XP8, severity: Medium, aim: deliverable, fix_induced: false, component: tests, disposition: fixed}
  - {id: CM5, severity: Medium, aim: deliverable, fix_induced: false, component: ledger, disposition: fixed}
  - {id: CL10, severity: Low, aim: deliverable, fix_induced: false, component: enumeration, disposition: fixed}
  - {id: CL13, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

`X` = Codex, `C` = Claude, both on `89bb0f9d`; 28/28 and 11/11 mutations real on both. Every finding is one property —
the block must never be FALSELY REASSURING — failing in a different place:

- **CB1 = XP5 (fixed):** records were looked up by BRANCH NAME; subjects are not named like branches, so PR #392 and
  PR #371 showed no review and nothing said one was looked for. Now keyed by what the PR itself added
  (`git diff origin/master...origin/<b> -- docs/reviews/`), and "none added" / "no coordinator record, but N review
  files" is printed.
- **CB2 (fixed in wording; automation filed as backlog #366):** nothing writes the ledger, so "empty" printed while
  jobs ran. It now says "none RECORDED — written by hand, so empty is not proof that nothing is running".
- **XP1, XP2, CM5 (fixed):** unlocked read-modify-write lost jobs (20 concurrent adds kept 3), a truncation window read
  as empty, the next write erased unreadable lines, and a non-UTF-8 byte crashed the whole block. `flock` + atomic
  `os.replace`; unreadable lines (bad JSON or bad UTF-8) are reported and KEPT.
- **XP3 (fixed):** 20 s per call × up to 3 calls per PR overran the hook's 60 s kill, and a killed hook prints nothing.
  One 40 s total deadline; past it the remaining PRs are counted as NOT READ and the block still prints.
- **XP4 (fixed):** a fork PR with our branch's name showed our review. Forks are now noted as not read; a local ref at
  another commit than the PR head is flagged.
- **XP6, CL10 (fixed):** a full list said nothing about truncation; bad decision-log rows and a non-object PR element
  were skipped or crashed. Truncation is flagged at the limit; bad rows are counted; malformed `gh` output is CANNOT RUN.
- **XP7 (fixed):** a newline in a ledger id or decision-log text could forge `=== END IN FLIGHT ===`. `clean()` collapses
  control characters and breaks `===` in every external value.
- **XP8 (fixed):** "main() prints the block" checked only the exit code; it now asserts the printed block.
- **CL13 (prose):** backlog #364 is cited — it is on master since PR #409 merged (`4aaa6ed7`).

Verified, not just plausible (Claude half): Claude Code 2.1.309 turns SessionStart plain stdout into a model message,
and this session's transcript shows the `remember` plugin's block arriving that way after every compaction.

Route ACCRETE (decision-log row written before round 2): each finding patched where it lives. 40 cases; 15 mutations,
each killed by its named case — including one per r1 defect class (lock, kept lines, deadline, clean, none-said,
none-RECORDED, the print).
