# begin-plan-worktree — round 1, Claude half

Subject: `git diff origin/master...HEAD` at `80cd4e39` (branch `begin-plan-worktree`, PR #406).
Mandate: refute. Every experiment ran on a copy in a `mktemp -d` directory: a fresh repo holding a copy
of `scripts/`, a real linked worktree `linked`, and git 2.49.0 on macOS.

## What held (executed)

- `python3 scripts/begin-plan.py --self-test` in this linked worktree: **131/131 passed**.
  `check-plan-code.py --self-test` 239/239; `check-banner-armed.py --self-test` 236/236. That last one
  is the only other script that runs `begin-plan.py` without `--self-test` (TE5 runs `--finish` on a copy
  staged in a TemporaryDirectory). It passes because that temp dir is not inside a git repo.
- Main checkout `--status` gives rc 0. Linked `--status` gives rc 1 and nothing is written to the
  linked `.claude/`. A symlinked path to the worktree is still refused (ROOT is resolved).
- A submodule used as the main checkout is not refused (rc 0): its `--git-dir` equals its
  `--git-common-dir`.
- I applied each of the three new mutations to a copy. Each turns red through the case it names:
  rc 1, and the expected case is in the FAIL lines. Under mutation 1 (`if False:`) the copy's own
  `.claude/` stayed empty, so the redirection keeps an unrefused arm out of real state.
- Moving the `global` up is safe. A name assigned before a `global` statement is a SyntaxError, so no
  earlier local use could exist for the move to capture.

## Findings

### M1 — Medium — the copy-paste command in the refusal is unquoted, and pasting it runs a shell pipeline
`scripts/begin-plan.py:2078`, `{' '.join(argv)}`. Executed from the linked copy:
`begin-plan.py demo "one|doing x|why y" "two"` prints
`python3 …/main/scripts/begin-plan.py demo one|doing x|why y two`. Every step argument has the form
`title|doing|why`, so the command printed for the main use case, arming, can never be pasted as it
stands. Pasting it pipes `begin-plan.py demo one` into a command named `doing`. The PR body calls it
"the exact command to run", and it is not. Fix: `shlex.join(argv)`. Also add a case that round-trips
the printed command through `shlex.split` back to `argv`.

### M2 — Medium — "every state command is refused" is tested only for the slug arm; `--plan`, which also arms, has no witness
`scripts/begin-plan.py:2072` (the gate) against the single `main([...])` case at `:1031`. Executed: I
changed the gate to
`if _main_root is not None and a.slug and not (a.status or a.banner or a.finish or a.resume or a.pause or a.tick):`.
That exempts `--plan PATH`, the second way to arm and so the exact defect backlog #301 records, plus
every other state command. With that change the suite still reports **131/131 passed**. The PR body
and the dashboard both claim "refuses EVERY state command … before reading or writing any state". The
code does that today (the gate sits above all dispatch), but nothing tests it beyond the slug arm.
Fix: loop the linked-worktree `main()` case over `--plan <p>`, `--tick`, `--status`, `--finish`,
`--pause x` and `--resume`, and assert REFUSED and that no state file was written for each.

### M3 — Medium — when git cannot answer, a linked worktree arms silently and prints `armed:`, which is the #301 symptom
`scripts/begin-plan.py:2040-2045` returns None on any error, and the third new case (`:1027`)
writes that in as intended behaviour. Executed from the linked copy:
- `PATH=/nonexistent python3 linked/scripts/begin-plan.py demo one two` printed
  `armed: .claude/executing-plan -> .claude/plans/demo.md (2 steps)` and wrote `linked/.claude/executing-plan`.
- Main checkout moved (`mv main main-moved`): the worktree's `git status` reports
  `fatal: not a git repository`, and `begin-plan.py --status` returns rc 0 with no refusal.
- `GIT_DIR=<main>/.git` exported: rc 0, not refused.

None of these is common, and failing closed on a missing git would block every plan. But the project
rule says "cannot run is a FAILURE, never a pass", and here the fallback emits no warning. A worktree
is easy to recognise without git: `ROOT/.git` is a *file* containing `gitdir: …/worktrees/<name>`
(a submodule's file says `…/modules/…` instead). Suggested: when rev-parse fails, use that check, or
at least print a warning to stderr saying that whether this is a linked worktree was NOT CHECKED.

### L1 — Low — on git older than 2.31, the main checkout is refused, which would block every plan
`scripts/begin-plan.py:2038` and `:2042`. `git rev-parse` echoes a flag it does not recognise as an
output line. Executed on 2.49 with an invented flag: `git rev-parse --path-formatX=absolute --git-dir --git-common-dir`
prints `--path-formatX=absolute`, `.git`, `.git`, with rc 0. I fed that output shape, with
`--path-format=absolute`, to `linked_worktree_main` through `run=`. On the main checkout it returned
the main path, so the main checkout would be refused. *Unverified:* I did not run a real git 2.30. That
pre-2.31 git echoes this particular option is an inference from the behaviour measured on 2.49. Cheap
guard: require exactly two lines and reject any line starting with `-`. Alternatively use
`--absolute-git-dir` (git 2.13+) and resolve `--git-common-dir` against `root`.

### L2 — Low — the stated reason for refusing rather than resolving is not true of the fix that shipped
The backlog #301 tick, the dashboard `<!--tech-->` block and the PR body all say resolution was
rejected because "ROOT also feeds `current_branch(ROOT)`, so the sentinel would have recorded the main
checkout's branch, not the worktree's". The refusal sends the user to run
`python3 <main>/scripts/begin-plan.py …`. That copy's ROOT is the main checkout, so `_arm` at
`:441-443` records `pp.current_branch(<main>)`, the same branch the rationale objects to. Refusal
gives the same sentinel as resolution. The real argument for refusing is different: it surfaces the
problem and runs the main checkout's version of the script. The written argument should say that.

### L3 — Low — in a bare-repo-plus-worktrees layout, every checkout is refused and pointed at a path that does not exist
Executed: `git clone --bare main bare.git; git -C bare.git worktree add bwt`. Then
`bwt/scripts/begin-plan.py --status` is refused and the suggested command is
`python3 <T>/scripts/begin-plan.py`, the parent of `bare.git`, where there is no `scripts/`. Nobody
uses this layout in this repo today. The same `common.parent` guess is also wrong for a linked
worktree of a submodule (`…/.git/modules`). This affects only the message, not the safety.

### N1 — Note — the dashboard's mutation count is from before the merge
`docs/dashboard-entries.md` says "3 mutations (2105 -> 2108)". After the master merge, the code and
the PR body say 2115 -> 2118. It was true when written, but it is stale in the tree under review.

## Verdict

The gate works for the shape it targets, and its mutations are real. Two problems remain: the
refusal's own remedy cannot be pasted as printed (M1), and the claim "every state command" is
unwitnessed for the second arm path, `--plan` (M2). Both have small fixes.

VERDICT: NOT CONVERGED
