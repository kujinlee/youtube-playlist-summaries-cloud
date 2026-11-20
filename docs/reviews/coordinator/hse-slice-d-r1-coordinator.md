# Round 1 — `hse-slice-d` — coordinator — NOT CONVERGED (Codex half)

Codex (`docs/reviews/codex/hse-slice-d-r1-codex.md`) reviewed `c4861690` (plan Tasks 8-12, `scripts/check-publishability.py`):
3 MAJOR, 2 MINOR, no BLOCKER. Each finding came with an input Codex constructed and ran; each fold case below rebuilds that input.

REVIEW GAP: claude — weekly usage 88% at 07:03 on 11-17, against the 89.6% line where new spawns are refused; the Claude half runs in round 2 under alternation.

```yaml
round: 1
fixes_nontrivial: true
subject: hse-slice-d
halves:
  codex: ran
  claude: gap
findings:
  - {id: XM1, severity: High, aim: deliverable, fix_induced: false, component: detector-6-config, disposition: fixed}
  - {id: XM2, severity: High, aim: deliverable, fix_induced: false, component: detector-2-python, disposition: fixed}
  - {id: XM3, severity: High, aim: deliverable, fix_induced: false, component: detector-4-prose, disposition: fixed}
  - {id: Xm1, severity: Medium, aim: deliverable, fix_induced: false, component: self-test, disposition: fixed}
  - {id: Xm2, severity: Medium, aim: deliverable, fix_induced: false, component: report, disposition: narrowed}
```

| Id | Finding | Fold |
|---|---|---|
| XM1 | `os.getenv("X", None)` counted as a working default, so a required token was no finding | a default that is the constant `None`, positional or `default=`, is no working default; case `XM1:` |
| XM2 | a Python invocation of a file the repository does not hold was dropped (detector 2 required the target to exist) | a missing target that is a literal argument of a process runner is `outside-set`; an import or fixture path resolving to no file still is not (a substring test first added 40 false findings on the live tree; the runner form adds none, 228 → 228); case `XM2:`. The CLI case's fixture already invoked a missing `scripts/elsewhere.py` and now reports it |
| XM3 | "Use `TaskList` …" was a mention: the imperative list lacked `use` | `use`, `call` and `invoke` join the imperatives; case `XM3:` |
| Xm1 | the unreadable-registration case scanned the system temp dir and raised on a missing file before reaching the settings read | the case scans its own world, with the declared path in installed coordinates, and expects the settings message itself (`cannot read .claude/settings.json`), so the original missing-file error now fails it. Control: with detector 7's own read removed the case still passes, because the file-set stage reads the same file first (`check-shipping-sets.py` `registered_hooks`) and raises. The property holds through two readers; detector 7's read is unreachable on an unreadable file |
| Xm2 | the committed report's `measured_at` is not HEAD | NARROWED: re-measured on the fold. A committed report names the tree it scanned, which is always the commit before its own; the component results are what must match, and Codex found them identical |
