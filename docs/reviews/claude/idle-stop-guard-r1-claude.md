Reviewed head: 175d82c6ec66f81fb2d3e663bfe11530d83ce091

# idle-stop-guard — round 1, Claude half

Subject: branch `idle-stop-guard`, commit 175d82c6 (`git diff origin/master...HEAD`), worktree `.claude/worktrees/isg`.
Mandate: REFUTE that the Stop hook blocks an idle stop and lets a legitimate stop through.

## Gates run (against 175d82c6)

- `python3 scripts/check-idle-stop.py --self-test` → `47/47 self-test cases passed`
- `python3 scripts/check-plan-code.py --mutate . --only scripts/check-idle-stop.py` → `OK — delivered scripts mutated: 1 file(s), 48 mutation(s), 48 killed, 48 attributed to the case each names, 0 survivor(s) — measured over ONLY scripts/check-idle-stop.py — a DIAGNOSTIC slice, not the gate` (24.5 s)

## What holds

- The replays are faithful. I pulled the real turn ends from this session's transcript (`b387c8e6…jsonl`):
  10:24:18Z, 10:26:11Z and 10:29:12Z (02:24, 02:26 and 02:29 PST). Their closing paragraphs match the fixtures
  `T0224`/`T0226`/`T0229` word for word, and `asks_owner` is False on each full real text. `T0224` is shortened,
  but the paragraph the exception reads is the real one.
- The replays reach BLOCK through `decide`, and through `main()` with real files (`drive(payload(T0224))` → rc 2).
  `.claude/hooks/check-idle-stop.sh` maps 0→0, 2→2 and anything else→1. `run-hook.sh` `exec`s it, so the exit
  code reaches the harness.
- The schema of (a) is real. Harness 2.1.323 builds `background_tasks` in `e9n(taskRegistry.all())` as
  `{id, type, status, description, …}`.
- Wedge and loop are bounded: `stop_hook_active` allows the second stop. A crash or NOT CHECKED gives exit 1, and
  the hook times out after 10 s while `gh` is bounded to 3 s.

## Findings

### MAJOR-1 — The question exception is a prose escape, and the house-mandated closing table opens it most often
`scripts/check-idle-stop.py:83` (`QUESTION`), `:90-95` (`asks_owner`), `:243`.

Every one of these returns `asks_owner == True`, and so ALLOW with nothing running (I ran each one):
- `"Merged #595.\n\n| CHECK | RESULT |\n|---|---|\n| #657 started? | ✅ yes |"`. This is the house closing
  table with its CHECK cell phrased as a question, which is a common shape. It is also exactly the lie the guard
  exists to catch: a claim that the work started.
- `"Now starting backlog #657. Why now? The wake is too far."`: a rhetorical question.
- `"Now starting backlog #657 (see \`check?\` mode)."`: a `?` inside a code span.
- `"Now starting #657.\n\n<!-- ? -->"`: an invisible comment.
- `"Starting #657 now — OK?"`: the original 02:29 turn with three characters added.

Measured over the last 30 main-session transcripts: 2920 turn ends, of which 38 pass `asks_owner`. In a seeded
sample of 15 of those 38, **8 are CHECK/RESULT table cells** (for example `| Considered before? | Yes: … |`) and not
questions to the owner. So in roughly half the cases where the exception fires, it fires on a report rather than a
question. The block message (`:271-273`) also tells the model "ask the owner a question and end on it", which
teaches the rewording that backlog #48 rejected. This is the same "satisfiable by rewording" hole, moved from
"is work starting?" to "does it end in `?`".

The docstring (`:38-40`) already accepts that a reply to the owner is blocked once and costs one continuation. The
prose exception therefore saves at most one continuation and opens a permanent escape.

Suggested fix: keep only the AskUserQuestion branch (`last_tool_asked`) and drop the `?` scan. Failing that, at
least skip table rows (lines that start with `|`), code spans and HTML comments, and add a case for the
closing-table input above.

### MAJOR-2 — Signal (b) is any file write, including `git worktree add`, the natural first step of "starting #657"
`scripts/check-idle-stop.py:164-191`.

Failing input: the orchestrator runs `git worktree add .claude/worktrees/b657 -b b657 origin/master`, writes "Now
starting backlog #657.", spawns nothing, and stops. Checkout gives every file a fresh mtime, so `_recent` is True,
`moved == ["b657"]`, and the stop is ALLOWED for the next 10 minutes. That is the 02:29 failure with one setup
command in front of it.

Measured just now: the `b657` and `isg` worktrees each have about 5,360 files changed in the last 6 h, about 4,340
of them under `docs/`, which is checkout, not building.

Other writers that are not a working builder and also open (b):
- merging master into a PR worktree before merge (the house rule);
- `python3 scripts/…` writing `scripts/__pycache__/*.pyc`, which `SKIP_DIRS` does not skip (27 and 21 `.pyc` files
  in the two worktrees);
- a reviewer filing a review file;
- the guard's own sibling hooks, when a session runs in a worktree.

The docstring states only the "builder finished less than 10 min ago" bound (`:43-45`). It does not state that a
non-builder write counts.

Suggested fix: at minimum ignore files that are no newer than the worktree's `.git` file (its creation time), and
skip `__pycache__`. Better, take the watchdog fingerprint the TODO names, so that "moving" means a change since the
previous observation.

### MAJOR-3 (needs one capture to confirm or dismiss) — Idle in-process teammates may read as running tasks
`scripts/check-idle-stop.py:155-161`, `TERMINAL` at `:79`.

What I read in harness 2.1.323:
- `e9n` emits `in_process_teammate` entries.
- A teammate that finishes its turn is updated to `{...o, isIdle: !0, evictAfter: Date.now()+X0}` with `status`
  left at `"running"`. Only failure sets `status: "failed"`.
- The payload carries `status` but not `isIdle`, so `running_tasks` cannot tell an idle teammate from a working one.

The orchestrator runs in team mode: this review is itself an in-process teammate. If an idle teammate stays in
`taskRegistry` with `status: "running"`, (a) ALLOWs every stop while one exists. That is the orchestrator's
ordinary state after a review or build round reports back.

A constant `X0=30000` sits next to that code, which suggests eviction after 30 s and would make the window small.
I did not confirm that eviction removes the entry from `taskRegistry.all()`.

The docstring's measurement (`:27-28`) used `claude -p` with one shell task, so it does not cover the mode the
guard runs in.

FAILS IF: a Stop payload captured in a team session, more than 30 s after a teammate goes idle, still lists that
teammate with `status: "running"`. If so, drop `in_process_teammate` entries from (a) (`(b)` already observes
builders), or treat them as running only while (b) shows movement.

### MINOR-4 — Any other Stop hook's block disables this guard for the continuation
`scripts/check-idle-stop.py:235-236`.

`block-idle-stop.sh` (the plan gate) runs on the same Stop event. When it blocks, the next stop arrives with
`stop_hook_active: true`, and this guard skips it, even though the continuation is the first time this guard would
judge the turn. Separately, a model that repeats the 02:29 behaviour on its one continuation is let through. That is
inherent to a loop guard, but the docstring states it only for "a reply to a question" (`:38-40`). It should be
stated as a general bound.

### MINOR-5 — A case's name claims an unreadable directory, but its input is "no main checkout"
`scripts/check-idle-stop.py:441`. The case "an unreadable worktrees directory → NOT CHECKED" passes `main=None`. It
never reaches `except OSError: return None` in `moved_worktrees` (`:170-171`). Its mutation
(`check-idle-stop.json`, "(b) an unreadable worktrees dir is read as none") mutates `if main else None` instead.
The mutant `except OSError: return []` (fail toward BLOCK on a permission error) is unmanifested and would survive.
Suggested fix: build a directory with mode 000 (or patch `os.listdir` to raise `PermissionError`), and add that
mutant.

### MINOR-6 — A stuck pending check on any open PR turns (c) off permanently
`scripts/check-idle-stop.py:205-226`, `PENDING_STATE` at `:81`. A required status that never reports stays
`EXPECTED` forever: a path-filtered workflow, or a check on a stale draft opened "at slice start". So does a
workflow parked in `WAITING` for approval. Either one makes every idle stop ALLOWED for as long as the PR is open.
`:46` states the bound "any open PR", but not that it can be permanent. Consider ignoring PRs whose `updatedAt` is
older than some hours, or checks older than a ceiling.

## Answers to the brief's questions

- **A stray `?` counted as a question?** Yes: MAJOR-1.
- **A recent mtime from an unrelated write?** Yes: MAJOR-2.
- **A finished task?** The `"completed"`/`"Killed"` statuses are handled. An idle teammate is not; see MAJOR-3.
- **gh failure / error paths?** NOT CHECKED gives exit 1 (allowed, said). A crash also gives 1. Never 2.
  Fails open loudly, by design.
- **Owner asked, nothing to launch?** Blocked once, then allowed by `stop_hook_active`. A cost, not a wedge.
- **All work merged?** Blocked once, same as above.
- **Malformed payload?** Exit 1, NOT CHECKED (case at `:505`).
- **Does each case go red when what its name claims is flipped?** Yes for every case except MINOR-5. The 48
  mutations each die on the case they name.

VERDICT: NOT CONVERGED
