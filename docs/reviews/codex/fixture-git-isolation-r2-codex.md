<!-- codex-review: model=gpt-6.1-sol -->

**The bet is refuted:** an existing omitted suite runs caller-configured commands, and several guard-accepted programs write a victim repository.

Reproductions and raw results are retained under `/tmp/fixture-r2.gKux9y/`. Repository files were not edited; `git status --short` remains empty.

1. **Major — The population misses `brief-compose`, which executes caller configuration.**  
   **Location:** `scripts/check-fixture-git-isolation.py:271`; `scripts/brief-compose.py:979`, `:1070`.

   Its self-test drives `main()`, which calls `page_chrome.provenance()` and consequently launches `git status` against the checkout. It neither builds a repository locally nor receives isolation.

   **Executed reproduction:**
   ```sh
   python3 /tmp/fixture-r2.gKux9y/runner.py /tmp/fixture-r2.gKux9y/tree count brief-compose
   ```
   Result: `rc=0`, `153/153`, `victim=same`, **`tree_hits=9`**. The `params`, `home`, `xdg`, and `global` families each produced **8 caller-command executions**, also with 153/153 passing.

   **Fix:** isolate this suite and enumerate git-running self-tests through imported production helpers. Correct the “all 29” population claim in `docs/backlog.md:355`, the dashboard entry at `docs/dashboard-entries.md:17901`, and the commit’s corresponding universal claim.

2. **Major — Import-time environment capture remains accepted.**  
   **Location:** `scripts/check-fixture-git-isolation.py:205`, `:271`, `:314`.

   **Executed reproductions:** run:
   ```sh
   PYTHONDONTWRITEBYTECODE=1 python3 /tmp/fixture-r2.gKux9y/probe.py
   PYTHONDONTWRITEBYTECODE=1 python3 /tmp/fixture-r2.gKux9y/captures.py
   ```
   Each following variant returned **guard=0, process rc=0, victim_changed=True**:

   - A sibling module stores `os.environ.copy()` before isolation.
   - A default argument stores `dict(os.environb)`.
   - A default argument calls `snapshot()`, which returns `dict(os.environ)`.
   - A class attribute calls its class-local snapshot helper.
   - `saved = functools.partial(os.environ.copy)()`.

   The shared backing dictionary protects a live `os.environb` reference, **not a snapshot**. Capture checks also stop at file boundaries and miss indirect evaluation.

   **Fix:** establish the clean environment before importing the tested module, preferably in a fresh interpreter. Otherwise capture analysis must cover sibling imports, bytes environments, and indirect default/decorator/class evaluation.

3. **Major — Imported names are trusted after rebinding.**  
   **Location:** `scripts/check-fixture-git-isolation.py:165`, `:173`.

   **Executed reproduction:** `probe.py`, variant `shadow`:
   ```python
   from fixture_git import isolated as x
   from contextlib import nullcontext as x

   def self_test():
       with x():
           return body()
   ```
   Result: **guard=0, rc=0, victim_changed=True**.

   **Fix:** validate bindings and scope at the actual context-manager call; reject reassigned or shadowed helper names. Collecting imports anywhere in the AST does not establish what the name resolves to.

4. **Major — The accepted `with` shape permits work outside isolation and caller HOME reuse.**  
   **Location:** `scripts/check-fixture-git-isolation.py:194`; `scripts/fixture_git.py:91`.

   **Executed reproductions:**

   - `probe.py`, `earlier-context`: `with earlier(), fixture_git.isolated(): ...`. The first context’s `__enter__` executes git before isolation. **guard=0, rc=0, victim_changed=True**.
   - `more.py`, `home-extra`: `with fixture_git.isolated(HOME=os.environ["HOME"]): ...`. A reader constructing its own HOME-preserving environment then runs the caller’s pre-commit hook. **guard=0, rc=0, marker=True**.

   **Fix:** enforce one context item with the canonical argument-free `isolated()` call. Put additional contexts and fixture HOME setup inside that boundary.

5. **Major — A decoy named entry hides the actual `--self-test` dispatch.**  
   **Location:** `scripts/check-fixture-git-isolation.py:287`, `:304`.

   **Executed reproduction:** run:
   ```sh
   PYTHONDONTWRITEBYTECODE=1 python3 /tmp/fixture-r2.gKux9y/more.py
   ```
   Variant `wrong-dispatch` defines an isolated `self_test()` that does nothing, while `--self-test` dispatches to `run_checks()`, which calls the repository-building body.

   Result: **guard=0, rc=0, victim_changed=True**. The outside-reference check only protects functions directly called by the decoy block.

   **Fix:** validate the actual CLI dispatch target and its reachable suite, rather than treating a suitably named function as proof of isolation.

6. **Major — Deferred launches execute after the ambient environment is restored.**  
   **Location:** `scripts/fixture_git.py:97`; `scripts/check-fixture-git-isolation.py:302`.

   **Executed reproduction:** `more.py`, variant `atexit`. Inside the accepted isolated body:
   ```python
   atexit.register(subprocess.run,
                   ["git", "config", "fixture.escape", "yes"])
   ```
   Result: **guard=0, rc=0, victim_changed=True**. The callback inherits the restored caller `GIT_DIR`.

   **Fix:** keep the self-test interpreter isolated through interpreter shutdown, including exit callbacks. A fresh child interpreter with a constructed environment provides that lifetime boundary.

7. **Major — `os.putenv()` defeats restoration and subsequent isolation.**  
   **Location:** `scripts/fixture_git.py:77`.

   **Executed reproduction:**
   ```sh
   PYTHONDONTWRITEBYTECODE=1 python3 /tmp/fixture-r2.gKux9y/controls.py
   ```
   The reproduction sets an initially absent `GIT_DIR` using `os.putenv()` inside one block, leaves it, and launches git inside a **second** `isolated()` block. The victim config changes.

   A separate control confirms the misleading state: `dict(os.environ)` is restored exactly, but an inherited-environment child still sees the hidden added variable.

   **Fix:** use a clean child-process environment for the whole suite. Iterating `os.environ` cannot remove C-environment keys that `os.putenv()` never inserted into that mapping.

8. **Minor — Git argument values still create false repository-builder classifications.**  
   **Location:** `scripts/check-fixture-git-isolation.py:148`.

   **Executed reproduction:** `controls.py` checks:
   ```python
   subprocess.run(["git", "log", "--grep", "init"],
                  capture_output=True)
   ```
   The guard refuses the suite as a repository builder, although its command is `log`.

   **Fix:** identify the git subcommand after global options; do not interpret every argument equal to `init` or `clone` as a build verb.

9. **Minor — A legitimately isolated imported builder is refused.**  
   **Location:** `scripts/check-fixture-git-isolation.py:289`.

   **Executed reproduction:** `controls.py`, `legitimate imported builder`. The entry wraps `sibling.build()` in `fixture_git.isolated()`, but `run_check()` refuses the sibling because that helper module has no self-test entry.

   **Fix:** distinguish helper modules from CLI self-test entries and validate the isolation of their calling entry.

The recorded 29-script sweep reproduced **zero victim changes and zero marker hits across all 261 runs**, but that population excludes finding 1. The helper and guard pass **42/42** and **70/70**. All **48 mutations were killed and attributed**, anchors were unique when applied in sequence, and both totals really are **2294**. The thirteen migrated application suites retain identical original suite bodies; I found no case-count regression.

VERDICT: NOT CONVERGED
