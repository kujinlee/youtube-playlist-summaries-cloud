# Round 1 — `trim-hook-floor` — coordinator — ⟳ NOT CONVERGED (both halves); ACCRETE

```yaml
round: 1
fixes_nontrivial: true
subject: trim-hook-floor
halves:
  codex: ran
  claude: ran
findings:
  - {id: S1, severity: Blocking, aim: deliverable, fix_induced: false, component: owner-wait-matcher, disposition: fixed}
  - {id: S2, severity: High, aim: deliverable, fix_induced: false, component: owner-words, disposition: fixed}
  - {id: S3, severity: Medium, aim: deliverable, fix_induced: false, component: compact-instructions, disposition: fixed}
  - {id: S4, severity: Medium, aim: deliverable, fix_induced: false, component: ordering, disposition: fixed}
  - {id: S5, severity: Medium, aim: deliverable, fix_induced: false, component: recovery-path, disposition: fixed}
  - {id: S6, severity: Medium, aim: deliverable, fix_induced: false, component: not-captured-cut, disposition: fixed}
```

Both halves ran on `edcba890` and agree on the root: the trim made the strict `WAITS-ON-OWNER:` prefix the SOLE visibility
gate for the in-flight block, and the print dropped the owner's recorded words, so two classes of "the owner decided or is
waiting to decide" stopped reaching the coordinator on every turn.

- **S1 (Claude F1 Blocking; Codex HIGH 1).** Measured on the real ledger: 3 of its 5 owner waits are written
  `WAITS-ON-OWNER (card …)`, so the strict prefix missed them; five standing `OWNER hh:mm` instructions vanished too, and
  an unmarked "pending owner approval" entry printed `0 waiting on the OWNER`.
- **S2 (Claude F2 High; Codex HIGH 2).** The digest kept the "owner's recent words" headings and none of the answers or
  prompts, while a retained heading said "the other 59 NOT CAPTURED here". The case at `compaction-state.py:1240` asserted
  an owner prompt ABSENT.
- **S3 (Claude F3).** The `/compact instructions:` line of the title block was dropped.
- **S4 (Codex MEDIUM 3; Claude F4).** "Newest" was file order, not `at`.
- **S5 (Codex MEDIUM 4).** The printed `full:` path was relative and, in a linked worktree, resolved to the wrong checkout.
- **S6 (Codex MEDIUM 5).** A cut at 200 characters removed the `NOT CAPTURED` marker the digest promised to keep.

**Root cause:** the first cut optimised the size and defined "owner" by one spelling and one section. **Route: ACCRETE.**
The rule the fold holds to: nothing the owner decided, or is waiting to decide, is ever trimmed; only routine items are.
The fold widens the in-flight matcher (any form of the marker, `(card`, an `OWNER` instruction, approval text in `what` or
`on_done`), normalises the marker `--add` writes, names every hidden entry's id, sorts by `at`, prints the absolute main
checkout path, keeps the owner's words and the title block in the digest, and keeps the marker through a cut.

**Cost, stated rather than hidden:** correctness beats the size target. On the real ledger the in-flight block falls from
11,716 to 8,550 characters (not to about 2,600) and the snapshot from 7,527 to 3,638.
