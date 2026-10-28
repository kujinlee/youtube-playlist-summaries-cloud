# Round 4 — `compaction-guards` — coordinator — ⟳ NOT CONVERGED (both halves); the split's bet fired → DEFER the audit

Claude half: `docs/reviews/claude/compaction-guards-r4-claude.md` (wording vs code, on the pinned 6c837787), 2 Major + 7 Minor.

```yaml
round: 4
fixes_nontrivial: true
subject: compaction-guards
halves:
  codex: ran
  claude: ran
findings:
  - {id: X4-1, severity: Medium, aim: deliverable, fix_induced: false, component: snapshot, disposition: fixed}
  - {id: X4-2, severity: Medium, aim: deliverable, fix_induced: false, component: snapshot, disposition: fixed}
  - {id: X4-3, severity: Medium, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: X4-4, severity: Low, aim: deliverable, fix_induced: false, component: audit, disposition: fixed}
  - {id: X4-5, severity: Low, aim: deliverable, fix_induced: false, component: print, disposition: fixed}
  - {id: C4-F1, severity: Medium, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: C4-F2, severity: Medium, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: C4-F3, severity: Low, aim: deliverable, fix_induced: true, component: snapshot, disposition: fixed}
  - {id: C4-F4, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: C4-F5, severity: Low, aim: deliverable, fix_induced: false, component: snapshot, disposition: fixed}
  - {id: C4-F6, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: C4-F7, severity: Low, aim: deliverable, fix_induced: false, component: print, disposition: fixed}
  - {id: C4-F8, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: C4-F9, severity: Low, aim: deliverable, fix_induced: false, component: audit, disposition: fixed}
```

Both halves on `6c837787`. **The split's withdrawals HELD:** neither half could make the audit assert an item was kept or
dropped, or the print show a capture whose nonce did not match — the architecture review's own falsifier did not fire.
Every round-3 reproduction now fails or is a stated bound (XR5). 113/113, 62/62, all 103 mutations at their named cases,
2,439 real, 41 real answers paired in 0.57 s, the 262 MB + 7.9 s `gh` probe at 11.1 s.

**But the decision log's bet FIRED on two clauses, both in the process boundary, not in the withdrawn claims:**
**X4-1** a 512 MiB `compact_summary` keeps PostCompact alive 16.4 s — stdin is joined, decoded and parsed before the
child's timer starts. **X4-2** a grandchild that calls `setpgid(0, 0)` (not `setsid`) survives both a normal return and
the real 11 s kill. Plus **X4-3 / C4-F1 / C4-F2** the PR body, the dashboard entry and `settings.json`'s status message
still describe the withdrawn behaviour; **C4-F3 (fix-induced)** `tag_uncaptured` adds NOT CAPTURED by WORD MATCH on any
line containing CANNOT RUN or TRUNCATED, which is the class the split removed elsewhere.

**Four rounds: thrashing or prose floor? NEITHER.** Only C4-F3 is fix-induced (snapshot); no component carries
fix-induced findings in rounds 3 and 4 consecutively. Two findings are real boundary defects and the rest are prose.

**Route: DEFER the audit, as the bet recorded before the fold named.** X4-2 is the wall a third time in this subject —
"no process the capture started survives" is a negative about arbitrary descendant code, and each named exception
(`setsid`) is followed by the next (`setpgid`). It becomes a STATED BOUND: the hook returns within its bound; capture
calls are killed by process group; a descendant that leaves its group (`setsid`, `setpgid`) is not, and is named.
Deferring the audit also removes PostCompact, whose `compact_summary` is X4-1's input — the largest untrusted payload
these hooks take.
