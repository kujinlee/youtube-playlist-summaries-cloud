# Architecture review — 2026-10-27 — the fixture-isolation guard (backlog #373)

**Convened by THRASHING** (`docs/dev-process.md` → *The arming condition is thrashing*): rounds 2 and 3 of
`fixture-git-isolation` both carry findings caused by the previous round's own fix, in one component — the
guard `scripts/check-fixture-git-isolation.py`. Round 2's X3/X4/X5/X9 answered round 1's redesign; round 3's
Codex X2/X3 and Claude M3 answered round 2's X8 subcommand rule (a literal cwd, `*args`, a quoted `-C`,
`--config-env` in a shell string — shapes the round-2 guard caught and the round-3 one does not).

## What is NOT thrashing — and is therefore what ships

The BEHAVIOUR. Every round measured it, and every round it held:

| round | population | victim changes | caller-config commands run |
|---|---|---|---|
| r1 fold (coordinator) | 29 suites × 9 families | 0 | 0 |
| r2 (Codex) | 29 × 9 | 0 | 0 |
| r2 fold (coordinator) | **80 (every `--self-test`) × 8** | 0 | 0 — after `brief-compose` was wrapped |
| r3 (Codex, Claude) | **80 × 9 = 720 runs**, each | 0 | 0 |

## What thrashes, and the test: can a redesign REMOVE it?

The component that thrashes is the guard's **builder detector** — the AST rules that decide WHICH self-tests
must be isolated (git argv, shell strings, wrapper calls, the subcommand after global options, the declared
`GIT_SUITES` list). Each round's fix to its precision produced the next round's findings, in both directions:
false negatives (a builder it no longer sees) and an incompleteness that no static rule can close (Claude r3
M2: `subject_status`, `gen-dashboard`, `check-ci-watched` and `peer-sites` run read-only git through
production readers and are on no list — the hook/fsmonitor falsifier cannot see a read).

**Yes — a redesign removes it, and the cost was measured before writing this.** If EVERY `--self-test` entry
in `scripts/` runs inside `fixture_git.isolated()`, there is nothing to detect: no subcommand parsing, no
`GIT_SUITES`, no builder heuristics. Measured 2026-10-27 on `4334b444`: all 80 self-tests run as children of
the isolated environment → **79 of 80 pass**; the one failure is `subject_status`, already 16/17 with
nothing planted (pre-existing, unrelated). The guard then checks one closed property: *every script whose
`--self-test` is dispatched runs that suite inside `isolated()`*, with a small explicit exemption list if any
suite genuinely needs the caller's environment (none measured).

What the redesign does NOT remove: the escape shapes that are properties of in-process isolation itself —
`os.putenv`, `atexit`, import-time launches, work after the block exits, a decoy dispatch (backlog #380).
Its structural answer is a fresh child interpreter with a constructed environment, which the universal
wrapper makes cheap to add later, because there is then one wrapper to change.

## Decision (owner's standing AFK rule — not critical)

- **This PR stops by DEFER** (the decision ladder after a lost SPLIT): it ships the measured behaviour, its
  limits are corrected to name every escape shape found in round 3, and the false prose is fixed
  (`subject_status` is a git-running suite the detector misses, not "out of scope").
- **The redesign is its own subject, backlog #382** — universal wrapping, deleting the builder detector.
  Doing it here would be a fourth round on a PR whose subject (the behaviour) has already converged; the
  ladder exists to stop exactly that.
- ⚠ **Falsifier for this decision:** if #382 is not started before the next PR that adds a git-running
  self-test, the detector's known blind spots become live — that PR's suite is the observation.
