<!-- codex-review: model=gpt-6.1-sol -->

## Findings

- **HIGH — `scripts/check-plan-code.py:836`: trailer dependencies can bypass the full-run guard.** `edit_needs_full_run` examines enclosing functions, but does not follow helpers called by the trailer. A mutation in such a helper can therefore produce a false kill.

  Reproducer: `python3 /tmp/pr476-repro.py` ([script](/tmp/pr476-repro.py)). It creates this initially green suite:

  ```python
  import sys, time

  def value():
      return 1

  def self_test():
      fails = value() != 1
      if fails:
          print("  [FAIL] named: got 0 want 1", flush=True)
      time.sleep(0.5)
      return value() if fails else 0

  if __name__ == "__main__":
      sys.exit(self_test())
  ```

  Mutate `return 1` to `return 0`, with `expect: "named"`. The predicate returns `False`.

  **Full mode:** exits 0; records `caught=False`, survivor present.  
  **Early mode:** interrupts after `named`; records `caught=True`, `attributed=True`, `stop="sigint"`, no survivor.

  The comments acknowledge exit-0-after-FAIL, but claim the printer/trailer predicate prevents it. This reproducer bypasses that protection and directly satisfies #405’s FAILS-IF. The full sweep on master detects the discrepancy only after the PR’s early run has certified it.

Validation: self-test **315/315 passed**. The `check-ratchet-contract.py` slice recorded **16 killed, 16 attributed, 0 survivors** in both modes; early mode stopped five mutants.

VERDICT: NOT CONVERGED
