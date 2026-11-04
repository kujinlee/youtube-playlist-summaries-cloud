# Round 4 — `spawn-line-500` (backlog #500, PR #500) — coordinator — CONVERGED (Codex)

```yaml
round: 4
fixes_nontrivial: false
subject: spawn-line-500
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Low, aim: deliverable, fix_induced: true, component: docs, disposition: fixed}
```

REVIEW GAP: claude — alternation (rounds 2+ run ONE half; Claude ran r3).

Codex reviewed `ea744cf7` and CONVERGED. It measured:
- 60,000 calendar and verdict inputs across six zones, including Lord Howe's 30-minute shift and probes of nonexistent
  midnights in Santiago and Beirut;
- `pct_up` at the requested edges, at adjacent floats and on 200,000 random values;
- end-to-end spawn hooks over 4 MiB hostile meter logs, at 0.22–1.66 s, each denying correctly;
- 302/302 self-test cases, with four hand-run mutations (DST, rounding, the day floor, blank-line timing) each killed
  by its named case.

- **X1 (Low, not a BLOCKER; FIXED, an exception to the §0 Q4c cap, stated):** backlog row 404's FAILS IF still read
  "with the cache at 90% or more". This occurrence was missed by r3 C6's fix, which corrected the same row's title.
  It is a one-phrase completion of a fix already dispositioned, with no behaviour to review. Filing a backlog row to
  change one phrase in another row would cost more than the edit. The fix_induced flag is true because the miss is
  r3's own fix. No other round shows that pattern, so this is not thrashing.
