# Round 2 — `session-state` — coordinator — ⟳ NOT CONVERGED (bet LOST); REDESIGN

```yaml
round: 2
fixes_nontrivial: true
subject: session-state
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XP1, severity: High, aim: deliverable, fix_induced: true, component: records, disposition: fixed}
  - {id: XP2, severity: High, aim: deliverable, fix_induced: true, component: records, disposition: fixed}
  - {id: XP3, severity: High, aim: deliverable, fix_induced: true, component: untrusted-text, disposition: fixed}
  - {id: XP4, severity: Medium, aim: deliverable, fix_induced: true, component: records, disposition: fixed}
  - {id: XP5, severity: Medium, aim: deliverable, fix_induced: true, component: deadline, disposition: fixed}
  - {id: XP6, severity: Medium, aim: deliverable, fix_induced: true, component: ledger, disposition: fixed}
  - {id: XP7, severity: Medium, aim: deliverable, fix_induced: true, component: records, disposition: fixed}
  - {id: XL8, severity: Low, aim: deliverable, fix_induced: true, component: ledger, disposition: fixed}
```

REVIEW GAP: claude — round 2 alternates to the Codex half (`review-method.md`, *The protocol*, step 4; backlog #339).

`X` = Codex, tree `1eb2e8b2`. HELD: 60 interleaved ledger writes kept all 60; the truncation window is closed by
`os.replace`; the 50-PR slow-git hook finished in 40.12 s and printed; 100 PRs say MAY BE TRUNCATED; fork, missing ref,
`gh` failures and malformed elements stay visibly unchecked; every live check state classifies correctly; 40/40 and
15/15 mutations real. **LOST** — three P1s and four P2s, every one caused by the r1 fold:

- **XP1:** results keyed by `headRefName`, so a same-named fork and local PR shared one review and lost the fork note.
- **XP2:** `--diff-filter=AM` let a PR that only EDITED an inherited record show that record's verdict as its own.
- **XP3:** `clean()` stripped ASCII controls only; U+2028/U+2029/U+0085 and zero-width characters forged a line and a
  visually matching END marker.
- **XP4:** PR #371's `backlog-249-260-r11-thrashing.md` (NOT CONVERGED) still read as "no coordinator record".
- **XP5:** the deadline missed the ledger read (a FIFO hung the hook to its 60 s kill, empty output), the hook's stdin
  drain, and calls launched after expiry.
- **XP6:** damaged ledger bytes were rewritten as U+FFFD; a Unicode separator inside a ledger value broke the ledger's
  own `splitlines()`, turning one job into two damaged lines.
- **XP7:** the review-half count was printed only when no record was found, though the prose said it always was.
- **XL8:** the lock sidecar `.claude/inflight.jsonl.lock` was not gitignored.

Every P1 came from INTERPRETING review semantics out of filename conventions. Route REDESIGN (decision-log row
written before round 3): the block says less, from sturdier sources — keyed by PR number; per PR the branch's latest
commit subject and a count of review files the PR ADDED; no record headings, no bets; `clean()` by Unicode category;
no stdin read; a regular-file ledger split on `\n` only, written ASCII-escaped, damaged lines kept byte-for-byte; no
call launched past the budget; the lock sidecar ignored.
