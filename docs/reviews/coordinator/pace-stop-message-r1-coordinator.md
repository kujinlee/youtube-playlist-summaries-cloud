# pace-stop-message r1 fold (backlog #525)

```yaml
round: 1
fixes_nontrivial: true
subject: pace-stop-message
halves:
  codex: ran
  claude: ran
findings:
  - id: codex-1
    severity: Low
    aim: deliverable
    component: scripts/check-usage-pace.py
    fix_induced: false
    disposition: fixed
  - id: codex-2
    severity: Low
    aim: deliverable
    component: scripts/check-usage-pace.py
    fix_induced: false
    disposition: fixed
  - id: claude-m1
    severity: Low
    aim: deliverable
    component: scripts/check-usage-pace.py
    fix_induced: false
    disposition: fixed
  - id: claude-m2
    severity: Low
    aim: deliverable
    component: scripts/check-usage-pace.py
    fix_induced: false
    disposition: fixed
```

Both halves of r1 returned MINORs only (Codex: NOT CONVERGED on two; Claude: see its file). Each finding is fixed with a case that was RED before the fix.

| Finding | Source | Fix | Case (scripts/check-usage-pace.py) | Mutation (scripts/mutations/check-usage-pace.json) |
|---|---|---|---|---|
| Tie `RISE_END_S == LAST_NIGHT_S` names a 99% that `refuse_at` never reaches | Codex 1, Claude | next stop is the 99% rise end only if `now < rise_end < night_at`; a tie goes to the hard limit | `backlog #525 r1 fold: a TIE ...` | `a tie names the 99% (< night_at becomes <=)` |
| Rise end already past (`RISE_END_S > LAST_NIGHT_S`, now in the plateau) names a past 99% | Codex 1 | the `now < rise_end` clause | `backlog #525 r1 fold: past the rise's end ...` | `a rise end already past is still named` |
| The 99% branch must stay reachable | own guard on the fix | (same expression) | `...while BEFORE a rise end that precedes the last night, the 99% IS the next stop` | `the 99% branch is unreachable` |
| Minute-only forecast time can be up to 59 s early (reset 02:37:42 shows 18:37) | Codex 2 | `local_time(t, exact=True)` adds `:%S` when `int(t) % 60`; used only for the forecast transition | `...a transition that is not minute-aligned shows its seconds`, `...an aligned transition keeps the minute form` | `the forecast never shows seconds`, `the forecast always shows seconds` |
| Docstring claimed "99% is never reached" unconditionally | Codex 1 | stated for the SHIPPED constants (RISE_END_S < LAST_NIGHT_S), with the general rule | n/a (prose) | n/a |
| Stale restatements of the rule | task | `.claude/hooks/usage-pace-spawn.sh:4`, `usage-pace-wake.sh:4`, `docs/memory/a-budget-stop-is-soft-with-a-reserve.md:21` now point at the docstring instead of restating it | n/a (prose) | n/a |

Self-test: 338 -> 343. Mutation pin for the file: 148 -> 153. The constants are patched in place inside the case and restored in `finally`.
