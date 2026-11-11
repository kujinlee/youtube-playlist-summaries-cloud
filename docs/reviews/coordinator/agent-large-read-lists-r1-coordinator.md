# Round 1 — `agent-large-read-lists` (PR #471, backlog #465) — coordinator — NOT CONVERGED (both halves); NARROWED

```yaml
round: 1
fixes_nontrivial: true
subject: agent-large-read-lists
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: bash-parser, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: true, component: bash-parser, disposition: narrowed}
  - {id: X3, severity: High, aim: deliverable, fix_induced: false, component: bash-parser, disposition: declined}
  - {id: X4, severity: High, aim: deliverable, fix_induced: true, component: bash-parser, disposition: narrowed}
  - {id: X5, severity: High, aim: deliverable, fix_induced: true, component: bash-parser, disposition: narrowed}
  - {id: X6, severity: Medium, aim: deliverable, fix_induced: true, component: bash-parser, disposition: narrowed}
  - {id: F1, severity: High, aim: deliverable, fix_induced: false, component: bash-parser, disposition: fixed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: true, component: bash-parser, disposition: narrowed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: true, component: bash-parser, disposition: narrowed}
  - {id: F4, severity: Low, aim: deliverable, fix_induced: false, component: bash-parser, disposition: declined}
```

REVIEW GAP: none

**Subjects.** Both halves reviewed `c377529a`. Codex's findings 1–6 are written X1–X6 here; the Claude half's are its
own F1–F4. `fix_induced` here means "introduced by this PR's list support", not by an earlier fold of this PR.

## The design decision: NARROW, failing toward allow

PRs #468 and #469 showed that a shell-parsing surface keeps yielding edge cases when each one is patched. So this fold
patches one real defect (the redirect regex, X1/F1, which merged two commands into one) and NARROWS the rest: each
input the reviewers found now makes the whole list ALLOWED, the hook's in-doubt direction, rather than being modelled
more exactly. The bound is stated in the docstring.

## Dispositions

| ID | Finding | Disposition |
|---|---|---|
| X1 / F1 | `STDERR_REDIRECT`'s `\S+` swallowed a following `;`/`&&`/`\|` (`2>/dev/null;`), merging two commands: `sed -n 1,200p a 2>/dev/null; sed -n 1,200p b` allowed (400 printed); `cat a 2>/dev/null; head -n 1 b` (201), `cat small 2>/dev/null; wc -l big` (101) and the pipeline `cat big 2>/dev/null\|head -5` (5) denied | FIXED: a redirect's target ends at an operator character (`;&\|<>()`); the list is split first (`split_list` keeps a stderr redirect in its part instead of reading its `>`/`&` as an operator) and the redirect is removed per part (`simple_command`). Verdicts now deny / allow / allow / allow, matching bash. Case + 2 mutations (regex, split branch) |
| X2 | `printf -v D x` assigns, so `printf` was not state-free: false refusal and silent allow | NARROWED: `printf` removed from `LIST_ZERO`; a list with `printf` is allowed whole. Case + mutation |
| X3 | `cat a ';'; cat b` (401 printed) allowed: `shlex` drops the quotes, so `';'` reads as an operator | NO CODE CHANGE: it fails toward allow; added to the docstring's stated bound |
| X4 | `cd missing; cat a; cat b`: a failed `cd` before `;` moved the modelled cwd | NARROWED: only ONE leading `cd DIR &&` is accepted (master's old prefix behaviour); any other `cd` part (after `;`, a second `cd`, not first) allows the whole list. Case + 2 mutations |
| X5 | `cd logical/link; cd ..; cat big`: a second `cd` is logical traversal, not filesystem | NARROWED with X4 (a second `cd` allows the whole list). A single leading `cd DIR/..` through a symlink keeps master's `os.path.join` behaviour, unchanged by this PR |
| X6 / F2 | `cat big;;`, `; cat big`, `cat big &&`, `cat a && ; cat b` are bash syntax errors (0 lines) but were denied | NARROWED: only ONE trailing `;` is accepted; any other empty part allows the whole list. Case + 2 mutations; the old empty-part mutation now severs the trailing-`;` drop |
| F3 | ANSI-C `$'...\'...'` is not tracked by `split_list`: `echo $'\';cat big;echo ' \'` (1 line) denied | NARROWED: `$'` anywhere allows the whole list. Case + mutation |
| F4 | one unjudgeable part makes the whole list NOT CHECKED (loudly) | NO CHANGE: matches the single-command `Unreadable` rule |

**Collateral.** The case `cd DIR; cat small; cd DIR; cat b300` (deny) left the `&&`-list case: under the narrowing it
is allowed. The `cd -` and `#` cases moved from `cd DIR;` to `cd - &&` (payload cwd) and `cd DIR &&`, since a `cd`
after `;` now allows the list on its own and would have masked them (the `#` mutation survived until it moved).
Self-test 96 → 101 cases; mutations 95 → 103 (pin in `scripts/check-plan-code.py`).
