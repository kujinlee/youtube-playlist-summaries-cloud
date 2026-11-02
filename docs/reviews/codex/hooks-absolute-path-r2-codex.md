<!-- codex-review: model=gpt-6.1-sol -->

Review of `6178e305`, mandate **REFUTE**. Repository unchanged; all experiments ran in `/tmp/hooks-r2.c46i96`.

1. **High — inherited Git discovery settings can select the wrong checkout and bypass its plan gate.**  
   `.claude/hooks/run-hook.sh:38–43` clears three Git variables but retains `GIT_CEILING_DIRECTORIES`.

   Reproduced with main checkout `M`, linked worktree `W`, project dir `M`, and a pending plan gate only in `W`:

   ```sh
   cd W/sub
   GIT_CEILING_DIRECTORIES=W CLAUDE_PROJECT_DIR=M \
     bash "$M/.claude/hooks/run-hook.sh" block-implementation-before-plan-gate.sh
   ```

   With an implementation `Agent` payload, this exits **0**. Without the ceiling variable, it exits **2**. A probe confirms that the affected invocation executes **main’s hook**. Failed discovery silently becomes permission to substitute another checkout—the round-1 failure returns.

   The discovery environment needs isolation, with this world covered by a test.

2. **Medium — the launcher changes working behavior at a submodule root.**  
   `.claude/hooks/run-hook.sh:42` treats the submodule as unrelated and selects the parent project.

   I installed the plan hook and pending sentinel in a real submodule, leaving the parent unarmed:

   | Invocation from submodule root | Result |
   |---|---|
   | Old relative command | **2**, blocked |
   | New launcher, project dir = parent | **0**, allowed |

   This follows the implemented common-directory policy, but contradicts the PR body, backlog row, and launcher comment claiming equivalent behavior **at any checkout root**. Either preserve this behavior or explicitly narrow the contract and document the regression.

3. **Medium — a missing worktree hook silently substitutes main’s hook.**  
   The file-existence condition at `run-hook.sh:39` participates in checkout selection. Removing the plan-hook file from `W`, while retaining its pending sentinel, makes an invocation from `W/sub` execute main’s unarmed hook and exit **0**.

   Once the cwd identifies a worktree of this repository, a missing hook should reach the missing-hook diagnostic for that checkout. It should not select another checkout’s implementation.

4. **Low — evidence attribution and published counts are inaccurate.**  
   All **13 manifest mutations were killed**, but the final mutation, “main() ignores the root it is given,” was **not killed by its named case**. Its expected “shipped defect exits 1” case stays green because `unregistered={}` causes the real repository’s deliberately unregistered memory hook to produce exit 1 anyway. Two other cases kill the mutation. Thus “each killed by its named case” is false.

   The backlog #223 row and dashboard entry also say **29 cases**; the executed suite has **32**. The PR body correctly says 32. The manifest totals **2138 → 2151** are correct.

Other executed results:

- **32/32 self-tests passed**; the tracked registration check accepted all **13 commands**.
- All **six hand mutations** made their corresponding launcher cases fail.
- Round 1’s ordinary linked-worktree plan-gate world now blocks correctly, including through a symlinked project path.
- Symlinked cwd, relative project path, trailing slash, and bare-repository worktrees selected the expected hook.
- Explicit `GIT_DIR`, `GIT_WORK_TREE`, and `GIT_COMMON_DIR` did not redirect selection.
- From `.git/`, a worktree’s administrative directory, or a non-git project directory, the launcher used the project fallback.
- Empty/unset project variables work at checkout root but still exit **127** from a subdirectory. This retains the old limitation; the “from anywhere” prose needs that qualification.
- Stdin survived intact, with zero arguments forwarded. A quoted hook name containing spaces launched directly; the guard deliberately refused its registration.
- A direct push-hook invocation from `scripts/`, with a configured remote, returned **`permissionDecision: deny`**. No push occurred; live harness verification remains outstanding.
- Median launch time was about **14 ms** before, **28–29 ms** with a physical project path, and **51–54 ms** when three Git probes ran. The overhead is measurable and accumulates across hooks, but does not independently block convergence.

The redesign fixes the ordinary worktree regression and closes the demonstrated command-shape bypasses. The wrong-checkout bet is nevertheless refuted.

VERDICT: NOT CONVERGED
