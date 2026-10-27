<!-- codex-review: model=gpt-6.1-sol -->

Reviewed `1003add0` against `9ac7c80d` using `git diff origin/master...HEAD`. No repository files changed. All victims, hostile configs, generated snippets, and mutants were under temporary directories.

The claim is refuted.

1. **Major — unsafe `codex-review.py` exemption still permits victim writes.**  
   `scripts/check-fixture-git-isolation.py:61`; `scripts/codex-review.py:2319`.

   `unredirected()` strips only `GIT_DIR`, `GIT_WORK_TREE`, and `GIT_COMMON_DIR`. The fixture consequently retains `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`, and command-scope config.

   **Executed reproduction:** initialized a fresh temporary victim for each run, exported `GIT_DIR=<victim>/.git`, and ran:

   ```sh
   GIT_INDEX_FILE=<victim>/.git/index python3 -B scripts/codex-review.py --self-test
   ```

   Separately:

   ```sh
   GIT_OBJECT_DIRECTORY=<victim>/.git/objects python3 -B scripts/codex-review.py --self-test
   ```

   Both passed **168/168**, exit 0. SHA-256 over sorted relative filenames and file contents under the victim’s `.git` changed:

   | Additional channel | Before | After |
   |---|---|---|
   | `GIT_INDEX_FILE` | `a8030606f0dc…` | `0c267528558f…` |
   | `GIT_OBJECT_DIRECTORY` | `a8030606f0dc…` | `7dc2c8c12e92…` |

   Config isolation also fails: a temporary `HOME/.gitconfig` setting `core.fsmonitor` to a marker-writing script invoked it **twice**, with 168/168 passing. Supplying the same setting through `GIT_CONFIG_COUNT/KEY_0/VALUE_0` invoked it **five times**, again passing.

   **Fix:** construct the fixture’s environment with `fixture_git.env()`, including the production calls exercised by the fixture. Preserve production config semantics by controlling the self-test environment around those calls; do not rely on `unredirected()` as fixture isolation.

2. **Major — `check-diff-coverage` self-test still reads caller global config.**  
   `scripts/check-fixture-git-isolation.py:65`; `scripts/check-diff-coverage.py:301`.

   `constructed_env()` retains `HOME` without disabling global/system config. Most real fixture calls add isolation through `iso()` or `iso_run()`, but the final `main()` cases use ordinary production launches.

   **Executed reproduction:** created a temporary HOME containing:

   ```ini
   [trace2]
       eventTarget = <temporary-directory>/events
   ```

   Ran `check-diff-coverage.py --self-test` with that HOME and inherited `GIT_*` removed. It passed **61/61**, exit 0, while the global setting recorded two git launches: diffs against `no-such-ref-xyz...HEAD` and `HEAD...HEAD`.

   The same probe against `check-run-hook.py` passed **72/72** with **zero** events. Its `base_env()` exemption is supported by this test.

   **Fix:** isolate the environment throughout the self-test, including its `main()` cases. Update the exemption reason to distinguish repository-redirection protection from config isolation.

3. **Major — merely containing a helper call satisfies the environment check.**  
   `scripts/check-fixture-git-isolation.py:107`.

   `_calls_helper()` searches descendants instead of establishing that the supplied environment is isolated.

   **Executed reproduction:** both following environments were accepted by `check_source()` with code 0:

   ```python
   env={**fixture_git.env(), **os.environ}
   ```

   ```python
   env=os.environ if True else fixture_git.env()
   ```

   I used each on this launch inside `_self_test()`, alongside an isolated `git init`:

   ```python
   subprocess.run(
       ["git", "config", "fixture.leak", "yes"],
       env=...,
   )
   ```

   With `GIT_DIR` exported to a temporary victim, both executions exited 0 and changed its `.git/config`. The conditional form never even evaluates the helper call.

   **Fix:** validate a restricted environment-expression grammar. Require a direct helper call, or explicitly safe composition whose later entries cannot override isolation. Add executed regression cases for both forms above.

4. **Major — one isolated launch hides unchecked launches; shell-only builders pass outright.**  
   `scripts/check-fixture-git-isolation.py:78`, `:118`, `:129`, `:152`.

   The “no checkable call” fallback protects only files with zero recognized fixture launches.

   **Executed reproduction:** after one isolated literal `subprocess.run(["git", "init", ...])`, each following addition was accepted with code 0 and changed the temporary victim’s config:

   ```python
   os.system("git config fixture.leak yes")
   ```

   ```python
   cmd = ["git", "config", "fixture.leak", "yes"]
   subprocess.Popen(cmd).wait()
   ```

   ```python
   launch(["git", "config", "fixture.leak", "yes"])
   # module-level launch(cmd) calls subprocess.run(cmd)
   ```

   A module-level `configure()` helper outside test-named scope, called by `_self_test()`, likewise passed while writing through an inherited environment.

   Even without the isolated decoy, this entire builder passed:

   ```python
   def _self_test():
       os.system("git init -q; git config fixture.leak yes")
   ```

   **Fix:** follow fixture-reachable helpers and recognize shell/variable/wrapper launches, refusing unresolved process launches in that scope. Unsupported shapes must remain refusals when another recognized launch exists.

5. **Minor — unrelated `"init"` arguments falsely classify legitimate code as repository builders.**  
   `scripts/check-fixture-git-isolation.py:82`.

   **Executed reproduction:**

   ```python
   def _self_test():
       obj.method("init")
   ```

   `check_source()` returned 1, claiming a repository build with no checkable git launch. There is no git operation.

   **Fix:** associate builder detection with git launchers or resolved git wrappers rather than arbitrary positional strings.

Additional verification:

- All **eight migrated fixtures** left the temporary victim’s `.git` byte-identical under exported `GIT_DIR`. Several suites went red through production readers, as documented.
- Literal `Popen`, `check_output`, `cwd`-only calls, precomputed environment names, and `env` supplied through `**kwargs` were refused. Safe `**{"env": fixture_git.env()}` is also refused.
- All **23 manifest mutations** were applied to temporary copies and executed. Every edit anchor occurred exactly once; every mutant exited nonzero and failed every named expected case. No equivalent or ambient-pass mutant was observed in this run. These cases nevertheless omit the bypasses above.
- CI explicitly runs the helper self-test, guard self-test, and live guard at `.github/workflows/ci.yml:412–417`. Baselines passed **14/14**, **28/28**, and the live scan respectively.

VERDICT: NOT CONVERGED
