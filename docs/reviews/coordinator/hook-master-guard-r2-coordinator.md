# Round 2 — `hook-master-guard` (backlog #522) — coordinator — NOT CONVERGED, fixed

REVIEW GAP: claude — alternation, and weekly usage 98% on the last day before the reset. Codex: `docs/reviews/codex/hook-master-guard-r2-codex.md`, on `ce568784`.

```yaml
round: 2
fixes_nontrivial: true
subject: hook-master-guard
halves:
  codex: ran
  claude: gap
findings:
  - id: P2
    component: usage-pace-run
    verdict: accepted
    fix: the read passes --no-replace-objects (a refs/replace entry swapped the guard's blob)
```

Also folded, from the automated security review of the r0 commit: the spawn and wake hooks now ALLOW with a `systemMessage`
when origin/master's guard cannot be read (stderr alone was not seen), and the header states the bound — the threat is an
ACCIDENTAL loosening by a branch's guard; the launcher and the hooks still come from the checkout, and the ref is locally
writable. Reverting either change reds exactly its case (measured). 327 cases.
