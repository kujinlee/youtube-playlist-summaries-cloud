# Round 3 — `explainer-port-631` (PR #651, backlog #631) — coordinator — NOT CONVERGED (Claude); THRASHING in explainer-serve, Phase 6 run

Claude reviewed the round-2 fold `24d0380d` (`git diff 1745c1b9 24d0380d`).

What held, by live probes on ephemeral ports:
- A legacy server on a port other than 7391 is recognised and stopped, through a symlinked checkout and through the shebang.
- Concurrent starts and a failed record write leave no temp files and no server the script cannot manage.
- The self-test passes 343/343.
- Nothing loosens a gate.

| id | sev | fix_induced | finding |
|---|---|---|---|
| Z1 | MAJOR | false (round-1 exact-path rule, `9b42334e`) | A legacy server from ANOTHER checkout or worktree is reported as "a program that is NOT explainer-serve", and start/stop exit 3. All checkouts share the default root `~/explainers`. |
| Z2 | MINOR | true (`:164-168`, Y2) | With the legacy `.serve.pid` read on every port, `--stop` on an idle port exits 3 and calls a live legacy server on ANOTHER port "not our server". |
| Z3 | MINOR | true | A child whose record write fails makes the parent print "nothing is listening" with rc 1. The delivery doc reads rc 1 as "re-run", and the cause is only in `.serve.log`. |
| Z4 | MINOR | true | Two hand mutants survive (`:1583` isfile clause, `:1442` temp cleanup). The `-c`/`-m` line at `:1601` is redundant. The concurrent-start case ran sequentially, so without exercising the race, in 1 of 8 runs under load. |
| Z5 | NIT | true | A script path containing a space is not recognised when its leading part is an existing directory (fails safe). |

**Thrashing.** Round 2 and round 3 both carry findings caused by the previous round's fold, in one component (`explainer-serve`, the identity rules), so Phase 6 is armed. Severity is falling (r2: a BLOCKER and three MAJORs; r3: fold-induced findings MINOR/NIT only). But the arming condition is the cause, not the severity, so a third fold does not happen before the architecture review answers *can a redesign remove the class?* The review is `docs/reviews/coordinator/architecture-review-2026-11-27-explainer-identity.md`.

Z1 is a design question, not a gate loosening. Whether a sibling checkout's server is "ours" changes what `--stop` may signal. Signalling it stays refused. The message and the delivery doc's reading of rc 3 are the Phase 6 review's to settle.

REVIEW GAP: codex — alternation (round 3 is Claude's).

```yaml
round: 3
fixes_nontrivial: false
subject: explainer-port-631
halves:
  codex: gap
  claude: ran
findings:
  - {id: Z1, severity: MAJOR, aim: deliverable, fix_induced: false, component: explainer-serve, disposition: deferred}
  - {id: Z2, severity: MINOR, aim: deliverable, fix_induced: true, component: explainer-serve, disposition: deferred}
  - {id: Z3, severity: MINOR, aim: deliverable, fix_induced: true, component: explainer-serve, disposition: deferred}
  - {id: Z4, severity: MINOR, aim: deliverable, fix_induced: true, component: explainer-serve, disposition: deferred}
  - {id: Z5, severity: NIT, aim: deliverable, fix_induced: true, component: explainer-serve, disposition: deferred}
```

Review: `docs/reviews/claude/explainer-port-631-r3-claude.md`.
