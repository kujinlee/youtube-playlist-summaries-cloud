# Round 5 — `diff-coverage-zeros` — coordinator — ✅ CONVERGED (scoped: a case CI found ambient)

```yaml
round: 5
fixes_nontrivial: false
subject: diff-coverage-zeros
halves:
  codex: ran
  claude: skipped
findings: []
```

REVIEW GAP: claude — round 5 is a scoped confirmation on the Codex half, of ONE commit (`12e4d63d`) made after the
round-4 CONVERGED head (`review-method.md`, *The protocol*, step 4; backlog #339).

**Why a round after the loop closed:** CI shard 1 on `2c479352` went red — the mutation "the constructed environment
passes GIT_* through again" was killed, but not by its named case. That case ("no GIT_* variable at all reaches a git
call") can only go red when the host HAS a `GIT_*` variable: this session's harness exports `GIT_EDITOR` and
`GIT_ASKPASS`, a Linux runner exports none, so locally it passed for the right reason and in CI it could not fail at all.
The fix plants `GIT_DIFF_COVERAGE_SENTINEL` around the run that records the calls, and restores it.

Codex confirmed: the change is confined to `self_test()`; with EVERY `GIT_*` removed, 37/37 mutations killed and
attributed; the sentinel is restored for absent, empty and pre-existing values and across an injected exception, and
never reaches a real git call's environment; no other case is ambient on this axis (the `GIT_DIR` and command-scope
cases plant their own inputs); 61/61 scrubbed. No findings.
