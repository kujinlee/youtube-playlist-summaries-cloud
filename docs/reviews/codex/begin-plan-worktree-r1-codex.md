<!-- codex-review: model=gpt-6.1-sol -->

1. **HIGH — Git <2.31 blocks legitimate main-checkout runs.** `scripts/begin-plan.py:2038–2046`  
   Built and executed Git **2.30.9** in the temporary copy. `rev-parse` exits **0** and prints:
   ```
   --path-format=absolute
   .git
   .git
   ```
   The helper interprets the option as `git_dir`, compares it with `.git`, and falsely detects a linked worktree. Main-checkout `--status` exits **1**; every state command hits the same refusal. Handle older Git without interpreting unknown-option output as paths.

2. **HIGH — Ambient Git variables bypass refusal or falsely block the main checkout.** `scripts/begin-plan.py:2038`  
   Executed the linked copy with `GIT_DIR=<main>/.git GIT_WORK_TREE=<main>`:
   ```
   begin-plan.py env-bypass one
   rc=0
   armed: .claude/executing-plan -> .claude/plans/env-bypass.md
   ```
   The sentinel existed **inside the linked checkout**, reproducing #301’s failure. Conversely, pointing those variables at the linked worktree made the legitimate main checkout refuse `--status`. `git -C ROOT` does not override repository-selection environment variables; detection must inspect ROOT independently.

3. **MEDIUM — Moving the main checkout makes the guard fail open.** `scripts/begin-plan.py:2040–2044`  
   Created a real linked worktree, renamed its main checkout without repairing worktree metadata, then executed:
   ```
   begin-plan.py moved-bypass one
   rc=0
   armed: .claude/executing-plan -> .claude/plans/moved-bypass.md
   ```
   The linked sentinel was written. Failed Git discovery returns the same `None` as a verified main checkout. Distinguish an ordinary staged copy without Git metadata from a checkout whose `.git` indirection is broken. The blanket refusal claims in backlog #301 and the PR body are therefore false.

4. **MEDIUM — The “exact command” changes arguments when executed.** `scripts/begin-plan.py:2078`  
   Requested `--pause "waiting on CI"` from a linked checkout. The suggestion was:
   ```
   python3 <main>/scripts/begin-plan.py --pause waiting on CI
   ```
   Executed it against an armed main plan: exit **0**, sentinel contained **`paused: waiting`**. Arguments containing spaces lose their boundaries; the documented `title|doing|why` syntax becomes shell pipelines. Quote the complete argument vector, including the script path.

5. **LOW — Dashboard mutation totals are stale.** `docs/dashboard-entries.md:17630`  
   It claims `2105 -> 2108`. The diff updates the declared total **2115 → 2118**, and summing the delivered manifests produced **2118**. The PR body has the corrected figures.

Validation: all experiments ran under `mktemp -d`; no repository files were edited. `python3 scripts/begin-plan.py --self-test` passed **131/131**. Each of the four new cases reddened under its corresponding flip. Spies confirmed ordinary linked-worktree refusal precedes every handler and state loader, including `--status`. Submodule, bare-repository, and symlink probes produced no false detection. The moved `global` declaration is safe; state restoration remains present. Caller inspection found CI uses the exempt self-test, and mutation copies omit `.git`; no additional ordinary caller regression was established.

Backlog #358’s PR #405 example is supported: run `40378652317` logged all three 150-second ffmpeg download timeouts. Its aggregate frequency was not independently recounted.

VERDICT: NOT CONVERGED
