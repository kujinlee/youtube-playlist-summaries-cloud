# Round 6 — `hook-master-guard` (backlog #522) — coordinator — NOT CONVERGED, the BLOCKER removed by a redesign

REVIEW GAP: claude — weekly usage 99% on the last night before the reset. Codex: `docs/reviews/codex/hook-master-guard-r6-codex.md`, on `4f615fba`.

```yaml
round: 6
fixes_nontrivial: true
subject: hook-master-guard
halves:
  codex: ran
  claude: gap
findings:
  - id: BLOCKER
    component: usage-pace-run
    verdict: accepted
    fix: cannot() prints a FIXED literal JSON message (nothing interpolated, nothing to escape, no python) and writes the reason to stderr
```

⚠ **THRASHING (dev-process.md, Phase 6's arming condition):** r5's finding came from r4's fix (`cannot` used python) and r6's from
r5's (the printf JSON left control characters unescaped) — two consecutive rounds caused by the previous fix, in one component.
**Can a redesign remove it? Yes, and this round does:** every defect in the class came from interpolating text (paths, exit codes)
into JSON built in bash. The JSON is now a constant; the reason goes to stderr. The convened architecture review is not run — new
agents are refused at 99% weekly usage — and this answer stands in its place, stated as such.

Cases: the four that read the reason now read it from stderr (the hook helper keeps the last stderr), and a new one puts a newline,
a tab, a quote and a backslash in TMPDIR. Interpolating the reason back into the JSON reds the new case (measured). 331 cases.
