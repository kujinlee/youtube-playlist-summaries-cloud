# agenda-refs-check r1 — coordinator fold (backlog #504)

```yaml
round: 1
fixes_nontrivial: true
subject: agenda-refs-check
halves:
  codex: ran
  claude: ran
findings:
  - {id: F1, severity: Low, aim: deliverable, fix_induced: false, component: ref-kinds, disposition: fixed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: false, component: blank-repair, disposition: fixed}
```

Both halves CONVERGED (Claude: 2 MINOR; Codex: none). Both MINOR findings fixed.

| Finding | Fix | Case that fails without it |
|---|---|---|
| F1 MINOR — `REF_KINDS` hard-coded; the case sampled a fixed string and could not see grammar drift | `REF_KINDS` is derived from the alternation group of `REF_RE` (`page_markup.KEY_REF`). The case now compares `REF_KINDS` with the grammar's alternatives and parses `"<kind> #7"` for each. Probe on a temp copy with `issue` added to `KEY_REF`: self-test 404/406, the case "the known ref kinds are exactly the alternatives…" goes red (and the unknown-kind case that uses `issue`) | "the known ref kinds are exactly the alternatives of the step grammar, each one parsed by it"; mutation: a kind the grammar does not write is added |
| F2 MINOR — `<record>\n` + blanks, no final newline, left a blank line after the next write | `_locked` strips trailing whitespace (truncates to the stripped length) unless the log already ends in exactly one newline; all-blank and lone-newline logs are emptied | "a log whose last line is blanks after a record leaves no blank line…" (red before the fix: the log had 4 lines with a blank), plus "a log that is a lone newline is emptied too" |

Mutations (temp copies): 3 added (whitespace-only not emptied; trailing blanks kept; kinds include a non-grammar kind), 1 re-anchored and renamed (lone-newline). Manifest 308 entries = pin. All 8 #504 mutations KILLED by their named case.
