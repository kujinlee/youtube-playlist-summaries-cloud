# Round 3 — `fixture-git-isolation` — coordinator — ⟳ NOT CONVERGED (both halves); THRASHING → architecture review; DEFER

```yaml
round: 3
fixes_nontrivial: false
subject: fixture-git-isolation
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: false, component: guard, disposition: deferred}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: true, component: guard, disposition: deferred}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: true, component: guard, disposition: deferred}
  - {id: Xm4, severity: Low, aim: deliverable, fix_induced: true, component: guard, disposition: deferred}
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: false, component: guard, disposition: deferred}
  - {id: Cm2, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: Cm3, severity: Low, aim: deliverable, fix_induced: true, component: guard, disposition: deferred}
```

`X` = Codex, `C` = Claude, both on `4334b444` (round 3 ran as a PAIR: `check-review-recorded` reads only Codex
verdicts, so a Codex half was required to merge anyway, and alternation permits a pair).

**Held, independently in both halves:** 720 runs (all 80 `--self-test` scripts × 9 families) — 0 victim changes,
0 hook/fsmonitor hits; wrapped suites identical case by case (brief-compose 153/153, gen-backlog-page 165/165);
2303 is the real sum, every mutation attributed. **The bet's first clause (the behaviour) held; its second (the
LIMITS are complete) is lost.**

**THRASHING — YES.** X2/X3/Xm4 = Cm3 are caused by round 2's X8 fix, in the guard, and round 2 also carried
fix-induced guard findings: two consecutive rounds, one component. Convened:
[`architecture-review-2026-10-27-fixture-guard.md`](../architecture-review-2026-10-27-fixture-guard.md). Its
answer: the thrashing component is the builder DETECTOR, and a redesign removes it — wrap every `--self-test`
(measured 79/80 green; the one red is pre-existing) — filed as backlog #382.

**Route: DEFER (ladder exhausted).** Every guard finding is deferred to #380 (escape shapes, now named in
LIMITS) or dissolved by #382 (detector precision: X2, X3, Xm4, Cm3, and the GIT_SUITES incompleteness). Cm2's
FALSE PROSE is fixed: `subject_status`, `gen-dashboard`, `check-ci-watched` and `peer-sites` run read-only git
and are not on `GIT_SUITES`; "out of scope / touches neither" is withdrawn.
