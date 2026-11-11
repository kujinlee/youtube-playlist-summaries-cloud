# Round 4 — `wrap-every-selftest` — coordinator — ⟳ NOT CONVERGED (Codex SPLIT confirmation); DEFER, prose only

REVIEW GAP: claude — round 4 is the SPLIT route's Codex confirmation round; the Claude half of round 3 did not file (see round 3's record).

```yaml
round: 4
fixes_nontrivial: false
subject: wrap-every-selftest
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Low, aim: deliverable, fix_induced: false, component: rule-5, disposition: deferred}
  - {id: X2, severity: Low, aim: deliverable, fix_induced: false, component: rule-5, disposition: deferred}
```

Codex on `ffe613b9`. **X1** a direct launcher in a `match` case GUARD and **X2** in a lambda's DEFAULT argument, each
taken only when `--self-test` is in argv, pass both halves (executed; markers created). Neither is a loosening against
master's guard. **Held:** 141/141; 79 isolated, 0 exempt; 84 imports observed without launch; the r1–r3 fixed suite;
argv/CI/HOME direct probes refused; inherited `sitecustomize` excluded and a `.pth` launch blocked (`-I -S` works); ordinary
statement bodies traversed; 55/55 mutations attributed; 2,361 real; #380 records outside enforcement with a FAILS IF.

**Why not fold them.** The static half is a SYNTAX backstop, chosen by the architecture review as cheap, never complete;
two more expression positions is the whack-a-mole the review named, one level smaller (comprehension conditions,
f-string fields and evaluated annotations would be next). **Route: DEFER** (accrete, redesign and split all lost). Only
the PROSE changes: the guard's LIMITS, the #382 row, the dashboard and the PR body now say the static half covers
module-level STATEMENT BODIES, not every expression position, naming these two; #380's row records them as one more
reason enforcement belongs outside the interpreter. The guard's code is unchanged (AST without docstrings identical).
