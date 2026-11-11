# Round 3 — `register-memory-budget-hook` (PR #430) — coordinator — NOT CONVERGED (Codex); REDESIGN: no pathname passes through bash

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 3
fixes_nontrivial: true
subject: register-memory-budget-hook
halves:
  codex: ran
  claude: gap
findings:
  - {id: R1, severity: Low, aim: deliverable, fix_induced: false, component: hook, disposition: fixed}
  - {id: R2, severity: Low, aim: deliverable, fix_induced: true, component: hook, disposition: fixed}
```

Every round-1 and round-2 reproduction now fails. **R1** a FILENAME ending in a newline was stripped by `$(…)` before
resolution, so an alias `tail<newline> -> B` measured `tail`'s target A. **R2 (fix-induced)** an index resolving to a
NON-index file kept the lexical checkout, because round 2's `elif` fell back to it.

**Thrashing in `hook`** — fix-induced findings in rounds 2 (Q1) and 3 (R2), consecutively. The cause is visible without
convening: each round patched one more place where BASH mangled a pathname (a lexical match, `dirname`, `$(…)`, an
`elif`), and each patch moved the edge. **Route: REDESIGN.** No pathname passes through bash: bash launches one Python
program with the payload on stdin untouched, and parsing, resolution, index identification, the walk to the checkout
and the checker call all happen there. STATED BOUND, not a fix: an index resolving to a file that is no checkout's
`docs/memory/MEMORY.md` is NOT MEASURED, naming the resolved target. The checker now runs under a 20 s timeout (Codex's
standing note that it waited synchronously). Measured through `run-hook.sh`, eight inputs including every reproduction
from rounds 1–3: all as intended, 75–221 ms; garbage rc 0. Self-test 20/20.
