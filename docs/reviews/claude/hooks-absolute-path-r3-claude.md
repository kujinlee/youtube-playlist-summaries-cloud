# Round 3 — `hooks-absolute-path` — Claude half (mandate: REFUTE)

Tree reviewed: `19880062` (PR #409, branch `hooks-absolute-path`), `git diff origin/master...HEAD`.
I did not edit the checkout. Every experiment ran in a fresh `mktemp -d` copy under the session scratchpad: a
`git archive HEAD` snapshot (`r3c.*`), old/new worlds built from `merge-base(origin/master, HEAD)` and from `HEAD`
(`r3c-old.*`), and probe worlds that use the shipped launcher (`r3c-v.*`).

**The bet is LOST.** A linked worktree whose branch predates this PR has `.git` but no `run-hook.sh`, so the walk
skips it and runs MAIN's hooks. A pending plan gate in that worktree goes **2 → 0**. That is round 1's observation
again, through the launcher's marker.

## Baseline (executed)

- `python3 scripts/check-hook-commands.py --self-test` gives **36/36**. `python3 scripts/check-hook-commands.py` gives
  `ok — 13 hook command(s)`, rc 0.
- `python3 scripts/check-plan-code.py --mutate . --only scripts/check-hook-commands.py` was run in a full copy. The
  first run was **CANNOT RUN** because `node_modules/typescript` was missing. After I copied it in:
  `13 mutation(s), 13 killed, 13 attributed to the case each names, 0 survivor(s)`. The 2138 → 2151 total in
  `check-plan-code.py` matches.
- At each checkout root, in a real repo copy and in a linked worktree of it, `bash -x` on the launcher shows
  `exec bash <root>/.claude/hooks/check-schema-gates.sh`. That is the copy the old relative form names. From
  `scripts/` in each, it is the same root's copy, where the old form found nothing. So the claim holds **for
  checkouts that have the launcher**. F1 is the case where it does not.

## Findings

### F1 — High — `.claude/hooks/run-hook.sh:44` (the marker), contradicting `run-hook.sh:18-19`, the PR body, the backlog #223 row and the dashboard entry

**Defect.** The walk accepts a directory only if it has BOTH `.git` and `.claude/hooks/run-hook.sh`. A checkout of
any commit before this PR has `.git` and its own hooks, but no launcher. The walk passes it, finds no other match,
and falls back to `$CLAUDE_PROJECT_DIR`, which is the main checkout.

**When it happens.** A session started in the main checkout, after merge, does work in the worktree of a branch
that has not yet merged master. That is every open branch on the day this lands, and this repo works through
linked worktrees per slice. A worktree nested under `.claude/worktrees/` is affected the same way.

**Executed.**
- Setup: main = `HEAD` tree; branch `oldbranch` = merge-base tree.
- Worktrees: `$X/wt` and `$X/main/.claude/worktrees/nested-old`, each with `.claude/plan-gate-pending`.
- Payload: an implementation `Agent` payload.
- Commands compared: the old form, `bash .claude/hooks/block-implementation-before-plan-gate.sh`, and the shipped
  form, `bash "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/run-hook.sh block-implementation-before-plan-gate.sh`, with
  `CLAUDE_PROJECT_DIR=$X/main`.

| cwd | old relative form | new canonical form |
|---|---|---|
| `wt` (root) | **2** (blocked) | **0** (allowed) |
| `main/.claude/worktrees/nested-old` (root) | **2** | **0** |
| `nested-old/scripts` | 127 | 0 |
| `wt/scripts` | 127 | 0 |

`bash -x` confirms the choice: `root=$X/main` and `exec bash $X/main/.claude/hooks/block-implementation-before-plan-gate.sh`.

**Effect.** Every hook that locates state through `dirname "${BASH_SOURCE[0]}"` reads MAIN's state, not the
worktree's. That includes the plan gate, `block-idle-stop.sh` and `check-plan-gate.sh`, which writes the sentinel
into MAIN.

**What this contradicts.** The comment says "at any checkout root it picks exactly the copy `bash
.claude/hooks/<name>.sh` picked". At an old checkout's root it picks a different checkout's copy. This is also
round 2's XM3 again ("a missing X in the worktree ran MAIN's copy"), with X now the launcher instead of the hook.

**Fix.**
- Make the nearest `.git` (file or directory) the boundary, and never walk past it.
- Within that checkout, run `.claude/hooks/<name>` if it exists, whether or not the checkout has a launcher. That
  is exactly the old relative form at its root. Otherwise report NOT RUN.
- Use the project dir only when there is no `.git` ancestor.
- The cost, stated: a nested repo with no hooks (a vendored clone) gives NOT RUN, which is what the old form gave.
- Add a real-git case: a worktree at a commit that has `probe.sh` and no `run-hook.sh`, with the project dir naming
  main, must run the worktree's probe. Add a second case for that worktree nested inside main.

### F2 — Low — `.claude/hooks/run-hook.sh:46` (`dir=$(dirname "$dir")`)

**Defect.** When `dirname` fails, the walk stops silently and selection falls back to the project, which is another
checkout.

**Executed.** In `wt/sub`, I made 130 nested 10-character directories (a 1605-character physical path, past macOS
`PATH_MAX`). From the deepest one, the launcher printed `dirname: …: File name too long` and ran
**`T/main`**'s probe, not `T/wt`'s.

**Fix.** Replace the line with `dir=${dir%/*}; [ -n "$dir" ] || dir=/`, which uses no subprocess and no syscall.
A prototype with that change ran `T/wt`'s probe from the same directory, and the 36-case suite passed with it
(`self_test(launcher=<prototype>)` rc 0).

### F3 — Low — `.claude/hooks/run-hook.sh:42,46` (command substitution strips trailing newlines)

**Defect.** `$(pwd -P)` and `$(dirname …)` drop trailing newlines from a path.

**Executed.** Two sibling checkouts, `T/nl` and `T/nl\n` (the second name ends in a newline), each with a launcher
and a probe. From `T/nl\n/sub` the launcher ran **`T/nl`**'s probe: `dirname` returned `T/nl\n`, and the
substitution truncated it to the sibling.

**Severity.** Exotic, but it is a way to launch from a checkout other than the one containing the cwd.

**Fix.** Use `${dir%/*}` (as in F2), and read the cwd with a sentinel:
`dir=$(pwd -P && echo .) && dir=${dir%.} && dir=${dir%$'\n'}`. Both were in the F2 prototype.

### F4 — Low — `scripts/check-hook-commands.py:274` (a case passes for an ambient reason)

**Defect.** "⭐ main() over the shipped defect exits 1" calls `main([], root=root)` with the default `UNREGISTERED`.
Its exit 1 does not depend on the defect.

**Executed.**
- On the case's own output, `main` reports THREE findings: the relative command, `x.sh` registered by no command,
  and `UNREGISTERED lists check-memory-index-budget.sh, which does not exist — stale entry`.
- I then removed the defect: same world, compliant canonical settings, default `UNREGISTERED`. `main()` still
  returned **1**, with the stale-entry finding as its only line.
- Mutation 13 is still killed, because main ignoring `root` reads the compliant real repo and returns 0. But the
  case does not witness what its name says. The commit message says "mutation 13's named case now fails on its
  own", and that is true only of the mutation, not of the defect.

**Fix.** Pass `unregistered={}` and register `x.sh` correctly apart from the shape, so the relative command is the
only finding. Or assert on the specific message.

### F5 — Low — the hand mutations of the launcher: `scripts/check-hook-commands.py:43-46`, the commit message, the PR body, the backlog row and the dashboard

**Defect 1: the seven are not recorded.** The docstring says the launcher mutations are "recorded in the PR #409
round-1 and round-2 coordinator records". The r2 coordinator record lists none. The r1 record lists six, all for
the superseded git-asking design (for example "no common-dir check" and "git toplevel never consulted"). The PR
body names only two of the seven. So "7 launcher mutations by hand, each killed by its named case" cannot be
checked against anything.

**What I did instead.** I built 12 natural mutations of the current launcher and ran each through
`self_test(launcher=<copy>)` after importing the module. Control: 36/36.

| mutation | killed? | by |
|---|---|---|
| M1 always the project dir (r1 design) | yes | 5 cases, incl. the ⭐ worktree case |
| M2 the hook file is the marker (r2 defect) | yes | "a hook MISSING in the worktree is NOT RUN" |
| M3 no `.git` requirement | yes | "a hooks copy with no .git is not a checkout" |
| M4 arguments passed through | yes | "no argument after the hook name reaches the hook" |
| **M5 drop `*/*` from the refusal** | **NO — survives** | "a path-shaped hook name is refused" uses `../hooks/probe.sh`, which `.*` still refuses: a masking pair |
| M6 a missing hook exits 0 | yes | both NOT RUN cases |
| M7 a missing hook falls back to the project's copy | yes | "a hook MISSING in the worktree" |
| **M8 `pwd` instead of `pwd -P`** | **NO — survives** | no case uses a symlinked cwd |
| M9 the outermost match instead of the nearest | yes | the nested-checkout case |
| M10 `.git` must be a directory | yes | the 3 worktree cases |
| **M11 `:-.` default → `:-/nonexistent`** | **NO — survives** | "project dir UNSET … old relative behaviour holds" runs from a checkout root, so the walk answers before the default is read |
| **M12 deleted cwd → `.` instead of the project** | **NO — survives** | no case uses a deleted cwd |

M8 matters. I executed cwd = `main/link-to-wt`, a symlink into `wt/sub`: the shipped launcher runs `wt`'s hook. M8
would run main's, and nothing would go red. The "physical cwd" in the rule is therefore untested.

**Fix.**
- Record the seven by name in the r3 coordinator record.
- Add cases for: the name `sub/probe.sh` refused; a symlinked cwd into the worktree; a deleted cwd; the unset
  default from a directory the walk cannot answer for.
- Correct the docstring pointer.

### F6 — Low — prose: the PR title, `docs/dashboard-entries.md:17695-17696`, the PR body, the backlog #223 row

- **PR title.** "Hooks are registered at the project dir, and a guard refuses a relative hook path" describes round
  0. Hooks are now chosen from the cwd's checkout, and the guard is a one-shape allowlist.
- **Dashboard plain-language half.**
  - "they still use the copy of the project you are working in when you work in a side copy" is false for an
    old-branch side copy (F1).
  - "They now start from anywhere" is unqualified. With `CLAUDE_PROJECT_DIR` unset or `.`, the launcher command
    itself is not found from a subdirectory: executed from `wt/sub`, `bash: ./.claude/hooks/run-hook.sh: No such
    file or directory`. Round 2 asked for this qualification and it is still missing.
- **PR body and backlog row.** "at any checkout root it picks the copy the old form picked" is false under F1.
- **What is true.** 36 cases; 13 manifest mutations, all attributed; 2138 → 2151; "rounds 1 and 2 NOT CONVERGED".
  The live falsifier is correctly stated as still owed.

**Fix.** Retitle the PR, and qualify or correct those sentences after F1's fix.

## Attacks that held (executed)

- **cwd inside `.git/`** (`main/.git`, `main/.git/hooks`) and **inside a worktree's admin directory**
  (`main/.git/worktrees/wt`): the walk reaches `main`, the checkout that physically contains the cwd, and main's
  probe runs.
- **A stray `.git` file in a subdirectory with no launcher:** ignored, main runs.
- **An empty `.git` directory plus a planted `run-hook.sh` in a subdirectory:** the inner directory wins, and its
  missing hook gives NOT RUN (rc 1). That needs a planted launcher, and nothing tracked or habitually untracked in
  the repo provides one. Not a finding.
- **A symlinked cwd:** `main/link-to-wt` → `wt/sub` runs `wt`'s hook, which is correct physically. A cwd through a
  symlinked main root runs main's.
- **A deleted cwd** inside `wt`: `pwd -P` fails, the project's (main's) hook runs. The worktree's hooks are gone in
  that case, so this matches the bet's "no checkout contains the cwd" branch. Untested (F5 M12).
- **A path with spaces:** correct.
- **A 300,000-byte binary payload on stdin:** the hook received all 300,000 bytes. Zero arguments are forwarded.
- **A cwd outside every checkout** (`/tmp`, a non-git directory): the project's hook runs.
- **A relative `CLAUDE_PROJECT_DIR`** (`../main` from a non-git sibling): the launcher is found and main's hook
  runs. With `.` from a subdirectory the launcher is not found, which is the old limitation (F6).
- **A new checkout nested inside an old one:** the nearest new checkout wins. When the session's project is an old
  checkout, its settings use the relative form and the launcher is never involved. The harmful direction is old
  inside new, which is F1.
- **`GIT_CEILING_DIRECTORIES` and other `GIT_*` variables:** irrelevant, because no git process runs (the case is
  green, and I confirmed no `git` call in the launcher).

## Note, not a finding

`origin/master` has moved two commits past the merge base (PR #408, PR #407). PR #408 files backlog #359 about the
mutation total that conflicts, so expect to rebase the 2151 figure.

VERDICT: NOT CONVERGED
