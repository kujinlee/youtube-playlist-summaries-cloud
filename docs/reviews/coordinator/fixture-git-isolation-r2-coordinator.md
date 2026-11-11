# Round 2 — `fixture-git-isolation` — coordinator — ⟳ NOT CONVERGED (Codex); SPLIT

REVIEW GAP: claude — round 2 alternates to the Codex half alone (rounds 2+ alternate, `review-method.md` → *Round topology*); the coordinator's own widened falsifier on 80ccf0eb (9 families x 29 suites, both trees) stands beside it.

```yaml
round: 2
fixes_nontrivial: true
subject: fixture-git-isolation
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: false, component: population, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: isolation-boundary, disposition: deferred}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: true, component: guard, disposition: deferred}
  - {id: X4, severity: Medium, aim: deliverable, fix_induced: true, component: guard, disposition: fixed}
  - {id: X5, severity: Medium, aim: deliverable, fix_induced: true, component: guard, disposition: deferred}
  - {id: X6, severity: Medium, aim: deliverable, fix_induced: true, component: isolation-boundary, disposition: deferred}
  - {id: X7, severity: Medium, aim: deliverable, fix_induced: true, component: isolation-boundary, disposition: deferred}
  - {id: X8, severity: Low, aim: deliverable, fix_induced: false, component: guard, disposition: fixed}
  - {id: X9, severity: Low, aim: deliverable, fix_induced: true, component: guard, disposition: deferred}
```

Codex on `80ccf0eb`. **Held:** 0 victim changes and 0 marker hits over 261 runs (9 families x 29 suites) — reproduced
independently by the coordinator, who also measured 0 real-tree hits on the branch vs up to 6 on master; 42/42, 70/70; all
48 mutations attributed; EXPECTED_MUTATIONS 2294 is the real sum; the 13 migrated suite bodies are unchanged.

**The bet is LOST** (decision log). **Route: SPLIT** (ladder: accrete skipped → redesign lost → split).

- **X1 (fixed):** `brief-compose` runs caller config through `page_chrome.provenance()` and was outside the population —
  which was a HAND LIST of 29. The population is now derived: the falsifier runs over every script with `--self-test`.
- **X4, X8 (fixed, cheap and real):** the entry's `with` takes exactly one item, the argument-free `fixture_git.isolated()`;
  the git SUBCOMMAND after global options marks a builder, not any `init` argument.
- **X2, X3, X5, X6, X7, X9 (deferred → backlog #380):** each is a program written to escape — an import-time capture,
  a shadowed name, a decoy dispatch, `atexit`, `os.putenv`. No existing script does any of them (the derived falsifier is
  the evidence). X7 shows in-process swapping cannot be complete: `os.putenv` writes the C environment that restoring
  `os.environ` never sees. The structural answer is a fresh child interpreter with a constructed environment, a different
  mechanism and its own subject. The guard's docstring states this as its limit.

**Thrashing? Not armed — it needs TWO consecutive rounds of fix-induced findings, and round 1 had none.** Two kinds here, not a chain: X1 is a population miss present before the fold; X2–X9 are new shapes
against the new guard, a guard asked to stop adversarial code. Neither is a defect caused by fixing the previous round's.
