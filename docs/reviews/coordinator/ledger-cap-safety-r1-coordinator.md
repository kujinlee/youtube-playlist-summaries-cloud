# Round 1 — `ledger-cap-safety` — coordinator — ⟳ NOT CONVERGED (both halves); ACCRETE

```yaml
round: 1
fixes_nontrivial: true
subject: ledger-cap-safety
halves:
  codex: ran
  claude: ran
findings:
  - {id: XP1, severity: High, aim: deliverable, fix_induced: false, component: lock, disposition: fixed}
  - {id: XP2, severity: Medium, aim: deliverable, fix_induced: false, component: ledger-read, disposition: fixed}
  - {id: XP3, severity: Medium, aim: deliverable, fix_induced: false, component: tests, disposition: fixed}
  - {id: CF1, severity: Medium, aim: deliverable, fix_induced: true, component: ledger-read, disposition: fixed}
  - {id: CF2, severity: Low, aim: deliverable, fix_induced: true, component: ledger-read, disposition: fixed}
  - {id: CF3, severity: Low, aim: deliverable, fix_induced: false, component: ledger-write, disposition: fixed}
  - {id: CF5, severity: Low, aim: deliverable, fix_induced: false, component: enumeration, disposition: fixed}
  - {id: CF6, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
  - {id: CF7, severity: Low, aim: deliverable, fix_induced: false, component: tests, disposition: fixed}
```

`X` = Codex, `C` = Claude, both on `c3a2b169`. Both: 45/45; 21/21 mutations killed by their named cases; the cap
boundaries (exactly at the cap read whole, landing exactly at the cap accepted, one byte over refused), 20 concurrent adds
near the cap, a huge id, the real hook with an oversized ledger (exit 0, full block), and every rollup type held.

- **CF1 + CF2 (fold-induced, fixed):** `_whole()` RE-IMPLEMENTED `read_ledger`'s two refusal rules, and nothing tied them:
  changing only `read_ledger`'s `>` to `>=` brought the erasure back with all 45 green; and the two stats left a window a
  lock-ignoring writer could use. Now ONE rule — `_read_whole()`: `open(O_NOFOLLOW)`, `fstat`, one read on that fd — serves
  the block and every update, and a mutation makes that one rule drift.
- **XP1 (fixed):** a lock file symlinked to the ledger followed the replaced inode, and three concurrent adds lost one.
  The lock is opened with `O_NOFOLLOW`.
- **XP2 (fixed):** a symlinked ledger was replaced by a regular file, detached from its target. Refused now.
- **CF3 (fixed):** writes re-escaped non-ASCII, so a 60 KB ledger "grew" past the cap and refused the `--done` that would
  trim it. Writes are UTF-8 now; a raw U+2028 is safe because the reader splits on `\n` only.
- **XP3 = CF4 (fixed):** the "None" rollup case tested a MISSING key; an explicit `null` is now its own case.
- **CF5 (fixed):** the row's "require each PR element's fields" was undone — a PR missing them now says UNREADABLE.
- **CF6 (fixed):** the `read_ledger` docstring still described the erasure as current.
- **CF7 (fixed):** the `S_ISREG` refusal now has its own mutation.

Route ACCRETE (decision-log row written before round 2). 51 cases; 25 mutations, each killed by its named case.
