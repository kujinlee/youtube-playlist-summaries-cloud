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
  - {id: X1, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fixed}
  - {id: X2, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fixed}
  - {id: X3, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fixed}
  - {id: X4, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fixed}
  - {id: C1, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fixed}
  - {id: C2, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fixed}
  - {id: C3, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fixed}
  - {id: C4, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fixed}
  - {id: C5, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fixed}
  - {id: C6, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fixed}
  - {id: C7, severity: Minor, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fixed}
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

## How the fixes were proved

Fold on head `04063844`, in `scripts/strace_reads.py`; every disposition above is now `fixed`, none filed.

- **Before:** every reviewer input became a `_self_test_body` case asserting the refusal (15 cases: X1, X4 ×2, C6 ×2,
  C7, X2, C5a, C5b, C4, C3 ×2, X3, C1, C2), plus 26 adjacent probes. On the UNFIXED code the suite printed
  **102/133** — the 31 failures were exactly the 15 reviewer cases and the 16 adjacent probes that expect a refusal.
  The other 10 adjacent probes are controls, and they passed both before and after the fix.
- **After:** **134/134**. One more adjacent probe was added during mutation (a `readlink` *below* a /proc magic link),
  because no case could fail for the non-final half of the /proc rule. The two whole-log end-to-end fixtures still
  pass.
- **The fix, by class:**
  1. *Fields, not text.* `RET` is the return grammar: a label without its `>`, or a last line with no newline, is
     `log did not parse`. `outcome()` gives success, failure or unknown. A `= ?` cwd change is refused with the new
     reason `unknown return`; for symlinks, renames and removers, `= ?` counts as made. `FLAG_OPERAND` names the one
     operand an `AT_*` flag is read from. A trailing `/` or `/.` forces a follow.
  2. *Refuse where the model is short of the kernel.* `link`/`linkat`: the source is always checked as followed.
     `renameat2` with a flag beyond RENAME_NOREPLACE, an `openat2` RESOLVE_IN_ROOT, and any flags operand that does
     not parse are refused with the new reason `unmodelled flags`. `PROC` now covers `task/<tid>/`, `exe` and
     `map_files/`. `_cwd_overlap` replaces the fork counter: any cwd-change window that overlaps, in the same
     filesystem context, another cwd change, a cwd-relative call or a copying clone is a `cwd race`.
- **One deliberate loosening:** a call that does NOT follow a /proc magic link as its final component
  (`readlink /proc/self/exe`, which both whole-log fixtures contain) is no longer refused, because it reads only the
  link's text. A lookup below such a link, or a call that follows one, is still refused.
- **Adjacent probes added (27):** 17 expect a refusal, 10 are controls. They cover:
  - newfstatat with the flag name only in the path;
  - a real NOFOLLOW (control);
  - an unparseable statx operand;
  - RENAME_WHITEOUT;
  - a file named RENAME_EXCHANGE (control);
  - linkat AT_EMPTY_PATH, and linkat without a flag;
  - a hard link of an ordinary file (control);
  - an fchdir in flight;
  - two chdirs in flight;
  - an AT_FDCWD probe in flight;
  - an absolute call across a chdir (control);
  - another filesystem context (control);
  - fchdir `= ?`;
  - a successful fchdir (control);
  - `/proc/thread-self/cwd` and `/proc/self/task/<tid>/root`;
  - following `/proc/self/exe`, and readlink of it (control);
  - task status (control);
  - a lookup below a magic link;
  - no final newline;
  - a dup2 label cut short;
  - a trailing `/.`;
  - an unlink with a trailing slash;
  - symlink `= ?`;
  - openat2 RESOLVE_IN_ROOT.
- **Mutations:** the pin went from 62 to **82**. The refactor orphaned 13 existing anchors; all 13 were re-bound to the
  new text, and 20 new mutations cover the new branches.
  - `check-plan-code.py --mutate . --only scripts/strace_reads.py` gives **82 killed, 82 attributed, 0 survivors**.
  - The first sweep had 2 survivors:
    - one was an equivalent mutation, re-bound to the old bug (honouring the flag anywhere in the arguments);
    - the other was a real gap, closed by the new case above.
