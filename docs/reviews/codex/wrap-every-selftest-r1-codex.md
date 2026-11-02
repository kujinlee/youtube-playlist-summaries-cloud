<!-- codex-review: model=gpt-6.1-sol -->

1. **Major — dispatch discovery silently excludes real suites.** `scripts/check-fixture-git-isolation.py:152` and `:326`.

   This program is accepted and omitted from the population:

   ```python
   import subprocess, sys

   def suite():
       subprocess.run(["git", "init", "-q"])
       subprocess.run(["git", "config", "fixture.escape", "yes"])

   {"--self-test": suite}[sys.argv[1]]()
   ```

   Executed in a temporary directory with `GIT_DIR` pointing at a fresh victim: exit 0, victim config gained `fixture.escape=yes`. Master’s guard returns 1; this branch returns 0.

   `getattr` dispatch and argparse `action=` dispatch also bypass discovery. A two-file reproduction delegating to a sibling’s argparse dispatcher passed **whole-tree** checking with “0 --self-test script(s)” and wrote the victim.

   **Fix:** recognize flag registrations outside conditional tests, refuse opaque dispatch, and require an auditable dispatcher for dynamic or delegated routes. Add these population regressions without restoring the builder detector.

2. **Major — decorators can replace the checked entry.** `scripts/check-fixture-git-isolation.py:182`.

   Beside the usual flag dispatch:

   ```python
   def replace(fn):
       return lambda: subprocess.run(
           ["git", "config", "fixture.escape", "yes"])

   @replace
   def self_test():
       with fixture_git.isolated():
           return 0
   ```

   Guard returns 0. Execution exits 0 and writes the victim: the dispatched callable is the decorator’s replacement, whose body was never checked.

   **Fix:** reject decorators on canonical entries, or explicitly validate the resulting dispatch semantics. Merely checking the original function body does not establish isolation.

3. **Major — an async entry can pass without executing its suite.** `scripts/check-fixture-git-isolation.py:330` and `:345`.

   ```python
   async def self_test():
       with fixture_git.isolated():
           assert False, "suite executed"

   if "--self-test" in sys.argv:
       self_test()
   ```

   Executed result: guard 0, process exit 0, assertion never reached, and a “coroutine was never awaited” warning.

   **Fix:** require synchronous `ast.FunctionDef` entries for this canonical contract, or verify that async dispatch actually awaits the entry. Add an executed negative case proving the assertion runs.

4. **Major — rule 5 skips executable exception-type expressions.** `scripts/check-fixture-git-isolation.py:290`.

   Insert this beside a canonical isolated entry and dispatch:

   ```python
   try:
       raise ValueError()
   except (
       subprocess.run(["git", "init", "-q"]),
       subprocess.run(["git", "config", "fixture.escape", "yes"]),
       ValueError,
   )[2]:
       pass
   ```

   Master returns 1; branch returns 0. Execution exits 0 and writes the victim config. This is a direct launch inside a module-level `try`, beyond the documented indirect-launch limits.

   **Fix:** inspect each handler’s `type` expression, including for `TryStar`, as well as its body. Add an executed regression.

5. **Minor — the unconditional “nothing is loosened” statement is false.** `docs/backlog.md:364`.

   I loaded both guards and ran their `check_source` functions over identical probe text. Each following program contained `git init` and a config write; each executed successfully and changed the victim:

   | Probe | Master | Branch |
   |---|---:|---:|
   | Dict dispatch | 1 | 0 |
   | `getattr` dispatch | 1 | 0 |
   | Argparse action dispatch | 1 | 0 |
   | Assigned launcher, `r = subprocess.run` | 1 | 0 |
   | `__import__("subprocess").run(...)` | 1 | 0 |
   | Class-body launch | 1 | 0 |
   | Module-level builder with no self-test | 1 | 0 |
   | Exception-type launch above | 1 | 0 |

   Some relaxations are explicitly intentional under #380 and the detector deletion. They still disprove claim (4).

   **Fix:** replace the universal statement with a bounded, measured claim and enumerate intentional relaxations. Preserving literal equivalence requires refusing these counterexamples.

Verification completed in temporary copies:

- The delivered population is **79 scripts, zero exemptions**.
- All 79 suites ran wrapped and unwrapped. Normalized full output and case sequences differed only at the documented `gen-dashboard` HOME assertion. `subject_status` remained 16/17 in both.
- The coordinator runner completed **711 runs across all nine families: zero victim changes and zero marker hits**. Two initial nonzero `check-run-hook` runs both passed diagnostic reruns at 72/72; their initial cause remains unproven.
- All **35 guard mutations and both rebound dashboard mutations** were killed, with every expected case name appearing exactly once among the failures.
- `EXPECTED_MUTATIONS` and manifest cardinality both equal **2,340**. Every mutation anchor resolves exactly once.
- Double wrapping, `isolated() as x`, and imported isolation aliases remained isolated in the executed probes. The documented indirect-launch escapes were also reproducible.

VERDICT: NOT CONVERGED
