# Round 1 — `586-slice2` — coordinator — both halves NOT CONVERGED; every finding goes to the fold

Subject: PR #565 (DRAFT), branch `586-slice2`, reviewed head `b0703863`. Halves:
`docs/reviews/codex/586-slice2-r1-codex.md` (4 Major) and `docs/reviews/claude/586-slice2-r1-claude.md` (6 Major, 1 Minor).
Every finding is a FAIL-OPEN: a log the reviewer built returns a read set smaller than the truth, with no refusal. The
coordinator re-ran all four Codex inputs through `resolve_log` at 03:16 and each reproduced exactly (refusal `None`).

Two pairs are the SAME defect and keep both ids so each half's record is answered:
- Codex #2 = Claude F5 — `link`/`linkat` of (or through) a runtime symlink is not tracked as a runtime link.
- Codex #3 = Claude F1 — an operation in flight (an unfinished relative-path call, or an unfinished `chdir`) on one
  CLONE_FS thread overlapping a `chdir` on a sibling is not a `cwd race`. Claude F2 is the fork-entry variant of the same
  window and is folded with it.

```yaml
round: 1
fixes_nontrivial: true
subject: 586-slice2
halves:
  claude: ran
  codex: ran
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fold}
  - {id: X2, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fold}
  - {id: X3, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fold}
  - {id: X4, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fold}
  - {id: C1, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fold}
  - {id: C2, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fold}
  - {id: C3, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fold}
  - {id: C4, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fold}
  - {id: C5, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fold}
  - {id: C6, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fold}
  - {id: C7, severity: Minor, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fold}
```

## The class, not the instances

Two roots cover most of the eleven:
1. **Text read where the meaning is structural** — X1 (a flag name searched in the whole argument string, filenames
   included), X4 (a return label accepted without its closing `>`), C6 (success = "does not start with `-1 `", so
   `= ? ERESTARTSYS` counts), C7 (a trailing slash dropped before the follow decision). Fold rule: parse the return
   value and the flag operand into fields once, and decide from fields; anything that does not parse REFUSES.
2. **An enumerated model of the kernel that is short of the kernel** — X2/C5 (`link*`), C4 (`RENAME_EXCHANGE`), C3
   (`/proc/<pid>/task/<tid>/…`), X3/C1/C2 (in-flight windows). Fold rule: where the model cannot enumerate, refuse —
   any `link*` touching a runtime link, any `renameat2` with a flag other than none/NOREPLACE, any `/proc/` path not
   matched by the resolver, any relative-path or `chdir` call whose entry/exit window overlaps a sibling sharing FS.

A false refusal is safe (falls back to today's selection); the fold should prefer refusing to modelling.

## Not findings (recorded by the Claude half)

`[pid N]` prefixes, truncated paths, relative `symlinkat`, renaming a directory holding a link, a copy path through a
symlink — all refused correctly. `unshare(CLONE_FS)` is left to slice 3's `DENIED_SYSCALLS` per the plan; slice 3 must
not drop it.

## Next

A fresh fold agent turns every reviewer input above into a failing self-test case FIRST, then fixes; then round 2 runs
ONE half (alternation) on the folded head.
