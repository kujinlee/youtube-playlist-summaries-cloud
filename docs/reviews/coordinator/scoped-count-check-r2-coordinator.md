# Round 2 — `scoped-count-check` — coordinator — CONVERGED (Claude half); three findings filed

The Claude half reviewed `17cd4e57`, the round 1 fold (`d5b90f8d..17cd4e57`) and then the PR as a whole. It reported no
BLOCKER and no High; all three findings are FILE and are now backlog rows.

REVIEW GAP: codex — alternation (round cap: both halves in r1, then one half per round; review-method section 0 Q4c).

```yaml
round: 2
fixes_nontrivial: false
subject: scoped-count-check
halves:
  codex: gap-alternation
  claude: ran
findings:
  - {id: F1, severity: Medium, aim: deliverable, fix_induced: false, component: reached, disposition: filed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: true, component: reached, disposition: filed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: true, component: gates-runner, disposition: filed}
```

Half: `docs/reviews/claude/scoped-count-check-r2-claude.md`, on `17cd4e57`. Evidence it reports: self-tests 40/40, 37/37 and
281/281; `--mutate . --only` 23/23 and 12/12 killed and attributed; the scoped gate on this PR rc 0 over 50 of 75 suites; the
round 1 rename false green is gone at both diff sources; two new probes (a file-load chain two hops deep, a helper renamed and
edited) select the right suite; CI keeps the unscoped run (`ci.yml:704`).

| Finding | Disposition |
|---|---|
| F1 — a suite that finds files by glob is never selected by the file it globs (`check-main-drivable.py` reds on a new guard while `--changed` says "nothing to check") | FILED as backlog row 452. Bounded: the realistic shape is rescued by name-list edges, and `gates-for-pr.py` runs `check-main-drivable` as its own gate. Not a Q4c BLOCKER |
| F2 — the 50-suite scope is blamed on dictionary keys; the measured cause is plain name lists | FILED as backlog row 453 (prose only) |
| F3 — `gates-for-pr.py`'s gate-set docstring omits that the scoped step replaces CI's arguments locally | FILED as backlog row 454 (prose only) |

**The narrowing question is DECIDED: keep the current rule.** Round 1 asked whether string edges should be limited to load
sites. The review simulated it: PR #450's scope falls from 50 suites to 8 (about two to three minutes saved per local run),
but the `run-hook.sh` rename stops reaching `check-run-hook.py` (it names the launcher through a module constant and reads it
with `.read_text()`, not a load call), and a lone edit of each of 5 sampled guards stops reaching `check-main-drivable.py`
(5/5 to 0/5). That brings back round 1's own BLOCKER. If precision is wanted later, the route is a declared-dependency
mechanism (row 452's `READS_GLOB`), not a narrower guess at which strings are loads.

**No script changed in this round**, so no further review round is owed on code.

**Not run:** the full unscoped `check-selftest-counts.py` (CI's) and the full mutation sweep.
