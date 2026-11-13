# Round 8 — `hook-master-guard` (backlog #522) — coordinator — CONVERGED (the one finding rejected, with its reason)

REVIEW GAP: claude — weekly usage 99% on the last night before the reset. Codex: `docs/reviews/codex/hook-master-guard-r8-codex.md`, on `66e30308`.

```yaml
round: 8
fixes_nontrivial: false
subject: hook-master-guard
halves:
  codex: ran
  claude: gap
findings:
  - id: BLOCKER
    component: usage-pace-run
    verdict: rejected
    reason: an inherited SHELLOPTS=noexec or onecmd stops bash from executing ANY script, so no line inside the launcher can answer it; run-hook.sh runs under the same options before the launcher does, every other hook is silenced the same way, and so is master's direct invocation — this change neither introduces nor widens it, and the launcher's header bounds the threat to accident, not a hostile environment
```

Round 7's class (an inherited option altering the launcher's OWN error handling) is closed by `set +e +u +o pipefail`. Round 8's
is different in kind: options that stop bash executing at all. Neutralising them would need a change to how Claude Code starts a
hook, not to a hook — outside this repository. Rounds 4-8 ran past the cap on BLOCKERs; this one is out of the stated threat model.
