# Round 3 — `agent-large-read-lists` (PR #471, backlog #465) — coordinator — NOT CONVERGED (Codex); THRASHING, Phase 6 convened

```yaml
round: 3
fixes_nontrivial: true
subject: agent-large-read-lists
halves:
  codex: ran
  claude: skipped
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: true, component: bash-parser, disposition: fixed}
```

REVIEW GAP: claude — alternation

**Subject.** Codex reviewed `877686d5` (the round-2 fold). Rounds 2+ alternate, so the Claude half did not run this
round. Codex's one finding is written X1 here. `fix_induced` means "introduced by the round-2 fold".

## Dispositions (verdicts are this head's; `bash N` is what bash printed)

| ID | Finding | Disposition |
|---|---|---|
| X1 | `true; cd . '&&' cat big` (bash 0) DENIED as 500: `list_spans` called master's `simple_command(part)`, whose `cd DIR &&` prefix parser (quote-unaware after `shlex`) read the literal `'&&'` as an operator inside a list part | FIXED: master's prefix handling stays in master's path (the whole command). In `list_spans`, a part that `simple_command` resolves through a `cd` prefix makes the WHOLE list allowed; any other `cd` part but the one leading `cd DIR &&` already did. Both `true; cd . '&&' cat big` and `cat a; cd . '&&' cat big` (bash 200) are now allowed |

**Tests.** Self-test 107 → 108 cases: one new case with the reproducer and the `cat a; ...` variant (the list falls
back to allow). Mutations 106 → 107: one severs the new rejection (`if simple[0] is not None` → `if False`), naming
the new case. The r1 mutation "a list counts only its first reader" was re-bound: its anchor named the line the fix
replaced. Pin updated in `scripts/check-plan-code.py`.

## Thrashing

The Phase 6 arming condition (`docs/dev-process.md`: two consecutive rounds whose findings came from the previous
round's own fix, in one component) is **MET**.

- **Round 2 — every finding caused by the round-1 fold.** All eight r2 findings (X1–X4, F1–F3, O1;
  `agent-large-read-lists-r2-coordinator.md`) are `fix_induced: true`, `component: bash-parser`: the r1 fold's
  per-part redirect parsing and `cd` handling. Examples: `cd . 2>/dev/null && cat big` (bash 500) allowed because the
  `cd` part was tokenised with its redirect (X1); `cat a; cat b 2>err\;x` (bash 400) because the r1 redirect regex
  consumed the `\` of `\;` (X2); `cat ' 2>x(big)'` read the quoted name as a redirect (X4).
- **Round 3 — the finding caused by the round-2 fold.** X1 above exists only because the r2 fold restored master's
  `simple_command` (with its `cd DIR &&` prefix parser) and `list_spans` then called it on each list part, so master's
  quote-unaware prefix parsing leaked into list parts.
- **One component.** Both rounds' findings are in the shell-command parser of `scripts/check-agent-large-read.py`
  (`simple_command` / `split_list` / `list_spans`).

Two consecutive rounds of fix-caused findings in one component: a focused architecture review of that parser is
convened, next, by the coordinator. It is not written here.
