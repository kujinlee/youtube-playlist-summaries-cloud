<!-- codex-review: model=gpt-6.1-sol -->

Both self-tests passed: **66/66** and **234/234**. The scratch probes nevertheless reproduced data loss.

### R1-F1 — Blocking — Forged `.git` passes ownership proof and overwrites another checkout’s index

**File:** `scripts/regen-pages.py:134–142`

**Scenario:** Replace the generator tree’s `.git` file with `gitdir: <main>/.git`, or copy another linked worktree’s `.git` file into it. Both pass `_own_worktree()`: Git reports the generator directory as its top level and the expected common directory.

**Repro:** In scratch clones, stage unique content in the main checkout or another worktree, substitute the pointer, then call `materialise()`. It succeeds and replaces that checkout’s staged content with committed content. The main-pointer case also detaches the main checkout’s HEAD.

**Fix:** Verify the actual Git administration directory and its reciprocal worktree registration. Require a dedicated linked-worktree identity; explicitly reject the main Git directory and metadata registered to another path. Add real-Git regression cases for both substitutions.

### R1-F2 — Blocking — Path replacement after proof lets both destructive commands reach main

**File:** `scripts/regen-pages.py:156–168`

**Scenario:** The proof and destructive subprocesses resolve the path separately. The advisory lock does not prevent filesystem replacement.

**Repro:** In a scratch clone, intercept the first `checkout` call after successful proof. Rename the generator tree and replace its path with a symlink to main, then execute the original Git call. Main’s tracked edit becomes committed content, and `clean -fdq` deletes its untracked file. The subsequent proof raises `CannotRun` **after the loss**.

**Fix:** Bind validation and execution to stable directory and Git metadata identities, preventing path rediscovery through replaceable names. Prefer a design without destructive reuse if that guarantee cannot be established. Add deterministic replacement tests before both destructive commands.

### R1-F3 — High — Refresh timeout releases the tree lock while its generator keeps running

**File:** `scripts/explainer-serve.py:1456`; `scripts/regen-pages.py:186`, `scripts/regen-pages.py:274`

**Scenario:** Refresh now launches a runner which launches a generator. `subprocess.run(..., timeout=left)` kills the runner on timeout, leaving its generator alive. Killing the runner releases its file lock, allowing another rebuild to move the tree beneath the surviving generator.

**Repro:** In a scratch clone, launch a generator that writes a start marker, sleeps, then writes a completion marker. Timeout its runner after 0.8 seconds. The tree lock is immediately acquirable while the generator remains active; the completion marker subsequently appears.

**Fix:** Manage the subprocess group and terminate and reap descendants on timeout or cancellation. Ensure the lock remains held until every process using the tree has stopped.

The scratch probes confirmed that a missing tree is recreated safely, an existing symlink is refused, and inherited `GIT_DIR`/`GIT_WORK_TREE` are scrubbed. Injected fetch, worktree-add and read-back failures refused materialisation; lock contention also refused it. A killed holder leaves an acquirable lock, with the surviving-child exception above.

The live ledger and goal-tree log resolve through `session-state.main_checkout`. The changed publishing callers route through the runner; `check-page-links.py` still invokes generators directly for temporary validation output. Mutation exclusions document a reason for protecting the real-repository self-test guard, but the ownership mutations use mocked Git answers and miss both reproduced identity failures.

Reproduction script: `/tmp/review-regen-r1.py`. No GitHub actions were taken; `.claude/plans/` was not read.

## Loosening answers
LOOSENING-CHECK fb89f268396d: finding: a Refresh timeout now leaves a descendant generator running after the runner is killed and its tree lock is released
LOOSENING-CHECK 606dad727ce8: not a loosening
LOOSENING-CHECK 935e69a64e55: not a loosening
LOOSENING-CHECK 705455503855: not a loosening
LOOSENING-CHECK 0ca3caeb1539: not a loosening
LOOSENING-CHECK 06eb9b4d1609: not a loosening
LOOSENING-CHECK 68a9fd0367a4: not a loosening
LOOSENING-CHECK e29b3fb8fa9a: not a loosening
LOOSENING-CHECK ef8c9de45337: not a loosening
LOOSENING-CHECK b25e1072da48: not a loosening
LOOSENING-CHECK 0670c030fae3: not a loosening
LOOSENING-CHECK 51049a3f8433: not a loosening
LOOSENING-CHECK 75ec8edc4012: not a loosening
LOOSENING-CHECK 27004bcf2f0b: not a loosening
LOOSENING-CHECK 4a9e19b085f0: not a loosening
LOOSENING-CHECK 647fd36ca84a: not a loosening
LOOSENING-CHECK 1004179b2d29: not a loosening
LOOSENING-CHECK afddc8ea43c6: not a loosening
LOOSENING-CHECK 302dad7bb9d4: not a loosening
LOOSENING-CHECK e2fc910cf7f5: not a loosening
LOOSENING-CHECK e2fc910cf7f5: not a loosening
LOOSENING-CHECK 62376f70e7a2: not a loosening
LOOSENING-CHECK 0b55d8682aec: not a loosening
LOOSENING-CHECK e74a4c7a0c52: not a loosening
VERDICT: NOT CONVERGED
