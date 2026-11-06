# Round 1 — `running-vs-owed` — coordinator — NOT CONVERGED, both folded

REVIEW GAP: claude — weekly usage at 97% (stop 98.3%); the Codex half ran. Codex: `docs/reviews/codex/running-vs-owed-r1-codex.md`, on `a71e86ae`.

```yaml
round: 1
fixes_nontrivial: true
subject: running-vs-owed
halves:
  codex: ran
  claude: gap
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: false, component: agenda-digest, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: false, component: agenda-digest, disposition: fixed}
```

Both findings are about IDENTITY: the split classified by the leaf's worst state and merged by display label, so
neither knew which PR a thread's work is.

- **H1** — `derive_thread` now records `open_prs`: every named PR that is open, plus the one a backlog-only row resolved
  to, read whatever the leaf's worst state. A thread with an open PR runs even when its row cannot be read. A case
  through the real `derive` (PR #30 + backlog #11, backlog unread, a ledger entry); two mutations.
- **M1** — each item carries a `key` (its first open PR, else its label), and `agenda_now_items` merges by it: one PR
  reached as PR #30 and as a row whose title resolves to it is ONE item, and a wait on either holds it. Two cases
  through `derive`; two mutations. One older mutation re-bound to the new merge line.
