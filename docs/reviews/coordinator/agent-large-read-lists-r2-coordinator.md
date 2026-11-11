# Round 2 — `agent-large-read-lists` (PR #471, backlog #465) — coordinator — NOT CONVERGED (both halves); SURFACE REMOVED

```yaml
round: 2
fixes_nontrivial: true
subject: agent-large-read-lists
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: true, component: bash-parser, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: true, component: bash-parser, disposition: narrowed}
  - {id: X3, severity: High, aim: deliverable, fix_induced: true, component: bash-parser, disposition: narrowed}
  - {id: X4, severity: Medium, aim: deliverable, fix_induced: true, component: bash-parser, disposition: fixed}
  - {id: F1, severity: Medium, aim: deliverable, fix_induced: true, component: bash-parser, disposition: fixed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: true, component: bash-parser, disposition: fixed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: true, component: bash-parser, disposition: narrowed}
  - {id: O1, severity: Low, aim: deliverable, fix_induced: false, component: bash-parser, disposition: narrowed}
```

REVIEW GAP: none

**Subjects.** Both halves reviewed `f2d25120` (AMPLE mode: both halves ran this round). Codex's findings 1–4 are written
X1–X4 here; the Claude half's are its own F1–F3, and O1 is its "observed, not raised" `grep` row. `fix_induced` here
means "introduced by the round-1 fold" — every r2 finding came from that fold's redirect and `cd` handling.

## The design decision: REMOVE the parsing surface, do not patch it

Every r2 finding was caused by the round-1 fold's per-part redirect parsing. Patching it again would be a third round
on the same component (the thrashing shape). The coordinator decided to remove the surface:

- **A. MASTER'S PATH, UNCHANGED.** A command with no unquoted `;`/`&&`, or only master's one `cd DIR &&` prefix, takes
  master's code (`simple_spans`, master's `bash_spans` verbatim; master's `STDERR_REDIRECT` and `simple_command`
  restored) and gets master's verdict. The r1 operator-stop regex is gone.
- **B. LISTS ARE STRICT.** Any other `;`/`&&` list is summed only if it holds none of `LIST_STRICT` (`<`, `>`, a
  backslash, `$'`, `` ` ``, `$(`); otherwise the whole list is allowed. No redirect is parsed inside a list.
- **C. `grep` leaves `LIST_ZERO`**: `grep "" f500; cat f100` printed 600 and was allowed.

**Stated bound (docstring):** `cat a 2>/dev/null; cat b` (400 printed) is now ALLOWED. Master denied it, but only by
accident: its `\S+` target swallowed the `;` and read the two commands as one `cat`. Same for `cat big 2>&-; cat
small` (600). Both are lists with a redirect, so B allows them.

## Dispositions (verdicts are this head's; `bash N` is what bash printed)

| ID | Finding | Disposition |
|---|---|---|
| X1 | `cd . 2>/dev/null && cat big` (bash 500) allowed: the `cd` part was tokenised with its redirect | FIXED by A: master's `cd DIR &&` path, deny (= master) |
| X2 | `cat a; cat b 2>err\;x` (bash 400): the redirect regex consumed the `\` of `\;` | NARROWED by B: a list with `>` or `\` is allowed whole (stated bound) |
| X3 | `cat small 2>&1big; true` (bash 0) denied as 600 | NARROWED by B: allowed (= master) |
| X4 | `cat ' 2>x(big)'` (bash 100) denied, reading the quoted name as a redirect | FIXED by A: NOT CHECKED (= master) |
| F1 | `cd sub 2>/dev/null && head -n 400 ../f500` (bash 400) allowed | FIXED by A: deny (= master). The list form `cd sub 2>/dev/null && cat a && cat b` is allowed by B (master allowed it too) |
| F2 | `cat big 2>&-` (bash 500) allowed: `&` was excluded from the target class | FIXED by A: deny (= master) |
| F3 | `cat a;2>/dev/null cat b` (bash 400) allowed | NARROWED by B: allowed, a stated bound (a list with `>`) |
| O1 | `grep "" f500; cat f100` (bash 600) allowed: `grep` was a zero-line part | NARROWED by C: `grep` is not in `LIST_ZERO`, so a list with it is allowed whole. The bash result is the same; the rule is now honest about it |

**Tests.** Self-test 101 → 107 cases. New cases: master's path on every reviewer input that master handled (X1, X4,
F1, F2, `cd - &&`), with verdicts derived by running master's script; master's own false refusal kept (`cat big
2>/dev/null|head -5`); the strict-list case (X2, X3, F3, the trade-off, a backslash-only list); the escaped `;`; the
`grep` case; and two that re-bind r1 mutations whose case moved to master's path (`;` in `OPERATOR` now pinned by
`cat big ';'`, allowed as stated; the list part's `shlex` guard by `cat small; echo 'x`). Removed: the r1 redirect case. Changed: the `;`-list case drops its redirect input, the escaped-`;`
input moves into the strict-list case, and the `cd -` list case gains `&& echo` (bare `cd - && cat` is master's path
now). Mutations 103 → 106: A severed three ways (single command routed to the list path, the `cd DIR &&` form routed
to the list path, r1's regex restored), B severed two ways (backslash/`$'`, redirects), C once. The r1 mutation "the
list split reads a stderr redirect's `>`" was repurposed, since its branch is gone. Pin updated in
`scripts/check-plan-code.py`.
