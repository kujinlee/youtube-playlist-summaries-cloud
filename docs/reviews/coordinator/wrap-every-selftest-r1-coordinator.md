# Round 1 — `wrap-every-selftest` — coordinator — ⟳ NOT CONVERGED (Codex); ACCRETE (broad, dumb rules)

REVIEW GAP: claude — the Claude half ran 2h32m (spawned 21:12) without filing; its progress logs went silent at 21:44, a 23:19 request to write what it had produced no file by 23:44, and it was stopped so it could not write into the worktree mid-fold. Its measurements are lost; the Codex half below is comprehensive and executed.

```yaml
round: 1
fixes_nontrivial: true
subject: wrap-every-selftest
halves:
  codex: ran
  claude: gap
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: population, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: false, component: entry-shape, disposition: fixed}
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: false, component: entry-shape, disposition: fixed}
  - {id: XM4, severity: Medium, aim: deliverable, fix_induced: false, component: rule-5, disposition: fixed}
  - {id: Xm5, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

Codex on `2e4a7d9f`. **Held:** 79 scripts, 0 exempt; all 79 suites give identical case-by-case output wrapped and unwrapped
apart from the documented `gen-dashboard` HOME fix; 711 falsifier runs over nine families, 0 victim changes, 0 marker
hits; 35/35 guard and both re-bound dashboard mutations killed by their named cases; 2,340 real; every anchor resolves.

**Claim (4) — "nothing loosened against master" — is FALSE**, measured by running both guards' `check_source` over
identical probes (each also executed and shown to write a victim): dict, `getattr` and argparse-action dispatch of
`--self-test` (XM1 — discovery reads only `if` tests, so the file never enters the population); a module-level builder
in a file with no `--self-test`; a decorator that replaces the checked entry (XM2); an `async def` entry that never runs
(XM3); launches in an `except (…)` type expression (XM4), in a class body, via `r = subprocess.run` and via `__import__`.

**Root cause:** population discovery is itself a detector — of DISPATCH — and leaks the way the builder detector did.
**Route: ACCRETE with broad, dumb rules** (round 1): the population is every `scripts/*.py` whose source mentions
`--self-test`; a population file with no recognisable canonical entry is refused; entries must be plain synchronous,
undecorated module-level functions; rule 5 applies to EVERY file in `scripts/` and treats class bodies, decorators,
defaults and exception-type expressions as import time; the "not looser" claim becomes a measured, bounded statement.
