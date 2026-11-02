# Architecture review — hook launch path (backlog #364), 2026-10-26

Trigger: THRASHING (`docs/dev-process.md` Phase 6; `docs/review-method.md:127` Q5). PR #409 r2 and r3 were
each caused by the previous fold, all in the launch path (`decision-log.jsonl:66-68`).
Subject: origin/master `4aaa6ed7`. Harness: Claude Code **2.1.309** (`~/.local/share/claude/versions/2.1.309`).
Read-only; every experiment ran in `mktemp -d` (`$TMPDIR/arch364.eMmQ`). No ADR touches hooks, so none is re-litigated.

## Verdict in one line

**The frame was wrong, not the walk.** Every lost design had a *fallback to another checkout* when the cwd's
checkout "did not qualify": r1 always fell back, r2 fell back when git failed or the hook was missing, r3 fell
back when the marker was missing. Each new qualification created a new world that falls through to main.
**Candidate (a) removes the qualification**: the filesystem alone names the checkout (nearest `.git` above the
physical cwd), and the only fallback is "no checkout contains the cwd at all". Prototyped, it passes all 14
worlds, kills all 12 mutants (11 in the runner, plus 1 in a dedicated symlink world), and was verified **live in
the real harness**.

## 0. What the harness actually does (executed)

| Fact | Evidence |
|---|---|
| A hook is spawned with `cwd` = the session's current cwd, `shell:true` | binary: `Txe(to,[],{env:oo,cwd:Mo,shell:Ts,…})`, `Mo = NHr(Ao,b)` with `Ao = w` (current cwd); it is replaced only by `--project-config-root` (`fo = eo()` = `projectConfigRoot()`, set only by that CLI flag) |
| `CLAUDE_PROJECT_DIR` is set AFTER the inherited env, so an ambient value cannot override it | binary: `oo={…inherited…, …Ee, …, CLAUDE_PROJECT_DIR:Vt(wn)}` |
| **Live:** after `cd sub`, `bash .claude/hooks/x.sh` silently does not run; `bash "$CLAUDE_PROJECT_DIR"/…` does | `claude -p` in a temp repo: 3 Bash calls → anchored hook logged 3 times, relative hook 1 time (only the call before the `cd`) |
| A `cd` to a dir **outside** the session's working dirs does not persist (reset to the launch dir); a `cd` into `.claude/worktrees/w1` **does** persist | binary `kxr` (resets when `r!==originalCwd && !Ey(r,…)`); **live**: `cd <outside worktree>` → next call's hook ran at the launch dir; `cd .claude/worktrees/w1` → next call's hook ran at w1 |
| `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR=1` (documented env, settable in `settings.json` `env`) makes **every** `cd` revert after the call | **live**: with the flag, all 3 calls' relative hooks ran at the launch root |
| `EnterWorktree(path)` moves the session cwd/originalCwd to the worktree but **leaves `CLAUDE_PROJECT_DIR` = main** | **live**: after EnterWorktree, hook `pwd=…/w1`, `project=…/live` (main); relative form ran w1's copy, anchored form ran main's |
| A session **launched in a subdirectory** fires **no project hooks at all** | **live**: launched in `sub/`, neither the relative nor a pure-`echo` hook fired |
| No harness variable names "the checkout of the current cwd" | env names in the binary: only `CLAUDE_PROJECT_DIR`, `CLAUDE_PLUGIN_ROOT`, `CLAUDE_ENV_FILE`; hook stdin `cwd` = the same spawn cwd, so it adds nothing over `pwd` |

This repo's worktrees live in the session scratchpad, outside the project (`git worktree list` on main: 20+
`…/scratchpad/wt-*`), and subagents `cd` into them. So r1's world (project dir = main, cwd = a linked worktree)
is the **primary** workflow, not an edge case.

## 1. The requirement, world by world

"Today" = the current relative form `bash .claude/hooks/<name>.sh` (`.claude/settings.json:10` and 12 siblings).
Required = what #364 (`docs/backlog.md:346`) and r1–r3 ask for.

| # | World | Source | Today | Required |
|---|---|---|---|---|
| W1 | main, subdirectory | #223 | 127, silent | main's hook runs |
| W2 | linked worktree root, project dir = main | r1 XH1 | worktree's hook (gate 2) | worktree's hook |
| W3 | linked worktree subdirectory, project dir = main | r1 | 127 | worktree's hook |
| W4 | pre-launcher worktree (outside main), root and subdirectory | r3 CH1 | 2 at root / 127 below | its OWN hook (gate 2) |
| W5 | pre-launcher worktree nested under `main/.claude/worktrees/` | r3 CH1 | same as W4 | its own hook |
| W6 | hook missing in the cwd's checkout | r2 XM3 | 127 | **NOT RUN**, never main's copy |
| W7 | `GIT_CEILING_DIRECTORIES`, `GIT_DIR`/`GIT_WORK_TREE`, `PWD` set | r2 XH1 | n/a | no effect on the choice |
| W8 | submodule / nested repo with its own hooks, at root | r2 XM2 | submodule's hook | submodule's hook |
| W9 | nested repo with NO hooks | r3 fix note | 127 | NOT RUN (same as today) |
| W10 | cwd outside any repo | r2 | 127 | the project dir's hook (the only checkout in play) |
| W11 | symlinked cwd; symlink inside main pointing INTO a worktree | r2, r3 M8 | — | the PHYSICAL checkout |
| W12 | physical path > 1024 chars | r3 F2 | — | the containing checkout, not main |
| W13 | path with trailing newline (sibling `nl` vs `nl\n`) | r3 F3 | — | `nl\n` |
| W14 | project dir unset / empty | r2, r3 M11 | 0 at root | no worse than today |
| W15 | session launched in a subdirectory | live, this review | no hooks load | **out of reach of any settings design** |

## 2. Is the frame wrong? The options

| Option | What it is | Satisfies | Fails | Cost |
|---|---|---|---|---|
| r1 | `bash "$CLAUDE_PROJECT_DIR"/.claude/hooks/x.sh` | W1, W10 | W2–W5, W8, W11 (main's hook, gate **2→0**; executed, table below) | trivial |
| r2 | launcher asks git (`--git-common-dir`) | W1–W3 | W7 (ceiling → main), W6 (main's copy), W8 | 2–3 git forks/hook, ~+40 ms (r2 Codex) |
| r3 | walk to `.git` **+ launcher marker** | W1, W3 (new) | W4, W5 (marker absent → main) | — |
| **(a)** | walk to nearest `.git` (file or dir), **no marker**; missing hook → NOT RUN; no `.git` → project dir | **W1–W14** (executed, 14 worlds) | W15 (no design can) | one 25-line launcher, no fork |
| (b) | hooks location-independent: code from the project dir, state from the cwd's checkout | W1, W3 state | a branch's own hook CODE never runs in its worktree (W2/W4 regress from today); needs 10 hook edits (`block-idle-stop.sh:50`, `block-implementation-before-plan-gate.sh:27`, `check-plan-gate.sh:30`, `enforce-handoff-path.sh:37`, `enforce-selection-card.sh:37`, `regen-backlog-page.sh:25`, `regen-dashboard.sh:22`, `regen-features-page.sh:29`, `regen-goals-page.sh:22`, `surface-recall.sh:41`), so it is one rule written in ten places | high |
| (c) | harness: `env.CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR=1`, relative form unchanged, worktrees entered with `EnterWorktree(path)` | W1 (live) and W2/W3 **only through EnterWorktree** (live) | manual `cd wt && …` (today's practice) runs main's hooks; per the EnterWorktree tool contract, a subagent whose cwd is pinned can switch only to `.claude/worktrees/`, not to scratchpad worktrees; changes every agent's `cd` semantics | **a workflow change**, so it is not a technical choice |
| (d) | accept the limit; make failure LOUD (e.g. `[ -f … ] \|\| exit 2`) | none (it reports, it doesn't fix) | a `cd scripts` blocks every gated tool call, and on `Stop` exit 2 forces the session to continue | cheap; acceptable only as the NOT-RUN branch *inside* (a) |
| (e) | inline the walk in every `command` string (no launcher file) | same as (a) | 13 copies of a 10-line shell program in JSON | guard can pin it, but it is unreadable |

Why (a) is "the old relative form extended": at any checkout root it picks exactly the file the relative form
picks (W2, W4, W5, W8 roots), and below a root it picks the file the relative form *would* have picked from that
root. It adds nothing else.

## 3. Prototype and results (executed)

The prototype is `$TMPDIR/arch364.eMmQ/launcher.orig`: 25 lines of bash 3.2, no git process. It reads only
`pwd -P` (read through a sentinel, so trailing newlines survive) and `${CLAUDE_PROJECT_DIR}` (used only when no
`.git` exists above the cwd). It walks with `${dir%/*}`, requires exactly one argument, refuses `''`, `*/*` and
`.*`, and runs `exec bash "$root/.claude/hooks/$name"`. If the hook is missing it exits 1 with
`NOT RUN <name> — <root> has no .claude/hooks/<name> (no other checkout's copy is used)`.

The probe hook reads its sentinel through `REPO_ROOT` from `BASH_SOURCE`, the same derivation as
`block-implementation-before-plan-gate.sh:27-28`. Every worktree is armed and main is not. Registered command:
`bash "$CLAUDE_PROJECT_DIR"/.claude/hooks/run-hook.sh gate.sh`, run as `/bin/sh -c` with `CLAUDE_PROJECT_DIR=main`.

| World | Today (relative) | r1 (project dir) | **(a)** |
|---|---|---|---|
| main/scripts, main/sub/deep | 127 | 0 main | **0 main** |
| wt root (pre-launcher) | 2 wt | **0 main** | **2 wt** |
| wt/scripts | 127 | 0 main | **2 wt** |
| nested-old root / scripts | 2 / 127 | 0 main | **2 nested** |
| wtnew/scripts (post-launcher) | 127 | 0 main | **2 wtnew** |
| wtmiss/scripts (hook deleted, armed) | 127 | 0 main | **1 NOT RUN** |
| wt/scripts + `GIT_CEILING_DIRECTORIES=wt` | 127 | 0 main | **2 wt** |
| wt/scripts + `GIT_DIR=main/.git GIT_WORK_TREE=main` | 127 | 0 main | **2 wt** |
| wt/scripts + `PWD=main` | 127 | 0 main | **2 wt** |
| submodule `vend` root (own hook, armed) | 2 vend | 0 main | **2 vend** |
| outside any repo | 127 | 0 main | **0 main** |
| symlinked cwd → wt/scripts | 127 | 0 main | **2 wt** |
| symlink *inside main* → wt/scripts | — | — | **2 wt** (logical walk would pick main) |
| `main/.git` (admin dir) | 127 | 0 main | 0 main |
| 1,511-char physical path under wt | — | — | **2 wt** |
| `nl\n/sub` | — | — | launcher root = `nl\n` ✅ (`bash -x`); see limit L3 |
| project dir unset, wt/scripts | 127 | 127 | 127 (`${CLAUDE_PROJECT_DIR:-.}` in the command restores today's root behaviour) |

**Live in the real harness** (`claude -p`, temp repo; worktree `w1` on a branch that has **no** launcher):
`cd w1/sub && pwd` → the next two Bash calls were **blocked by w1's gate** (`ran=…/w1`, `blocked by …/w1`), with
`CLAUDE_PROJECT_DIR` = main. This is #364's falsifier in its worktree form. The literal falsifier is a `git push`
to master refused from `scripts/` of this repo; that was **not executed** here, because I made no edit in any
checkout. **UNVERIFIED** until the implementer runs it.

**Mutation table** (`$TMPDIR/arch364.eMmQ/worlds.sh`, 13 worlds, control ALL PASS before and after):

| Mutant (the design it reverts to) | Killed by |
|---|---|
| m1 always the project dir (r1) | W2–W7, W11 |
| m2 launcher marker required (r3) | W2, W4, W5, W7 |
| m3 missing hook → project's copy (r2 XM3) | W6 |
| m3b hook file as the walk's marker (r2) | W6 |
| m4 outermost `.git`, not nearest | nested-old, submodule |
| m5 `.git` must be a directory | every linked worktree (`.git` is a file) |
| m6 `pwd` not `pwd -P` | **only** the symlink-inside-main world (the plain symlink world passes for an ambient reason: the logical path names the same checkout) |
| m7 `dirname` not `${dir%/*}` (r3 F2) | the long-path world (→ main) |
| m8 NOT RUN exits 0 | W6 |
| m9 ask git first (r2) | `GIT_DIR` world |
| m10 no-`.git` fallback removed | outside-repo world |

## 4. Recommendation

**Adopt (a).** Register every hook as
`bash "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/run-hook.sh <name>.sh`. That is a one-line change to
`CANONICAL` (`scripts/check-hook-commands.py:50`), plus `run-hook.sh` in a launcher exemption beside
`UNREGISTERED` (`:54`). The launcher lives only in the project dir's checkout. That is the same checkout whose
`settings.json` registered it, so the two cannot disagree.

**Test worlds it must ship with.** Use real `git worktree add` and real `git submodule add`, not mocked `.git`
files: W1–W14 as tabled. That includes the pre-launcher worktree both outside and nested, the hook-missing world,
all three env worlds, and the **symlink-inside-main** world (the only one that kills m6).

- Build the long-path world with `os.makedirs` and `os.chdir` from Python, not a bash `cd` loop. Here each run of
  that world cost about 30 s in bash 3.2.
- Each case asserts **both** the exit code and *which file ran* (`BASH_SOURCE` from a probe hook), not the exit
  code alone. r3 F4 is the precedent for a case passing on exit code alone.

**Mutation classes that must be killed** (manifest entries in `scripts/mutations/`): m1–m10 above, plus three more.

- The name refusal, with **one case per refused shape** (`../x.sh`, `a/b.sh`, `.x.sh`, empty). r3 M5 survived
  because `../` masked `*/*`.
- "extra arguments forwarded".
- "stdin not forwarded". `exec bash` forwards stdin; assert that the payload reaches the hook.

**What it does NOT handle, stated:**

| Limit | Status |
|---|---|
| L1 Session launched in a subdirectory: the harness loads no project hooks at all (live) | out of reach of any `settings.json` design |
| L2 The launcher's own code always comes from the project dir. A branch that edits `run-hook.sh` is not exercised in its worktree until merged; its *hooks* are | accepted; the launcher is the one rule kept in one place |
| L3 The hooks' own `REPO_ROOT="$(cd "$(dirname …)/../.." && pwd)"` (e.g. `block-implementation-before-plan-gate.sh:27`) strips trailing newlines. In the `nl\n` world the launcher picked the right file, but the hook read sibling `nl`'s state | pre-existing, exotic, in ten hooks. File it, don't fold it |
| L4 A stray `.git` between the cwd and the checkout root (a fixture repo or vendored clone) → NOT RUN | same as today's relative form at that root |
| L5 NOT RUN exits **1**: visible in the transcript but non-blocking, the same severity as today's 127, now with a message that names the cause | see the decision line |
| L6 The hooks' internal `git` calls still follow the cwd and the `GIT_*` env (`block-default-branch-push.sh:172`, `suggest-explainer.sh:34`) | not a launch-path property; out of scope |
| L7 Windows/PowerShell shells | not considered |

**Why not (c), even though it is the only harness-native fix.** It solves W1 with one `env` line, and that was
verified live. But it fixes worktrees only if every worktree is entered with `EnterWorktree`. Today's practice is
scratchpad worktrees that subagents `cd` into, and (c) would silently move all of that work onto main's hooks:
r1's regression, workflow-wide. Choosing it means changing how the owner works, so it is not the implementer's
choice. It stays recorded here as the alternative if the owner ever moves worktrees under `.claude/worktrees/`.

## Decision needed?

**No.** (a) is a technical choice that the process lets the implementer make. It preserves today's behaviour at
every checkout root and changes nothing else.

Two optional owner calls, neither blocking:

- whether NOT RUN should **fail closed** (exit 2) instead of exit 1. That is a policy tightening, and on `Stop` it
  would force the session to continue;
- whether to adopt the (c) workflow instead.
