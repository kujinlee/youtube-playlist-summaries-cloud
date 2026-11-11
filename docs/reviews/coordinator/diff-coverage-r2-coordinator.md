# Round 2 — `diff-coverage` — coordinator — ⟳ NOT CONVERGED (bet LOST); REDESIGN of the coverage rule

```yaml
round: 2
fixes_nontrivial: true
subject: diff-coverage
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XP1, severity: Medium, aim: deliverable, fix_induced: true, component: coverage-rule, disposition: fixed}
  - {id: XP2, severity: Medium, aim: deliverable, fix_induced: false, component: diff-parse, disposition: fixed}
  - {id: XP3, severity: Medium, aim: deliverable, fix_induced: false, component: deletions, disposition: fixed}
  - {id: XL4, severity: Low, aim: deliverable, fix_induced: false, component: cannot-run, disposition: fixed}
  - {id: XL5, severity: Low, aim: deliverable, fix_induced: false, component: deletions, disposition: fixed}
  - {id: XL6, severity: Low, aim: deliverable, fix_induced: false, component: diff-parse, disposition: fixed}
```

REVIEW GAP: claude — round 2 alternates to the Codex half (`review-method.md`, *The protocol*, step 4; backlog #339).

`X` = Codex, tree `8130578c`. HELD: every r1 probe (trailing-newline anchor; the real `return env` -> `return {}`;
multi-line return/assert/except/exit; `if (` -> `while (`; spaced and tabbed paths; git missing); rename-with-edit
deleted lines read from the old path; a divergent merge-base; `\ No newline` markers; 39/39; 20/20; 211/211 and the
five PR-only steps; the quoted 57 and 32 reproduce.

- **XP1 (fold-induced, fixed by REDESIGN):** r1 aligned each edit's find/replace TEXT with difflib and, for an
  insertion, marked an adjacent unchanged source line — so a mutation inserting `audit = 1` above `if bad:` "covered"
  the unchanged `if bad:`. Now an edit is APPLIED and a source line counts as edited exactly when it does not survive
  unchanged; an insert-only change edits no original line. (The mutation that reproduces r1's rule needs two edits:
  `tag != "equal"` alone is EQUIVALENT, because an insert's range is empty — the scoped sweep caught that.)
- **XP2 (fixed):** a binary diff (`Binary files … differ`) dropped the file — now NOT CHECKED.
- **XP3 (fixed):** deleting a script together with its manifest hid its deleted decisions — scope now also comes from
  the merge-base's manifests.
- **XL4 (fixed):** non-UTF-8 git output was a traceback — every git call decodes with replacement.
- **XL5 (fixed):** an unparseable base side read as "nothing deleted" — now NOT CHECKED.
- **XL6 (fixed):** a C-quoted path with literal Unicode raised in a Latin-1 round trip — decoded byte-wise now.

Route REDESIGN of the coverage rule (decision-log row written before round 3); the other five patched in place.
48 cases; 24 mutations, each killed by its named case. Re-measured after the redesign: still 57 (`session-state` @
`16bed21b`) and 32 (`hooks-absolute-path` @ `b6e46a3a`), and `check-hook-commands.py:80` still warns.
