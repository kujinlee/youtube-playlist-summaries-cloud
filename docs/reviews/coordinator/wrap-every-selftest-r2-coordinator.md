# Round 2 — `wrap-every-selftest` — coordinator — ⟳ NOT CONVERGED (Codex); REDESIGN (rule 5 by execution, not syntax)

REVIEW GAP: claude — round 2 alternates to the Codex half alone (rounds 2+ alternate, `review-method.md` → *Round topology*).

```yaml
round: 2
fixes_nontrivial: true
subject: wrap-every-selftest
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: true, component: rule-5, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: true, component: rule-5, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: true, component: rule-5, disposition: fixed}
  - {id: Xm4, severity: Low, aim: deliverable, fix_induced: false, component: population, disposition: fixed}
```

Codex on `b3b988ab`. **X1** launcher bindings via annotated assignment, walrus and tuple unpacking; **X2** an aliased
`import_module`; **X3** launches evaluated in a `for` target and a `with … as` target — each master-refused,
branch-accepted, and executed against a victim. **Xm4** a `--self-test` mention only in a comment or docstring is outside
the population, contrary to the stated contract. **And a REAL one the static rule cannot see by design:**
`check-ci-watched.py:128` calls `_repo_sentinel()` at import, which runs `git rev-parse` (`:120`). **Held:** every round-1
probe refused; 109/109; 48/48 mutations attributed; 2,353 real; all 79 real scripts pass.

**Why patching cannot win:** rule 5 is a DENY-LIST OF SYNTAX — round 1 found four shapes, round 2 six more, and Python has
more. It is #376's lesson again (`architecture-review-2026-10-27-em-guard.md`): stop predicting from source; measure.
**Route: REDESIGN.** Rule 5 runs each `scripts/*.py` import in a child interpreter under an audit hook that refuses any
process-launch event, so every spelling, binding and indirect call is caught by the event, not by its shape.
**Thrashing?** X1–X3 come from round 1's rule-5 extension (fix-induced), the first such round in this subject — the
arming condition (two consecutive) is not met.
