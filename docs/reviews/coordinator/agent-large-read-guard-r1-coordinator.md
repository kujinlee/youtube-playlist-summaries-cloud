# Round 1 — `agent-large-read-guard` (PR #469, backlog #457) — coordinator — NOT CONVERGED (both halves); REDESIGNED (the re-read rule removed)

```yaml
round: 1
fixes_nontrivial: true
subject: agent-large-read-guard
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: false, component: bash-parser, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: bash-parser, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: false, component: read-rule, disposition: fixed}
  - {id: X4, severity: Medium, aim: deliverable, fix_induced: false, component: bash-parser, disposition: fixed}
  - {id: X5, severity: Medium, aim: deliverable, fix_induced: false, component: reread-rule, disposition: redesigned}
  - {id: X6, severity: Low, aim: deliverable, fix_induced: false, component: input-validation, disposition: fixed}
  - {id: X7, severity: Low, aim: instrument, fix_induced: false, component: mutations, disposition: fixed}
  - {id: F1, severity: Major, aim: deliverable, fix_induced: false, component: bash-parser, disposition: fixed}
  - {id: F2, severity: Major, aim: deliverable, fix_induced: false, component: read-rule, disposition: fixed}
  - {id: F3, severity: Major, aim: deliverable, fix_induced: false, component: reread-rule, disposition: redesigned}
  - {id: F4, severity: Medium, aim: deliverable, fix_induced: false, component: reread-rule, disposition: redesigned}
  - {id: F5, severity: Medium, aim: deliverable, fix_induced: false, component: reread-rule, disposition: redesigned}
  - {id: F6, severity: Minor, aim: deliverable, fix_induced: false, component: bash-parser, disposition: fixed}
  - {id: F7, severity: Minor, aim: deliverable, fix_induced: false, component: bash-parser, disposition: fixed}
  - {id: F8, severity: Minor, aim: deliverable, fix_induced: false, component: reread-rule, disposition: redesigned}
```

**Subjects.** Codex reviewed `46ce8031` (before the security fold); the Claude half reviewed `63d77c7b`, whose script
it checked byte-identical to its working tree. Both: NOT CONVERGED. Codex's IDs are written X1–X7 here (its own numbering
1–7); the Claude half's are its own F1–F8.

## The design decision: the re-read rule is REMOVED

Rule (b) refused a re-read of more than 50 lines the same agent had already read from an unchanged file. It needed
per-agent state on disk (a 0700 directory, its symlink and owner checks, 24 h pruning). The round showed it produced
most of the false refusals:

- after a compaction or context editing had removed the earlier lines from the context (F3), while the denial said
  "They are still in your context";
- on the retry of a call that had failed, because a read was recorded when the hook allowed it (F4);
- on the Read that Edit requires after a `sed -n` read, since a Bash read does not satisfy Edit (F5);
- on lines "read" by a pipeline stage that never printed them, e.g. `cat big | head -n 100 small` poisoned `big` (X1,
  history half);
- on an exact repeat Read, which Claude Code 2.1.309 already answers with "File unchanged since last read" (X5; both
  halves MEASURED this in the binary).

It targeted 57 of the 257 large reads in the audit, about 0.9% of usage. **Removed:** the rule, `REREAD_MAX_LINES`,
`STATE_TTL_S`, the state directory and its security code, `load_state`, their cases and their mutations. The hook is
stateless. Resolved by removal: X1's history half, X5, F3, F4, F5, and the corrupt-state traceback (F8, X6's second
half).

## Dispositions

| ID | Finding | Disposition |
|---|---|---|
| X1 | a later pipeline stage's file operands were discarded: `cat small \| head -n 400 big` allowed (400 lines) | FIXED: a later stage that names files reads them, not the pipe; `-` is the pipe. Cases for both directions and for `-`. History half: removed with rule (b) |
| X2 | a glob operand was read as a literal missing path: `cat b*` allowed (1,216 lines) | FIXED: an operand with `*`, `?` or `[` is expanded relative to the cwd (after `cd`); a glob that matches nothing is NOT CHECKED. Bound stated: quoting is not visible, so `'*.txt'` is expanded too |
| X3 / F2 | Read of a notebook or PDF counted its bytes; the tool ignores offset/limit for these | FIXED: `NOT_TEXT` = `ipynb`, `pdf`, `png`, `jpg`, `jpeg`, `gif`, `webp`, allowed. MEASURED in the 2.1.309 binary: `ext=extname(path).toLowerCase().slice(1)`; `jx` (`.ipynb`) resets offset/limit and returns every cell; `$_n=new Set(["png","jpg","jpeg","gif","webp"])`; `il=new Set(["pdf"])` renders by `pages`. An extensionless image is sniffed by the tool; here it is caught by the NUL sniff |
| X4 | `sed -n '1,400p;1q'` counted 400 (prints 1); several files counted per file | FIXED: `q` is modelled (a `p` before `Nq` prints line N, one after does not; bare `q` is line 1); `sed` counts against the concatenation of its files. `sed -s` is NOT CHECKED. Sibling: `head -n -K` is now exact (every line but K), not an upper bound |
| F1 | `sed -n '1,200p' a200 b200` denied (200 lines printed) | FIXED with X4: case for '1,200p' (allow) and '1,400p' (deny) over two 200-line files |
| X5 | identical Read already de-duplicated by the harness | RESOLVED BY REMOVAL of rule (b) |
| X6 | malformed input tracebacks: `cwd: 23`; corrupt state | FIXED: a non-string `cwd` is NOT CHECKED (decide and main cases). The state half is removed with rule (b) |
| X7 | clause-removal coverage claim false (`SED_QUIT`, size-vs-mtime) | FIXED: the manifest was rebuilt as one entry per clause of the remaining code, 77 entries, each killed and attributed. The size/mtime clause is gone with rule (b); the `q` handling has four entries |
| F3, F4, F5, F8 | re-read false refusals; corrupt state traceback | RESOLVED BY REMOVAL of rule (b) |
| F6 | `\|&` read as a file; `(cd … && cat …)` resolved in the wrong directory | FIXED: `\|&` is a pipe; a segment that opens with `(` is NOT CHECKED. `$(…)` in an assignment is not affected (case) |
| F7 | `head -q -n 5` NOT CHECKED | FIXED: `-q`, `-v`, `--quiet`, `--silent`, `--verbose` are skipped as flags (case: `head -q -n 400` still denied) |

**Not findings, folded anyway.** `tee` and a reader after a non-reader stage are added to NOT COVERED. The denial now
leads its remedy with "TO GET THE CONTENT: `grep -n` …, then … `offset` and `limit`, or `sed -n 'a,bp'`" (case pins
all four).

## Checks run on the fold

- `--self-test`: 85/85.
- `check-plan-code.py --mutate . --only scripts/check-agent-large-read.py`: 77 mutations, 77 killed and attributed
  (`EXPECTED_MUTATIONS` 77). Two defects the first sweep found and the fold fixed: `'400p'` could not tell one line
  from "N to the end" (case now `'100p'`), and a plain-text mutation crashed the suite without a `[FAIL]` line
  (replaced by a `deny`→`ask` mutation).
- Every reviewer repro replayed through `bash .claude/hooks/run-hook.sh agent-large-read.sh`: X1 deny / allow, X2 deny,
  X3 allow, X4 allow, F1 allow, X6 NOT CHECKED (exit 1, no traceback), F6 allow / NOT CHECKED, F7 allow.
- `check-fixture-variation.py`: OK, with `decide.now`, `decide.state_dir`, `main.state_dir` and the dead exemption
  removed.
