<!-- codex-review: model=gpt-6.1-sol -->

1. **Medium — direct launches in match guards escape the static half.** `scripts/check-fixture-git-isolation.py:451–454`

   `_module_level_code()` visits the match subject and case bodies but omits case guards, which execute at module level.

   **Reproduction:** add this `scripts/x.py` in a temporary copy:

   ```python
   import os, sys

   def self_test():
       import fixture_git
       with fixture_git.isolated():
           return 0

   match "--self-test" in sys.argv:
       case True if os.system("touch /tmp/match-marker") == 0:
           pass
   ```

   Executed: `run_check(temp_root, {})` returns **0**, reporting no direct launcher at module level. Importing the same file with `sys.argv = ["caller", "--self-test"]` exits **0** and creates the marker.

   This is a direct launcher call, outside the named non-literal-code limit. Include case guards in static traversal.

2. **Medium — skipping lambda bodies also skips their immediately evaluated defaults.** `scripts/check-fixture-git-isolation.py:473–474`

   **Reproduction:** retain the imports and canonical entry above, replacing the match statement with:

   ```python
   if "--self-test" in sys.argv:
       f = lambda x=os.system("touch /tmp/lambda-marker"): x
   ```

   Executed: the guard returns **0**. Importing with `--self-test` in argv exits **0** and creates the marker. The default executes when the lambda is created, before its body is called.

   Traverse lambda defaults while excluding the body. The current prose overstates coverage of direct calls within module-level `if` bodies.

Confirmed in temporary copies:

- **141/141** self-test cases pass; **79** scripts isolated, **0** exempt; **84** imports observed without launch or write. No delivered-script false refusal found.
- The fixed r1–r3 suite passes. Additional argv/CI/HOME direct-call probes are refused; inherited `sitecustomize` is excluded, and a virtual-environment `.pth` launch is detected and blocked.
- Ordinary if/elif/else, try/except/finally, with, for, and while bodies are traversed.
- **55/55 mutations** are killed, each named expected case appearing exactly once among failures. `EXPECTED_MUTATIONS` matches manifest counts and the **2,361** total.
- #380 records external enforcement with a concrete **FAILS IF**.
- Repository unchanged.

VERDICT: NOT CONVERGED
