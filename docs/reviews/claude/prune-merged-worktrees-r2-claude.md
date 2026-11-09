Reviewed head: e2a10f592443b28186c85ef7afa554baf23229bf

# Adversarial review, round 2 (Claude half): archive merged worktrees, never delete (PR #551, backlog #589)

Mandate: REFUTE the redesign. Method: throwaway repositories in the session scratchpad (bare origin, main clone,
worktrees under `main/.claude/worktrees/`, the self-test's own `_repo`/`_bins` fakes for `gh` and `lsof`), a
20 MB HFS+ disk image for the cross-device case, and real background processes for the `lsof` parse. Against
this repository only `--dry-run` and `--self-test` were run. `--self-test` at this head: 65/65. I did NOT run
the full `check-plan-code.py --mutate` sweep (27 mutations x ~12 s exceeds the 270 s per-call bound); I ran
my own 10 targeted mutations against a copy of the script instead (results under F5).

## What I tried to break and could not

- **Preservation by `git worktree move`.** In temp repos the archive kept, byte for byte: an untracked nested
  repository (its own `.git` and log intact), a stash entry made in the worktree (`refs/stash` is in the common
  dir), a `refs/worktree/*` ref, a `config.worktree` value (`extensions.worktreeConfig`), skip-worktree and
  assume-unchanged edits, ignored files and the worktree HEAD reflog (the last three are also self-test cases).
  `git worktree move <archive>/<name> .claude/worktrees/<name>` restored a working checkout with the stash still
  listed. A RELATIVE `node_modules -> ../../../node_modules` symlink dangles while archived and works again after
  the undo. That is no loss, and this repository's worktrees use ABSOLUTE links (measured: two live worktrees),
  which keep working.
- **Submodules / gitlinks.** `git worktree move` refuses both ("working trees containing submodules cannot be
  moved or removed", rc 128) and nothing moves. The docstring states this. See F6 for the recurring noise.
- **`mergedAt`.** `parse_time` requires a time zone and `now` is UTC-aware, so the 2 h comparison is
  zone-independent. An absent value is CANNOT RUN for the whole run, which is the fail-closed direction.
- **`st_dev` with no archive dir yet.** `dev_of` walks to the nearest existing ancestor (`~`). On this Mac `~`
  and the repo share a device, so the check passes as intended.
- **`lsof` with spaces / UTF-8 / a symlinked cwd.** lsof prints the resolved path, spaces and `é` verbatim, and
  the script `realpath`s both sides. Measured `lsof -d cwd -Fn` here: rc 0, 0.2 s. Real-repo `--dry-run`: rc 0,
  3.5 s, 7 worktrees, all KEPT with correct reasons (3 locked agent trees, 3 with a live cwd, 1 open PR).
- **Two runs at once** (two sessions starting together): no loss and no wrong move. See F7 for the report.
- **Other worktree walkers.** `check-stalled-work.py`, `gen-work-lines.plan_dirs` (and through it
  `goal-tree.py` and `check-banner-armed.py`) and `compaction-state.worktrees` all read `git worktree list`.
  They now see archive paths, but they saw the SAME registered set before this PR (nothing ever unregistered a
  worktree), so the archive adds no new noise or error. See F8 for what it locks in.
- **Branch reuse.** `git checkout <b>`, `git worktree add <p> <b>` and `git branch -d <b>` all refuse with
  "already used by worktree at '<archive path>'". That is stated in the docstring's BOUNDS, and the message names
  the archive path, so it can be discovered.

## Findings

### F1 — MEDIUM — the `lsof` guard cannot see how agents in this repository work, and a late writer after the move lands in the MAIN checkout

Rule 5's `lsof -d cwd` sees a process whose cwd is inside the worktree. Agents in this harness do not keep one:
their Bash cwd is reset between calls and they address worktrees by absolute path (the agent briefing says so).
So for a subagent working in a worktree the guard is blind, and the only real guard left is the 2 h rule
(`RECENT_S`). An agent that is still writing UNTRACKED files after its PR merged more than 2 h ago gets its
worktree moved under it. Untracked files do not block (rule 4). Examples are a review doc, a report, or a
follow-up on the same branch before its first commit.

What happens next was reproduced. After `git worktree move .claude/worktrees/st …`, an agent writing to
`.claude/worktrees/st/docs/r.md` recreates the directory (Write and `mkdir -p` both do that). Then
`git -C .claude/worktrees/st/docs rev-parse --show-toplevel --abbrev-ref HEAD` printed the MAIN checkout and
`master`: inside `.claude/worktrees/` git walks up to the main repo. In this repository that path is in
`.git/info/exclude` (`**/.claude/worktrees/`), so `git status` there shows nothing. The agent's work is now
split between the archive and an invisible stray directory, and any `git commit` it runs acts on the main
checkout's branch. Nothing is lost, but this is exactly the DISRUPTION the kept rules exist to prevent. The
docstring's bound names only "a process holding a file open there without its cwd inside", which understates it.

Fix options: (a) state the bound truthfully: in this harness the 2 h rule is the guard, `lsof` only catches
interactive shells and the session's own process. (b) Put a TOMBSTONE at the old path after a successful move: a
regular FILE `.claude/worktrees/<name>` whose content names the archive path. Then a late `mkdir -p`/Write fails
loudly ("Not a directory") instead of silently forking the work into the main checkout. The undo then becomes
`rm` + `move`, and `archive_target`/the collision rule must ignore tombstones.

### F2 — MEDIUM — a squash-merged branch whose remote branch is gone is KEPT forever, with a reason that says it has unpushed work

Rule 4's second half (`evaluate`: no `origin/<br>` → require `merge-base --is-ancestor HEAD origin/master`) can
never pass under squash merges, the house merge method. A squash never puts the branch's commits into
`origin/master`. Rule 2 has already established that HEAD is a merged PR's `headRefOid` or an ancestor of it, so
every one of HEAD's commits is on GitHub (in the PR's head). The check therefore adds no protection and only
false-keeps. Measured on this repository: of the last 100 merged PRs, 12 head branches are gone from origin and
11 have no local `refs/remotes/origin/<br>`. Every such worktree stays in `.claude/worktrees/` permanently, under
the reason "no origin branch, and HEAD is not in origin/master", which reads as unpushed work when there is
none. Reproduced in a temp repo (`sq`: HEAD == merged `headRefOid`, remote branch deleted and fetched with
`--prune` → KEPT). The self-test's `gone` case pins this false keep as correct. The first half has the same
false keep when the local tracking ref is stale (`origin/<br>` behind a `headRefOid` pushed from elsewhere).

Fix: when HEAD equals or is an ancestor of a merged `headRefOid`, the "unpushed" question is already answered.
Either drop the origin check for that case, or test reachability against the merged oid, not `origin/master`. The
`gone` case should then expect ARCHIVED, and a separate case should keep a HEAD that GitHub does not have.

### F3 — LOW — the cross-device reason is false: `git worktree move` never copies

The docstring (rule 6) and the KEPT reason say a cross-device move "would COPY, which is not atomic". Measured
with git 2.49 and a mounted disk image: `git worktree move` to another device fails with
`fatal: failed to move … : Cross-device link`, rc 128, and nothing moves. The guard is harmless (it turns a
FAILED into a KEPT with a reason), but the stated rationale is wrong. If the guard is kept it should say "git
cannot move across filesystems (EXDEV)". The mutation description in `scripts/mutations/prune-merged-worktrees.json`
("a copying, non-atomic move") repeats the error.

### F4 — LOW — a deadline kill between git's `rename` and its gitdir update is reported later with advice that destroys the admin dir

`git worktree move` renames the directory first, then rewrites `<common>/worktrees/<id>/gitdir`. A SIGKILL from
`Budget` between those two steps leaves the worktree at the archive path while git still records the old path,
so it is `prunable`. The current run reports it FAILED with both sides named, which is correct. On the NEXT run
`evaluate` sees `prunable`, finds the old directory missing, and prints "its directory is missing (`git worktree
prune` clears it)". Following that advice deletes the admin dir, and with it the archived worktree's index, HEAD
and reflog. The files survive, but they are now unregistered. The right advice is
`git worktree repair <archive path>`. The window is microseconds and needs the deadline to fire in it, hence LOW.
Since the log has the `archiving` line with the destination, the message could look the name up there.

### F5 — LOW — rules whose deletion leaves the self-test green

I ran each of these against a copy of the script; all SURVIVED (`--self-test` rc 0):

| Mutation | Rule it deletes |
|---|---|
| `if rc == 0 and os.path.isdir(dest) and not os.path.lexists(row.path)` → `if rc == 0` | the post-move verification |
| drop `return row` after the prunable reason | a prunable worktree is not evaluated further |
| drop the `tzinfo is None` refusal in `parse_time` | a zone-less `mergedAt` |
| `n <= ARCHIVE_WARN` → `n < ARCHIVE_WARN` | the warn boundary (fixture has 17, never 10/11) |
| drop the `GIT_ENV_DROP` loop in `run` | an inherited `GIT_DIR` redirects every git call |
| drop `stopped or` in the `prune` loop | after a CannotRun, later worktrees are still evaluated and MOVED |
| `print(lines[:HOOK_MAX_LINES])` → all lines in `main` | the hook's stated line cap |
| `return lines[:HOOK_MAX_LINES]` → `return lines` in `hook_lines` | the same, the inner copy |

The two cap mutations survive together, and individually, because no case produces more than 2 hook lines. The
`stopped or` survivor is masked: `_StopAfterMove` makes every LATER call raise too. A one-shot CannotRun
(one `git status` timing out) would let the loop go on moving after the run is already reporting CANNOT RUN.
Killed as expected: removing the `.claude/worktrees/` parent filter, and removing the `st_dev` check.

### F6 — LOW — a worktree git refuses to move is re-attempted and reported FAILED at every session start

A worktree with a submodule or gitlink passes every rule. `git worktree move` then refuses it (measured, rc 128),
it is FAILED (rc 1), and the hook prints `FAILED to archive …` on every SessionStart (startup, resume, clear,
compact) until someone acts. Nothing in the message says it will recur. Detecting it first (a gitlink in the
index: `git ls-files -s | grep ^160000`, or `<common>/worktrees/<id>/modules`) and KEEPING it with a reason would
make the report stable. The same recurrence applies to every other deterministic FAILED.

### F7 — LOW — two concurrent runs report FAILED for worktrees the other run archived

Two runs started together on 6 eligible worktrees. Every worktree ended in the archive, with no loss, but run 0
reported `ARCHIVED 2, FAILED 4` (rc 1) and run 1 `ARCHIVED 4, FAILED 2` (rc 1). Each FAILED row says "source …
is GONE, target … exists", which is true but reads as an alarm in the hook ("FAILED to archive 4"). Two sessions
starting within a few seconds is ordinary here. Fix: an exclusive `flock` on the log dir for the whole run (the
loser prints nothing or "another run is archiving"), or classify "source gone, target registered at the archive
path" as archived-by-peer.

### F8 — LOW / INFO — the registered set now grows without bound, and with it every walker's cost and the stale plans

Before this PR nothing unregistered worktrees either, so this is not a regression against master. It is a
regression against round 1's design, and the archive makes it permanent unless the owner acts on the >10 line.
Every archived worktree stays in `git worktree list`. So: `compaction-state.worktrees` runs one `git status` per
archived worktree inside the PreCompact hook's bound. `check-stalled-work.collect` walks every tip.
`gen-work-lines.plan_dirs` keeps reading each archived worktree's `.claude/plans/`, so the old plans stay on the
work page, and `check-banner-armed`'s documented "A REUSED SLUG IS NOT SEEN" bound is fed by plans that will
never go away. Two cheap options: these readers could skip worktrees under `~/.worktree-archive/`, or the
docstring could state the cost.

### F9 — LOW — the `lsof` match misses a worktree path holding a newline or other escaped byte

`lsof -Fn` printed a cwd named `nl<LF>x` as the literal `nl\nx` (measured), so `parse_lsof` + the prefix match
cannot match it. Worktree names here are generated and ASCII, so this is a bound to state, not a fix.

### F10 — LOW — the undo command is relative to the main checkout, and nothing says so

`undo_cmd` prints `git worktree move <archive>/<name> .claude/worktrees/<name>`. Run from inside another worktree
(a session whose project dir is a worktree), it nests the restored worktree inside THAT worktree. The script
knows `main`, so the log and report could print the absolute target.

## Verdict

No loss path found: the redesign removes round 1's data-loss class, and the preservation claims hold for every
case in the mandate. The two MEDIUMs are disruption and efficacy defects in the rules that remain. F1: the
stated cwd guard is blind to absolute-path agents, and a late writer silently forks into the main checkout. F2:
under squash merges, a branch whose remote is gone is never archived and is reported as unpushed. Both have
concrete fixes. The LOWs are statements to correct and mutation gaps to close.

VERDICT: NOT CONVERGED
