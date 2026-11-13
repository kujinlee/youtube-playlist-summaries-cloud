# Round 3 — `627-serve-master` (backlog #627) — coordinator — CONVERGED; m5-m8 FILED

```yaml
round: 3
fixes_nontrivial: false
subject: 627-serve-master
halves:
  codex: skipped
  claude: ran
findings:
  - {id: m5, severity: Minor, aim: deliverable, fix_induced: true, component: suite-isolation, disposition: filed}
  - {id: m6, severity: Minor, aim: deliverable, fix_induced: true, component: serve-handler, disposition: filed}
  - {id: m7, severity: Minor, aim: deliverable, fix_induced: false, component: suite-isolation, disposition: filed}
  - {id: m8, severity: Minor, aim: deliverable, fix_induced: false, component: suite-isolation, disposition: filed}
```

REVIEW GAP: codex — alternation (owner 2026-10-28: rounds 2+ run ONE half).

Reviewed `25ce6e06` (the Claude half only, `docs/reviews/claude/627-serve-master-r3-claude.md`). Verdict:
CONVERGED. No Blocker, no Major. All four r2 findings held under refutation, and each r2 case goes red when its
fix is removed. Decision (coordinator): STOP at r3 and FILE m5-m8; none is folded in this PR.

All four are FILED to backlog #632 (PR #576's follow-ups).

| Id | Finding | Caused by r2 fix (reviewer's line) | Disposition |
|---|---|---|---|
| m5 | r2's `_suite_owns(setup.copy)` clause masks r1's `_suite_owns(setup.checkout)` clause | **YES** | FILED to backlog #632 |
| m6 | `/latest`'s 404 note and the `poke(FETCH_WAIT)` wait on `/` and `/latest` have no case | yes, in the narrow sense: r2's own new lines, a coverage gap, no change in behaviour | FILED to backlog #632 |
| m7 | the strict-inside boundary in `_inside_suite_tmp` and `_suite_owns` is unbound (`startswith(base)` survives) | no (from r1) | FILED to backlog #632 |
| m8 | the fetcher moves `serve_copy_path()` at run time; its guard checks `setup.copy` from build time | no (predates r2) | FILED to backlog #632 |

**Thrashing: NOT armed.** The arming condition is two consecutive rounds whose findings were caused by the previous
round's fix. r2's four findings were not caused by r1's fix, and only r3's m5 and m6 were caused by r2's. So no two
consecutive rounds qualify. Round 3 is also the last round the cap allows to fold; from r4 findings are filed
unless a Blocker, and there is none.

None of the four exposes a write outside the suite: regen-pages' five writer guards stand, and nothing changes what
a reader sees in production.
