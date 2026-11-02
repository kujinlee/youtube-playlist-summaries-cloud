# Round 1 — `speed-main-drivable` (PR #449, backlog #401) — coordinator — Claude CONVERGED, Codex NOT CONVERGED (Minor only)

Codex half: `docs/reviews/codex/speed-main-drivable-r1-codex.md`. Claude half: `docs/reviews/claude/speed-main-drivable-r1-claude.md`. Both reviewed `1accbd93`.

```yaml
round: 1
fixes_nontrivial: false
subject: speed-main-drivable
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Low, aim: instrument, fix_induced: false, component: memo, disposition: fixed}
  - {id: X2, severity: Low, aim: instrument, fix_induced: false, component: memo, disposition: fixed}
  - {id: X3, severity: Low, aim: deliverable, fix_induced: false, component: memo, disposition: fixed}
  - {id: X4, severity: Low, aim: deliverable, fix_induced: false, component: memo, disposition: fixed}
  - {id: X5, severity: Low, aim: instrument, fix_induced: false, component: memo, disposition: fixed}
```

**Both halves found the cache CORRECT.**
- Claude ran 90,604 cached-versus-uncached comparisons on each of Python 3.14 and 3.12, with 0 differences: all 87 real scripts, dropped and re-parsed trees (address reuse), and 300 synthetic trees.
- The CI-shaped live run gives identical output on master, the branch and the uncached version.
- Codex found no cache-key omission, no missing argument retention and no frozen-result mutation.

**Speed, measured locally on Python 3.12:** the suite went from 83.5–84 s to 9.7–12 s; the live run from 75.7–93 s to 5.7–12.5 s; peak memory from 106–124 MB to 127–173 MB.

**All findings are Low:**
- **X1:** losing cache reuse (`hit = None`) survives, so the speedup has no test.
- **X2:** a key that ignores case survives.
- **X3:** the memo is unbounded for a long-lived importer (about 30 MB after 20,000 discarded trees).
- **X4:** the rule that a tree is not modified after a helper sees it is undocumented. Claude's M1 found the same.
- **X5:** the lifetime case relies on the allocator reusing addresses.

**Fold, small:**
- **X1:** a builder-call-count assertion.
- **X2:** a case-distinct name case, `p` versus `P`.
- **X3:** the cache's lifetime bounded to one analysis. Clear it at the end of `assess()`, or cap it the way `_parents` is capped; say which.
- **X4:** the immutability precondition stated in the docstring.
- **X5:** a direct lifetime assertion.

Then a scoped final round.
