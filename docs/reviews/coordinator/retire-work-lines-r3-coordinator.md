# Round 3 — `retire-work-lines` (PR #434, backlog #389) — coordinator — NOT CONVERGED (Codex); SPLIT: walk the chain, bound the rest

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 3
fixes_nontrivial: true
subject: retire-work-lines
halves:
  codex: ran
  claude: gap
findings:
  - {id: Z1, severity: Medium, aim: deliverable, fix_induced: false, component: retirement, disposition: fixed}
```

Codex on `2dee42b2`, told not to quote plan text (and the review text was leak-scanned before it was read: 0 hits).
**Z1** an alias chain that passes THROUGH a retired symlink (`chain → alias → work-lines.html → live.html`) serves and
lists stale content: resolution erases the intermediate retired name, and the inode rule excludes a symlinked retired
entry by design. Reproduced at round 2's `4b8dda56` too — pre-existing. **Held:** hard links, symlinked directories,
Unicode case folding, NFC/NFD, trailing dots and spaces, encoded slashes, below-root aliases; the leak scan at 0 with its
positive control, plus wrapped quotations, short fragments and slugs (no new disclosure); 348 scoped mutations; 2,504.

**Route: SPLIT** (the r2 identity bet lost on this clause). The decidable half ships: walk the symlink chain link by
link (`os.readlink`, bounded length, staying inside the served root), and retire the request if ANY name it traverses
is a retired name, casefolded — in the handler, the index and `/latest` alike. STATED BOUND: a chain leaving the served
root, or longer than the bound, is not followed and is refused (not served), and the PR body narrows its alias claim
to exactly that.
