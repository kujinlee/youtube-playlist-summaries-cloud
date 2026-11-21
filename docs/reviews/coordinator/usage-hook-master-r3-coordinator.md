# Round 3 — `usage-hook-master` — coordinator — ⟳ NOT CONVERGED (Claude); THRASHING → Phase 6 redesign folded

Claude reviewed `593ca25d` (PR #610, backlog #513) in `docs/reviews/claude/usage-hook-master-r3-claude.md`. It returned
C1 MAJOR, M1, M2 and M3 MINOR, and the B2 layout, and its verdict is NOT CONVERGED. The Codex half is a gap by
alternation; round 4 is Codex's.

REVIEW GAP: codex — alternation.

```yaml
round: 3
fixes_nontrivial: true
subject: usage-hook-master
halves:
  codex: gap
  claude: ran
findings:
  - {id: C1, severity: Major, aim: deliverable, fix_induced: false, component: locate-main, disposition: fixed}
  - {id: M1, severity: Minor, aim: deliverable, fix_induced: true, component: locate-main, disposition: fixed}
  - {id: M2, severity: Minor, aim: documentation, fix_induced: true, component: locate-main, disposition: fixed}
  - {id: M3, severity: Minor, aim: deliverable, fix_induced: false, component: locate-main, disposition: fixed}
```

**The thrashing pair.** Round 2's X1 was caused by the r1 fold. Round 3's M1 was caused by the r2 fold. Both are in
`locate-main`. Two consecutive rounds therefore carry findings caused by the previous round's fix in one component.
That is the arming condition, so Phase 6 convened:
`docs/reviews/architecture-review-2026-11-20-usage-hook-launcher.md`.

The redesign is that **git names the main checkout**:

- The hand-parsing is deleted.
- One `git rev-parse --git-dir --git-common-dir --show-toplevel` runs with every `GIT_*` unset and a 5 s alarm.
- A bare repository is NOT RUN.
- Main is the checkout that owns the common dir.
- Anything git cannot answer is NOT RUN.

The added cost is about 37 ms per usage-pace launch, measured, and nothing for any other hook.

## Dispositions (each input is a case over a real git layout)

| Finding | Disposition | Case and git's answer |
|---|---|---|
| **C1** (MAJOR). `wB/.git` = `gitdir: main/.git` ran wB's copy. | FIXED | Case *C1WB*. git's common dir is `main/.git`, so **main's** copy runs. A precondition row reads git's git-dir and common-dir for wB. Mutant **g10** is the literal "git-dir == common-dir → own copy" rule and is killed by C1WB. |
| **B2**. A gitdir moved out of `worktrees/`, with no `commondir` and with `objects/`. | BOUND | Case *B2*. git reads a standalone repository, so **its own** copy runs. This is git's answer, stated in the launcher's BOUNDS comment and the arch review. |
| **M1** (MINOR, fold-caused). A `--separate-git-dir` main at `…/worktrees/proj` and a submodule at `worktrees/x` were refused. | FIXED | Cases *M1SEP* and *M1SUB*. Each runs **its own** copy. A precondition row checks that mK's git dir is its own common dir at a worktrees path. Mutant **g8** is killed by M1SEP. |
| **M2** (MINOR, fold-caused). The r2 doc said a bound was "stated in the launcher's comment", but it was not. | FIXED / SUPERSEDED | The r2 doc's "Bound, stated in the launcher's comment: a submodule whose NAME is `worktrees/<x>` … is NOT RUN" (`usage-hook-master-r2-coordinator.md`, the line after the (c) bullet) is **false and superseded here**. That bound no longer exists, because M1SUB runs. The launcher now carries a `⚠ BOUNDS, stated (r3 M2)` comment naming the bounds that do hold. |
| **M3** (MINOR). Worktrees of a bare repository, a submodule and a separate-git-dir main were NOT RUN. | FIXED (submodule) / BY DESIGN (others) | Case *SUBWT* runs the **submodule's** copy. Case *BARE*, and *BAREGIT* (a bare repository named `.git` beside a usage hook), are NOT RUN "is bare", and a precondition row checks that git reports core.bare true. Case *SEPWT* is NOT RUN "names no main checkout". Mutants **g5**, **g7** and **g9**. |

## Every r1–r2 input, kept, with git's answer

The r1 and r2 broken layouts below are each still NOT RUN. Each case now asserts the reason "git cannot read the
repository":

- U4 (bare-path) and U5 (junk `.git`);
- GONE, DANG, NOCD, DECOY and the fakes missing objects/ or refs/;
- JUNKGD, UNREAD, LOCKGIT and NLCD.

X2's newline main (NL) is NOT RUN with "is not three lines". SYM (C2) is NOT RUN with "has no .claude/hooks/", unchanged.

Three cases **changed to RUN**, each with git's answer:

- **NOCDOBJ** (r2 X1) runs its own copy, because git reads it as a standalone repository.
- **OTHER** runs `other`'s copy, because git takes `other/.git` as the common dir.
- **fake-HEAD** runs the fake's copy. Measured under git 2.49: git tests a common dir's `objects/` and `refs/`, not its
  HEAD. Each fake's gitdir now has its own HEAD, as a real worktree's does. Before that, git refused every fake for
  the gitdir's missing HEAD, whatever part was missing, and the manifest's "fakes lack no part" entry was caught only
  by its precondition row. The same applies to X2's NLCD gitdir: without its HEAD, the newline was not what refused
  it, and the mutation survived.

Both are stated as the same bound as B2: whoever can rewrite `.git` or `commondir` chooses git's repository.

New cases:

- the cwd inside `main/.git`, and a stray empty `.git` inside main, both run main's copy;
- four GIT_* steering cases each run main's copy, and kill **g0** (sanitization deleted) and **g0b** (only GIT_DIR unset);
- a one-line fake git and a never-answering fake git on PATH are NOT RUN, and kill **g4** and the alarm mutant **g1**.

The W7 cases, which check that no environment steers an ordinary hook, pass unchanged: ordinary hooks run no git.

## Mutants and manifest

- **Shell mutants retired** with the code they mutated: u2–u7, c1a–c1g and r2a–r2g.
- **Shell mutants added:** g0, g0b and g1–g12.
- **Kept:** m1–m18, u1, u8, c2, c3a, c3b and r-<name>.
- **`scripts/mutations/check-run-hook.json`** goes from 39 to 47 entries; the pin is 47, with its reason in
  `expected_mutations.py`.
  - Every r1/r2 world entry is kept.
  - The stderr-comparison entry now names g2, because c1d was retired.
  - The two NOCDOBJ/OTHER entries name the renamed cases.
  - The eight new entries each unmake one r3 world: two steering envs, mK's separate git dir, the bare clone, B2's
    `objects/`, the two fake gits and wB's gitdir.
- Every anchor occurs exactly once.
- The docstring says `# 163 cases`.
