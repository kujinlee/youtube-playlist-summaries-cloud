# Round 1 — `diff-coverage` — coordinator — ⟳ NOT CONVERGED (both halves); ACCRETE

```yaml
round: 1
fixes_nontrivial: true
subject: diff-coverage
halves:
  codex: ran
  claude: ran
findings:
  - {id: XP1, severity: Medium, aim: deliverable, fix_induced: false, component: coverage-rule, disposition: fixed}
  - {id: XP2, severity: Medium, aim: deliverable, fix_induced: false, component: decision-lines, disposition: fixed}
  - {id: XP3, severity: Medium, aim: deliverable, fix_induced: false, component: diff-parse, disposition: fixed}
  - {id: XP4, severity: Low, aim: deliverable, fix_induced: false, component: cannot-run, disposition: fixed}
  - {id: XP5, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: CM2, severity: Medium, aim: deliverable, fix_induced: false, component: deletions, disposition: fixed}
  - {id: CM4, severity: Medium, aim: deliverable, fix_induced: false, component: ci-surface, disposition: fixed}
  - {id: CL5, severity: Low, aim: deliverable, fix_induced: false, component: tests, disposition: fixed}
  - {id: CL6, severity: Low, aim: deliverable, fix_induced: false, component: exemptions, disposition: fixed}
  - {id: CL7, severity: Low, aim: deliverable, fix_induced: false, component: ci-surface, disposition: fixed}
  - {id: CL8, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: CL9, severity: Low, aim: deliverable, fix_induced: false, component: cannot-run, disposition: fixed}
```

`X` = Codex, `C` = Claude, both on `772e0ab8`. Both: 23/23; 10/10 mutations killed by their named cases;
`check-merge-ready` 211/211 and its five PR-only steps; the PR #409 line `check-hook-commands.py:80` is a real warning
(`if True:` there leaves that suite green).

- **XP1 = CM3 (fixed):** coverage counted every line an anchor's text SPANS, so context lines and a trailing newline
  "covered" lines no mutation edits — 21% of covered lines; `return env` -> `return {}` in `check-plan-code.py` drew no
  warning. Now only the lines where each edit's find and replace text DIFFER.
- **XP2 = CM1 (fixed):** a multi-line `return`/`raise`/`assert`/`except` counted only its first line; a conditional
  expression and a comprehension `if` did not count. Now every line of each, and the `if` header plus its whole test.
- **CM2 (fixed):** a DELETED decision line drew nothing — the PR #364 sever exactly. Deleted decision lines are now
  read from the merge-base and warned.
- **XP3 (fixed):** git appends a TAB after a path with spaces; such files vanished from the check. C-quoted paths are
  unquoted too.
- **XP4, CL9 (fixed):** git missing, and a manifested script that is not UTF-8, were tracebacks (exit 1). Now CANNOT RUN
  and NOT CHECKED; a script that does not parse is NOT CHECKED, never a silent zero.
- **CM4 (fixed):** in CI the warnings were plain text in a green step's log; each is now also a `::warning` annotation.
- **CL7 (fixed):** the step sat between `check-review-recorded` and its comment block, so a CANNOT RUN could skip that
  gate; it now runs after it.
- **CL6 (fixed):** the docstring/import/literal-pin exemptions overlapped decision lines zero times — inert code and
  vacuous claims. Removed; only the `self_test` exclusion, which does something, remains.
- **CL5 (fixed):** five constructed mutants survived the self-test (the raising-loader arm, `except` dropped, a multi-line
  `if` reduced, the cap, two-dot instead of three-dot); each is now a manifest mutation killed by its named case.
- **XP5, CL8 (fixed, prose):** the dashboard said warned lines are ones "no test would notice"; it measures only whether a
  mutation EDITS the line. And the "48" did not reproduce — re-measured at named commits below.

Route ACCRETE (decision-log row written before round 2). 39 cases; 20 mutations, each killed by its named case. Re-measured:
`session-state` at `16bed21b` gives 57, `hooks-absolute-path` at `b6e46a3a` gives 32.
