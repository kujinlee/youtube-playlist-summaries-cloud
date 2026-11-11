# Round 3 — `hook-guard-gaps` — coordinator — ⟳ NOT CONVERGED on prose only; fixed by claiming less

```yaml
round: 3
fixes_nontrivial: false
subject: hook-guard-gaps
halves:
  codex: skipped
  claude: ran
findings:
  - {id: CL1, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
```

REVIEW GAP: codex — round 3 is a confirmation round on the Claude half, scoped to the r2 prose commit
(`review-method.md`, *The protocol*, step 4; backlog #339).

`C` = Claude. CONFIRMED: the `scripts/check-hook-commands.py` change is docstring-only (`git diff --quiet` on code, cases
and manifest); 29/29; live check green over 13 commands; the five types match the 2.1.309 binary's schema union; the
`args` prose matches the binary's runner code (spawn with no shell).

- **CL1 (fixed, prose, fold-induced):** the r2 correction said a non-default `shell` "misbehaves rather than not launch".
  With no PowerShell on PATH, 2.1.309 throws and the hook does not launch; with PowerShell, the canonical command
  probably works. Two rounds have now each refuted a guess about a feature this repo does not use, so the prose stops
  guessing: `shell` "changes which shell runs the command; its outcome here is not verified". Fixed in the docstring,
  backlog #368 and the r2 record. The proposed rule — refuse a non-default `shell` — is unchanged.
- **CI1 (info):** the decision-log row closed at `rounds_at_termination: 2` before this confirmation round — consistent
  with confirmation rounds of a closed unit not counting toward its rounds, which is how PR #406's r4/r5 were recorded.
