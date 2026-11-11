# Round 2 — `agent-large-read-guard` (PR #469, backlog #457) — coordinator — NOT CONVERGED (Codex); Bash NARROWED to a simple command

```yaml
round: 2
fixes_nontrivial: true
subject: agent-large-read-guard
halves:
  codex: ran
  claude: skipped
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: false, component: bash-parser, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: bash-parser, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: false, component: bash-parser, disposition: fixed}
  - {id: X4, severity: Medium, aim: deliverable, fix_induced: false, component: bash-parser, disposition: fixed}
  - {id: X5, severity: Low, aim: deliverable, fix_induced: true, component: bash-parser, disposition: fixed}
```

REVIEW GAP: claude — alternation. Round 2 runs ONE half; this round it is Codex (`review-method.md` → *Round topology*).

Codex reviewed head `91640452`: **NOT CONVERGED**, five findings, all in the Bash parser: pipeline stages (X1–X3),
heredocs (X4) and a 4301-digit number (X5). X1 was labelled BLOCKER (Q4c). Its numbering 1–5 is written X1–X5 here.

## The design decision: Bash is read only as a SIMPLE command

The same move as PR #468. Round 1 fixed six parser findings and round 2 found five new ones in the code those fixes
added: pipeline and heredoc parsing is an open surface, and each round finds its next edge case. The coordinator
NARROWED it. The hook now reads a Bash command only when it is ONE invocation of `cat`, `head`, `tail` or `sed`, after
at most one `cd DIR &&` prefix, with no newline, `$(` or backtick, and no shell-operator token (`|`, `|&`, `;`, `&&`,
`||`, `&`, `(`, `)`, `<`, `<<`, `>`). `scripts/check-agent-large-read.py:simple_command` is that test. ANY other
command is allowed silently (exit 0, nothing printed): a STATED BOUND, not NOT CHECKED, because it is common and not
an error.

**Removed:** the pipeline stage loop, the filter-stage exemption, the heredoc first-line truncation, segment
splitting on `&&`/`||`/`;`/`&`, `NAME=value` assignments, the subshell NOT CHECKED, their cases and their mutations.
**Kept as they were:** `sed` multi-file streaming, `q`, globs, `-`, `$VAR`/`~` from the environment, and the Read
rules.

**What the bound costs, ESTIMATED** (this session's transcripts, `big2.py` cost model: tokens = characters / 2, cost
= tokens × (1.25 + 0.1 × later calls before the next context reset); the simple/compound test is the hook's own
`simple_command`, imported). Of the over-8 KB subagent file-read results whose output is over 300 lines (5.84M,
2.54% of 230M): Read 54% and simple commands 16% are covered; compound commands 30% are not, of which a list of
several readers (`sed -n 1,200p a; sed -n 1,200p b`) is 21% and a pipeline 6%. Over all over-8 KB file-read
results, at any line count (12.88M), compound is 59%, Read 26%, simple 14%.

## Dispositions

| ID | Finding | Disposition |
|---|---|---|
| X1 (BLOCKER label) | `cat a \| sed s/x/y/ b` allowed, 500 lines printed from `b` | RESOLVED BY NARROWING: every pipeline is allowed silently, a STATED bound in the docstring and the PR body. Replayed: allow, exit 0, nothing printed — now by design |
| X2 | `cat big \| head -c 1` and `cat big \| sed -i.bak … a` denied (1 byte, 0 lines) | RESOLVED BY NARROWING: a pipeline is not read. Replayed: allow |
| X3 | `cat a \| grep x b` allowed, 500 lines from `b` | RESOLVED BY NARROWING: the filter exemption is gone with the pipeline code; a pipeline is the stated bound. Replayed: allow |
| X4 | `cat <<big …` denied (a delimiter matched a file); `cat <<EOF … EOF` then `cat big` allowed | RESOLVED BY NARROWING: a newline or `<<` makes the command compound. Replayed: both allow; the second is the stated bound |
| X5 | `sed -n '<4301 digits>q' big` tracebacks (`int` limit) | FIXED: a line number or count is at most 18 digits (`SED_RANGE`, `SED_QUIT`, `COUNT`), so a longer one does not match and is NOT CHECKED. Sibling, the 4301-digit `p` address, and `head -n <4301 digits>`, fixed with it. Replayed: exit 1, NOT CHECKED, no traceback |

## Checks run on the fold

- `--self-test`: 85/85.
- `check-plan-code.py --mutate . --only scripts/check-agent-large-read.py`: 83 mutations, 83 killed and attributed
  (`EXPECTED_MUTATIONS` 83): 58 kept, 19 removed with the code they mutated, 25 added — one per clause of
  `simple_command` (each `COMPOUND` alternative and each `OPERATOR` character), `-` as stdin, the per-file switch, the
  environment, and the four 18-digit bounds. The first sweep had two survivors, both fixture defects: `echo cat big`
  fell into the `sed` branch and was allowed either way (case now `echo -n cat big`), and the `-` case's cwd had a file
  named `-n`, not `-` (the case now writes one).
- Every Codex r2 repro replayed through `bash .claude/hooks/run-hook.sh agent-large-read.sh` as above; `cat big` and
  `sed -n 1,400p big` still deny, `head -n 300 big` allows.
- `check-fixture-variation.py scripts/check-agent-large-read.py`: OK. `check-selftest-counts.py --only`: verified.
