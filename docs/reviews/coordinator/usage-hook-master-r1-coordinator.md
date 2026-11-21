# Round 1 — `usage-hook-master` — coordinator — ⟳ NOT CONVERGED (both halves); every finding FIXED

Both halves reviewed `ca56bebe` (PR #610, backlog #513): Claude (`docs/reviews/claude/usage-hook-master-r1-claude.md`,
C1 BLOCKER, C2–C5 MINOR) and Codex (`docs/reviews/codex/usage-hook-master-r1-codex.md`, X1 and X2 BLOCKER, X3 MAJOR).
Both NOT CONVERGED.

```yaml
round: 1
fixes_nontrivial: true
subject: usage-hook-master
halves:
  codex: ran
  claude: ran
findings:
  - {id: C1, severity: Blocking, aim: deliverable, fix_induced: false, component: locate-main, disposition: fixed}
  - {id: C2, severity: Medium, aim: deliverable, fix_induced: false, component: locate-main, disposition: fixed}
  - {id: C3, severity: Medium, aim: deliverable, fix_induced: false, component: not-run-channel, disposition: fixed}
  - {id: C4, severity: Medium, aim: instrument, fix_induced: false, component: self-test, disposition: fixed}
  - {id: C5, severity: Medium, aim: instrument, fix_induced: false, component: prose, disposition: fixed}
  - {id: X1, severity: Blocking, aim: deliverable, fix_induced: false, component: locate-main, disposition: fixed}
  - {id: X2, severity: Blocking, aim: deliverable, fix_induced: false, component: locate-main, disposition: fixed}
  - {id: X3, severity: High, aim: instrument, fix_induced: false, component: self-test, disposition: fixed}
```

**Overlaps:** X1 = C1's failing input 3, where the gitdir has no `commondir`.

**Root cause, and the route: ACCRETE to FAIL CLOSED.** The launcher treated every state it could not read as the
state "not a worktree". In that state it fell through to the worktree's own copy, which is the one copy backlog #513
says is not trusted. The fold inverts the default. Once `.git` is a FILE, the launcher redirects to the main checkout
or reports NOT RUN, and nothing else is possible. It is NOT RUN when:

- the gitdir is missing or unreadable;
- `commondir` is missing and the gitdir is not a repository (it has no `objects/`);
- either path holds a newline;
- the common dir is not a `.git` directory;
- the main checkout has no such hook.

Files are read to EOF (`read -r -d ''`) and paths are resolved with `pwd -P && echo .`, so neither can truncate a
path in silence. Before the fix, the head launcher was run on four reproduced inputs (dangling, no-commondir,
unreadable and newline). All four ran the worktree's copy with rc 0. After the fix, all four are NOT RUN.

| Finding | Disposition | Fix and evidence |
|---|---|---|
| **C1** (BLOCKER). A stale or broken gitdir runs the worktree's copy. | FIXED | An unenterable gitdir is NOT RUN, and so is a gitdir with no `commondir` and no `objects/`. Cases: *C1 a worktree whose gitdir is gone (main renamed, worktree pruned): NOT RUN, its own copy NOT run*; *C1 a worktree whose gitdir cannot be read: NOT RUN, its own copy NOT run* (the gitdir is mode 0; a precondition row proves it really cannot be entered); and *C1 a worktree whose .git file cannot be read: NOT RUN, neither copy run*. Shell mutants c1a (missing-gitdir check → `false`, killed by DANG and UNREAD) and c1b (objects check → `false`, killed by NOCD). **Submodules keep their behaviour, proved:** mutant c1c (objects check → `:`, which NOT RUNs a submodule-style gitdir) is killed by the existing U3 submodule case. |
| **C2** (MINOR). A `.git` name does not prove its parent is the main checkout. | FIXED: the rule is stated and a case is added | Measured: in the symlink layout (`symmain/.git -> store/proj/.git`), `git worktree list` itself names `store/proj`, the common dir's parent, as the main worktree. It does the same for a `--separate-git-dir` main named `.git`. Nothing on disk tells these apart from a real main checkout. **The simplest rule that fails closed:** "main" is git's own answer (the resolved common dir's parent), and when that directory lacks the hook the result is NOT RUN. The rule is written in the launcher's comment under *WHICH CHECKOUT IS MAIN*. Case: *C2 a main checkout whose .git is a symlink: git's main (the common dir's parent) has no copy, so NOT RUN — neither the worktree's nor the symlink holder's copy*. Precondition row: *C2's world: git names the common dir's parent (the symlink target) as the main worktree*. Mutant c2 (a missing usage hook falls back to the worktree's copy) is killed by SYM. |
| **C3** (MINOR). A usage-pace NOT RUN signals on stderr only. | FIXED | `usage_not_run` matches `cannot()` in `usage-pace-run.sh`. It exits 0 and prints a fixed JSON line on stdout: `hookSpecificOutput`/`UserPromptSubmit`/`additionalContext` for `usage-pace-prompt.sh`, and `systemMessage` for every other usage hook. The reason goes to stderr. No new channel was added. The cases assert the exact stdout (`want_out`), and a row parses both lines (*C3 both NOT RUN JSON lines parse, under the keys their events read*). Mutants: c3a (stdout dropped, exit 1) is killed by U4 and U5; c3b (prompt sent through `systemMessage`) is killed by *X3 usage-pace-prompt.sh with no locatable main: NOT RUN, exit 0, its own JSON channel on stdout*. |
| **C4** (MINOR). The "commondir names a missing directory" case could not tell u4 from u5. | FIXED | Every NOT RUN case now asserts its OWN stderr reason (`want_err`) and its stdout. A mutant that reaches a different refusal therefore goes red. u4 and u5 are both now killed by U4 and by *U4 a worktree whose commondir names a missing directory: NOT RUN, its own copy NOT run*. u5 was re-anchored onto the `usage_not_run` call. |
| **C5** (MINOR). The docstring's case count was stale. | FIXED | It now says `# 132 cases`, verified by `check-selftest-counts.py --only check-run-hook.py`. |
| **X1** (BLOCKER). A missing `commondir` falls through to the worktree's hook. | FIXED | Same fix as C1. Case: *C1 a worktree whose gitdir has no commondir: NOT RUN, its own copy NOT run (r1 X1)*, a real `git worktree add` with `commondir` unlinked. Killed mutant: c1b. |
| **X2** (BLOCKER). A newline in a path truncates the gitdir. | FIXED | `.git` and `commondir` are read to EOF, and any path containing a newline is NOT RUN. Cases: *X2 a worktree of a main checkout whose path holds a newline: NOT RUN, its own copy NOT run* (a real main named `nlmain\nname`), and *X2 a commondir that holds a newline: NOT RUN, even though its first line names main's .git*. Mutants: c1d and c1e (first-line read; gitdir newline check off) are killed by NL; c1f and c1g (the same for `commondir`) are killed by NLCD. |
| **X3** (MAJOR). Only the synthetic `usage-pace-probe.sh` name was tested. | FIXED | `REAL_USAGE` is an independent literal of the four real hook names, and an identity row checks it against a glob of `.claude/hooks/usage-pace-*.sh` (*X3 REAL_USAGE names exactly the repository's usage-pace-*.sh hooks*). For each name there are two cases: *X3 \<name\> in a post-launcher worktree: MAIN's copy* and *X3 \<name\> with no locatable main: NOT RUN, …*. Codex's exact mutation is shell mutant r-\<name\> for each of the four names (`case $name in <n>) root=$dir;; esac` before `hook=`), and each is killed by its own real_ran case. |

**Manifest:** `scripts/mutations/check-run-hook.json` went from 21 to 33 entries, and the pin in
`scripts/mutations/expected_mutations.py` is 33. Thirteen entries were added and one was removed.

The first sweep on 34 entries returned `33 killed, 32 attributed, 1 survivor`, which exposed two problems:

- **The survivor.** The existing entry *U4's decoy beside the non-.git common dir has no usage hook* now survives.
  After C4, every NOT RUN case compares its own stderr reason, so u4 goes red without the decoy too: it reaches a
  different refusal. The second clause that kills u4 is `want_err`, which has its own entry. The decoy entry was
  removed and the decoy stays in the world.
- **The unattributed kill.** The C3 parse row called `json.loads` while the rows were being built. A broken constant
  therefore raised a traceback with no `[FAIL]` line. The row now turns a parse error into a red value.

The 13 new entries each remove one piece of the fold's test machinery:

- the dangling, no-commondir, unreadable-gitdir and unreadable-`.git` worlds;
- both newline worlds;
- the `want_err` and `want_out` comparisons;
- the REAL_USAGE plant and the real-name cases;
- the identity glob;
- C2's git precondition;
- the prompt JSON's parse.

Every new and existing anchor occurs exactly once in the file, and no two entries share one.

**Results on the fold tree:**

- `python3 scripts/check-run-hook.py --self-test`: `132/132 self-test cases passed`
- `python3 scripts/check-plan-code.py --mutate . --only scripts/check-run-hook.py --allow-long-local`: `OK — delivered scripts mutated: 1 file(s), 33 mutation(s), 33 killed, 33 attributed to the case each names, 0 survivor(s) — measured over ONLY scripts/check-run-hook.py — a DIAGNOSTIC slice, not the gate`

The sweep needs `--allow-long-local` because the run is estimated at over 13 minutes: 34 mutations at about 23 s each.

**Not thrashing:** no finding was caused by an earlier fold, because this is round 1.
