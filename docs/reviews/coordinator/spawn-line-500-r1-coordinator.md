# Round 1 — `spawn-line-500` (backlog #500, PR #500) — coordinator — NOT CONVERGED (both halves)

```yaml
round: 1
fixes_nontrivial: true
subject: spawn-line-500
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: false, component: line-note, disposition: declined}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: pace-line, disposition: fixed}
  - {id: X3, severity: Low, aim: deliverable, fix_induced: false, component: docstring, disposition: fixed}
  - {id: C1, severity: High, aim: deliverable, fix_induced: false, component: meter-read, disposition: fixed}
  - {id: C2, severity: Low, aim: deliverable, fix_induced: false, component: self-test, disposition: fixed}
  - {id: C3, severity: Low, aim: deliverable, fix_induced: false, component: pace-line, disposition: fixed}
  - {id: C4, severity: Low, aim: deliverable, fix_induced: false, component: meter-read, disposition: fixed}
  - {id: C5, severity: Low, aim: deliverable, fix_induced: false, component: meter-read, disposition: fixed}
  - {id: C6, severity: Low, aim: deliverable, fix_induced: false, component: pace-line, disposition: fixed}
```

Both halves reviewed `8b602d55`. **Both held:** the stop never leaves [90, 97] on any meter content they tried; ≥ 97% is
always refused; hostile meter content (FIFO, over 4 MiB, 10**400, NaN, 100,000-deep nesting, other windows) produces no
crash or hang; and the midnight computation was right at every 10-minute step over two years in 9 zones (Claude).

- **X2 = C3 = C6 (fixed as a CLASS):** a meter reading outside 0..100 was accepted. With −100, 150, or 110 on the last day,
  the line moved (−100 → 97, letting a 91% wake through). `pace_line` now skips a reading outside 0..100, exactly as
  it skips garbage. Start% is therefore ≤ 100, and the last day's line is always the cap. One case covers −100, 150,
  110 on the last day, an exact 0, and a boolean. The mutations for "negative accepted", "over 100 accepted" and
  "non-number accepted" are each killed by it.
- **C1 (fixed, the MAJOR):** no case exercised the DEFAULT meter path the hooks use. New case: `main()` with no `--meter`,
  under a HOME of its own that holds `~/.claude/meter/log.jsonl`. It kills both one-token mutations the reviewer found
  (the file name, and dropping `expanduser`).
- **C2 (fixed):** the suite's HOME redirect is now asserted as a PROPERTY: the default meter path is absent while the
  suite runs. Removing the redirect fails it.
- **C4 (fixed; latency is NOT mutation-guarded):** the meter is read only after the cache read succeeds, so a stalled
  cache costs one deadline, not two. The docstring now says three deadlines in the worst case. The mutation that undoes
  this was REMOVED: its effect (≤ 1 s) sits inside the existing timing case's bound, and tightening that bound would
  make CI flaky. Stated here instead of claiming coverage.
- **C5 (fixed in part; the growth itself is FILED as backlog #501):** a meter log that cannot be read now gives the read's
  own reason (`the meter log is unreadable: <why>`), so an over-4-MiB log says so instead of "missing". Reading the TAIL
  of a large log is a design change, filed. Until then the guard fails toward the 90 floor and says why.
- **X3 (fixed):** the stdin docstring said "a 95% wake is still DENIED" and "two deadlines". It now says "a wake at the
  stop" and "three deadlines".
- **X1 (DECLINED):** "an unreadable meter is silent below 80%". Below 80 no verdict depends on the line: the floor is 90,
  and WARN starts at 80 and names an unreadable meter before the floor can bind. Raising OK to a notice would warn on
  every prompt on any machine without a meter log (CI, a fresh clone). Refuted if a verdict below 80 is shown to depend
  on the line.

295 self-test cases; 120 mutations. All 20 `#500` mutations and the two re-anchored old ones were killed by hand on a temp copy.
