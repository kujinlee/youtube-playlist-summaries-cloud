<!-- codex-review: model=gpt-6.1-sol -->

The existing-suite isolation sweep held, but the guard/LIMITS bet is refuted.

1. **Major — Import-time git writes escape an otherwise valid isolated entry.**  
   **Location:** `scripts/check-fixture-git-isolation.py:335`, `:63`.

   The guard rejects import-time repository **builds**, but accepts this program:

   ```python
   import subprocess
   import fixture_git

   subprocess.run(["git", "config", "fixture.escape", "yes"], check=True)

   def body():
       subprocess.run(["git", "init", "-q", fixture_path], check=True)

   def self_test():
       with fixture_git.isolated():
           return body()
   ```

   **Executed reproduction:**
   ```sh
   PYTHONDONTWRITEBYTECODE=1 python3 /tmp/fixture-r3.kumrVw/probes.py
   ```
   Result: **guard=0, process rc=0, victim config gained `fixture.escape=yes`**. Adding the probe to a temporary full clone also passed the live guard: **17 isolated suites, zero exemptions**.

   This uses none of the named LIMITS: no capture, rebound name, decoy dispatch, callback, or `os.putenv`.

   **Fix:** reject import-time git launches in checked suites, with an executed regression case. If deferred, explicitly name import-time execution in LIMITS and #380 and narrow the completeness claim.

2. **Major — X8 misses builders whose wrapper cwd is a literal.**  
   **Location:** `scripts/check-fixture-git-isolation.py:205`.

   The wrapper detector skips leading arguments only until the first `ast.Constant`. Consequently:

   ```python
   def git(cwd, *args):
       subprocess.run(["git", "-C", cwd, *args], check=True)

   def self_test():
       git("/temporary/path", "init", "-q")
       git("/temporary/path", "config", "fixture.x8", "yes")
   ```

   **Executed reproduction:**
   ```sh
   PYTHONDONTWRITEBYTECODE=1 python3 /tmp/fixture-r3.kumrVw/x8.py
   ```
   The `literal-cwd` variant returned **guard=0, process rc=0, victim key=yes** under planted `GIT_DIR`. Using a cwd *name* instead is correctly refused.

   All command components are visible literals; the documented dynamically assembled-command bound does not describe this omission.

   **Fix:** retain wrapper parameter information and locate the arguments feeding its git argv. Do not infer the subcommand from the first constant argument.

3. **Major — The shell detector omits a documented value-taking global option.**  
   **Location:** `scripts/check-fixture-git-isolation.py:101`.

   **Executed reproduction:** the same `x8.py`, variant `shell-config-env`, runs an unwrapped suite containing:

   ```python
   os.system("git --config-env foo.bar=BAZ init -q")
   os.system("git config fixture.x8 yes")
   ```

   With `BAZ=ok` and victim `GIT_DIR`, the result was **guard=0, process rc=0, victim key=yes**.

   `--config-env` appears in `GIT_VALUE_OPTS` but is absent from the shell expression’s value-taking options. This literal builder is silently omitted.

   **Fix:** parse shell git arguments through the same subcommand logic, or cover every supported value-taking option consistently. Add an executed regression.

4. **Minor — X8 also misclassifies a literal cwd as the subcommand.**  
   **Location:** `scripts/check-fixture-git-isolation.py:205`.

   **Executed reproduction:** `x8.py` reports **guard=1** for a wrapper call `git("init", "status")`. Executing that status-only program in a temporary directory containing a repository named `init` returned **0**; it builds nothing.

   **Fix:** the wrapper argument binding described in finding 2, plus a false-positive regression.

Verification completed in temporary directories:

- Independently derived **80 scripts × 9 families = 720 runs**: **zero victim changes and zero marker hits**.
- The documented dependency failures and `subject_status` failure remained. Three additional parallel `check-run-hook` runs exited without tallies; all three passed **72/72** on repeat, with no hits.
- `brief-compose`: **153/153** before and after wrapping; `gen-backlog-page`: **165/165**. No vacuous-pass regression found.
- Guard **45** + composer **27** mutations: **72 killed, 72 attributed, zero survivors**; anchors unique.
- Declared and actual manifest totals both equal **2303**.
- Both `GIT_SUITES` entries still run git. #380 has a concrete falsifier, but its limits need the additional disposition above.

Artifacts: `/tmp/fixture-r3.kumrVw/`. No repository edits were made; final working tree is clean.

VERDICT: NOT CONVERGED
