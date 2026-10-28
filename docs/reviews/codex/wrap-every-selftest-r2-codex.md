<!-- codex-review: model=gpt-6.1-sol -->

1. **Major — launcher bindings bypass rule 5.** `scripts/check-fixture-git-isolation.py:323`

   `_launcher_names` follows only `Assign` nodes with simple name targets. These alternative bindings each bypass it:

   ```python
   import subprocess
   run: object = subprocess.run
   run(["git", "init", "-q", "d"])
   run(["git", "config", "fixture.escape", "yes"])
   ```

   Replace the annotated assignment with either `(run := subprocess.run)` or `run, = (subprocess.run,)`: same result.

   **Reproduction:** run both guards’ `check_source` over each program as `scripts/x.py`. Master returns **1**, branch returns **0**. Execute with `GIT_DIR` pointing at a fresh temporary victim: each exits 0 and writes `fixture.escape=yes` into the victim config. These direct launcher bindings are outside the listed intentional relaxations.

   **Fix:** follow `AnnAssign`, `NamedExpr` and unpacked bindings; recognize a named expression used directly as the callable. Add these programs to the fixed probe set.

2. **Major — aliased `import_module` bypasses rule 5.** `scripts/check-fixture-git-isolation.py:295`

   ```python
   from importlib import import_module as im
   im("subprocess").run(["git", "init", "-q", "d"])
   im("subprocess").run(["git", "config", "fixture.escape", "yes"])
   ```

   **Reproduction:** master returns **1**, branch returns **0**. Executed against the temporary victim, this exits 0 and changes its config.

   `_module_of` recognizes the literal name `import_module`, but does not resolve its imported aliases.

   **Fix:** track `importlib` and `import_module` aliases and rebindings, then resolve module-loading calls through those bindings. Add the reproduction as a regression probe.

3. **Major — executable assignment targets are omitted from import-time traversal.** `scripts/check-fixture-git-isolation.py:360–365`

   ```python
   import subprocess
   x = {}
   for x[(
       subprocess.run(["git", "init", "-q", "d"]),
       subprocess.run(["git", "config", "fixture.escape", "yes"]),
   )[1].returncode] in [0]:
       pass
   ```

   **Reproduction:** master returns **1**, branch returns **0**. Execution exits 0 and changes the victim config. Rule 5 visits the loop iterable and body, but skips the target’s evaluated expressions. A `with nullcontext(0) as x[<same expression>]` target also produces master **1**, branch **0**.

   **Fix:** inspect evaluated expressions in `For.target` and `withitem.optional_vars`, with regressions for both positions.

4. **Minor — population membership differs from the stated broad-source contract.** `scripts/check-fixture-git-isolation.py:172–179`

   **Reproduction:** either program below returns **0** and is omitted from the population, despite containing `--self-test` and having no canonical entry:

   ```python
   # --self-test
   ```

   ```python
   """--self-test"""
   ```

   The implementation deliberately uses non-docstring AST literals; the BET and requested rule say source contains the string.

   **Fix:** reconcile the contract and implementation explicitly. Implement source membership, or record prose-only mentions as an intentional exception and update the BET accordingly.

Verification:

- Both guards received identical fixed probes, including every named round-1 reproduction. The branch refuses all of them; its self-test passes **109/109**.
- All **48 guard mutations** were killed, with every listed expected case failing. Checks ran against in-memory mutants, reusing baseline execution results for unchanged probe programs.
- Forcing the dict-dispatch probe’s result to accepted makes the suite fail **108/109**, naming that probe.
- `EXPECTED_MUTATIONS` equals the actual **2,353** manifest entries; every per-target count matches.
- All **79 real population scripts pass the guard**; no real-script false refusal found.
- “None launches at import” is **not confirmed**: instrumented imports caught `check-ci-watched.py:128` calling `_repo_sentinel()`, which launches `git rev-parse --git-common-dir` at line 120. This fits the documented indirect-call limit.
- Called lambda, direct comprehension, match-body and annotation launch syntax, `os.posix_spawn`, `pty.spawn`, and `subprocess.getoutput` are refused. Concatenated flags remain accepted under intentional relaxation R3. Alias-only entry dispatch is refused. A symlinked population script is discovered and refused when missing an entry.
- Repository unchanged.

VERDICT: NOT CONVERGED
