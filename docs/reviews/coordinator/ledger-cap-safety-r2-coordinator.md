# Round 2 — `ledger-cap-safety` — coordinator — ⟳ NOT CONVERGED; DEFER (rungs skipped, reason recorded): filed, merge on READY

```yaml
round: 2
fixes_nontrivial: false
subject: ledger-cap-safety
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XP1, severity: High, aim: deliverable, fix_induced: false, component: lock, disposition: filed}
  - {id: XP2, severity: High, aim: deliverable, fix_induced: false, component: ledger-read, disposition: filed}
  - {id: XP3, severity: Medium, aim: deliverable, fix_induced: false, component: ledger-read, disposition: filed}
  - {id: XP4, severity: Medium, aim: deliverable, fix_induced: true, component: tests, disposition: filed}
  - {id: XP5, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

REVIEW GAP: claude — round 2 alternates to the Codex half (`review-method.md`, *The protocol*, step 4; backlog #339).

`X` = Codex, tree `2bd3ff94`, on macOS AND Linux. HELD — backlog #369's own subject: no erasure past the cap; the
exact-cap boundary; growth between `fstat` and `read` refused (exit 2, bytes unchanged); `O_NONBLOCK` on a regular file
reads whole; raw U+2028/U+0085 stay one job and `clean()` keeps one END marker; no false `NO CHECKS` for any rollup type;
the r1 symlinked-lock and symlinked-ledger attacks are refused; 51/51 on both platforms; 25/25 mutations real.

- **XP1, XP2, XP3 (FILED, backlog #372):** each needs an adversary manipulating the ledger's directory DURING a write —
  deleting the lock sidecar between writers (a three-writer lost update returns), retargeting a symlinked `.claude`
  directory mid-add (another directory's ledger overwritten), or hard-linking the ledger (an alias detaches). Each also
  breaks master's ledger, which has no lock-identity, size or symlink protection at all.
- **XP4 (FILED, backlog #372):** the at-cap update case checks no return value or contents, and the Unicode rewrite case
  removes its only Unicode entry, so neither establishes the property its name states.
- **XP5 (fixed, prose):** the PR body's counts were stale (45/21); the dashboard named the removed `_whole()` and said the
  ledger "can no longer wipe itself"; the backlog said UTF-8 writes "cannot re-inflate past the cap" (JSON spacing can,
  and is refused safely).

**Route DEFER, skipping REDESIGN and SPLIT, with the reason recorded in the decision-log row:** making a per-checkout,
gitignored scratch file tamper-proof against concurrent filesystem races is out of proportion to what it protects, and
#369's own subject held. Decided under the owner's standing rule; not critical (no shared, production or record data).
PR #413 merges on READY — it strictly improves on master.
