# Round 2 — `subject-status-386` — coordinator — NOT CONVERGED (Codex); BLOCKER folded, MINOR declined

Codex reviewed the round 1 fold `3d82e8d7` (`git diff 3b924595 3d82e8d7`).

- **D1 (Codex BLOCKER, fix-induced by round 1).** The 100,000-level case fails on Python 3.12, CI's pin: there
  `json.loads` itself raises `RecursionError` (correctly CANNOT RUN, "too deep to parse"), so the input never
  reaches the depth walk and the case's "nested deeper than 32" expectation is false — 175/176. Fold: the case
  nests 50 levels, which parses on every interpreter and is past the bound, so it reads the WALK; the 200,000
  case still reads the parse path. Measured after the fold: 176/176 on python3.12 and on the default python3, and
  the depth-bound mutation is killed by its renamed case on 3.12.
- **D2 (Codex MINOR) — declined, by design.** An unknown field nested past 32 levels is now CANNOT RUN where it
  was accepted. The bound covers the whole document deliberately, as `check-inventory._read_json` does: a value
  no rule reads today is still `repr`-ed by the next rule written, and the real map nests 4 (measured).

What held: the C2 fixture, the accepted-set pin (no collision that hides a loosening, per Codex), the docstring
corrections, all three new mutations on 3.14. All six loosening checks: not a loosening.

REVIEW GAP: claude — alternation (round 2 is Codex's).

```yaml
round: 2
fixes_nontrivial: false
subject: subject-status-386
halves:
  codex: ran
  claude: gap
findings:
  - {id: D1, severity: Blocker, aim: deliverable, fix_induced: true, component: check-shipping-sets, disposition: folded}
  - {id: D2, severity: Minor, aim: deliverable, fix_induced: true, component: check-shipping-sets, disposition: declined}
```

Review: `docs/reviews/codex/subject-status-386-r2-codex.md`.
