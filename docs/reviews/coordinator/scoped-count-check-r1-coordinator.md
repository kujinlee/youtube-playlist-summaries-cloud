# Round 1 — `scoped-count-check` — coordinator — NOT CONVERGED (both halves); fold applied

```yaml
round: 1
fixes_nontrivial: true
subject: scoped-count-check
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Blocking, aim: deliverable, fix_induced: false, component: changed-paths, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: reached, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: false, component: merge, disposition: fixed}
  - {id: C1, severity: Blocking, aim: deliverable, fix_induced: false, component: changed-paths, disposition: fixed}
  - {id: C2, severity: Medium, aim: deliverable, fix_induced: false, component: reached, disposition: fixed}
  - {id: C3, severity: Medium, aim: deliverable, fix_induced: false, component: gates-runner, disposition: fixed}
  - {id: C4, severity: Low, aim: deliverable, fix_induced: false, component: docs, disposition: fixed}
```

Halves: `docs/reviews/codex/scoped-count-check-r1-codex.md`, `docs/reviews/claude/scoped-count-check-r1-claude.md`, both on
`d5b90f8d`. Both reproduced the rename false green (`--changed` exit 0, the unscoped run exit 1).

| Finding | Disposition |
|---|---|
| X1 / C1 — a rename prints only its NEW name, so a suite naming the OLD one is unreached | FIXED: `--no-renames` on both `git diff` sources (`scripts/check-selftest-counts.py:546-547`). Cases: a STAGED and a COMMITTED `git mv` of a file a suite names both select it; each went red with the flag removed (2 red, checked), and each has a mutation entry |
| X2 / C2 — a file-loaded dependency stopped after one string edge | FIXED: `reached` closes BOTH edges to a fixed point (`:511`). Case: helper -> (import) -> script loaded by path -> suite. The earlier ONE-HOP asymmetry is retired with its mutation. COST, measured: scope on this branch grew from 26 of 75 suites (2m31s) to 50 of 75 (3m51s under load), because `check-plan-code.py` holds every script name as a dictionary key and this branch edits it. Over-selecting is the safe side and the full run stays CI's, but the saving is smaller than the row first claimed; r2 should weigh whether the string edge should be limited to `spec_from_file_location`/`runpy` arguments (Claude F2's suggestion) |
| X3 — the merge swallowed the `## 2026-10-30` header, folding the #402/#388 text into the 2026-11-01 compaction entry | FIXED: header restored at `docs/dashboard-entries.md:18565` |
| C3 — `gates-for-pr.py` still ran the unscoped count check locally | FIXED: `SCOPED_LOCALLY` (`scripts/gates-for-pr.py:66`) maps that step to `--changed --base origin/<base>`; an OUT OF SET line says the full count check is CI's (`:157`); a stale name refuses the set like `NOT_LOCAL` (`:165`). Self-test 35 -> 37 cases, both new cases mutation-killed |
| C4 — "in seconds" and "PR (to be opened)" | FIXED in backlog rows 388 and 402: the measured figures replace "in seconds", PR #450 replaces the placeholder. Row 393's own placeholder is a different PR and was left alone |

`EXPECTED_MUTATIONS`: `check-selftest-counts.py` 21 -> 23 (+3, -1 retired with its subject); `gates-for-pr.py` 10 -> 12.
`--mutate . --only` for each: 23/23 and 12/12 killed and attributed. Self-tests: 40/40 and 37/37.

**Not run:** the full unscoped `check-selftest-counts.py` (CI's), and the full mutation sweep.

**Next:** round 2, Claude half only (Opus); its record carries `REVIEW GAP: codex — alternation` (round 1 ran both halves).
