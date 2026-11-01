<!-- codex-review: model=gpt-6-astra -->

**NOT CONVERGED**

1. **High — The self-test exemption permits import-time pin decreases.** `scripts/check-plan-code.py:2888–2892`. **Fix-induced: yes.**

   Replace the real function’s signature with:

   ```python
   def _self_test_body(_init=EXPECTED_MUTATIONS.update({
       "scripts/check-vocabulary-collisions.py": 4
   })) -> int:
   ```

   Defaults execute at function definition, outside the self-test run. The checker exempts the entire function AST, including defaults and decorators.

   **Reproduced against the real source:** `pin_shape_problems == []`, effective pin **5 → 4**, production `hold_reasons == []`. This decorator produces the same result:

   ```python
   @(lambda f: (EXPECTED_MUTATIONS.update({
       "scripts/check-vocabulary-collisions.py": 4
   }), f)[1])
   def _self_test_body() -> int:
   ```

   A second `_self_test_body` definition containing a write, followed by a module-level call, also passes. The checker does not enforce its stated premise that this scope runs only during self-tests and restores the dictionary.

2. **High — A string can conceal a genuine literal pin decrease from HOLD.** `scripts/check-plan-code.py:2883–2886`; `scripts/check-merge-ready.py:861–866`. **Fix-induced: yes, as an incomplete replacement safeguard; the textual matcher predates the fold.**

   Change the actual vocabulary-collisions pin from `5` to `4`, then append:

   ```python
   _audit_note = '''
       "scripts/check-vocabulary-collisions.py": 5,
   '''
   ```

   **Reproduced:** shape problems `[]`, effective pin `4`, HOLD reasons `[]`.

   The AST check validates the actual dictionary but ignores the string. `PIN_LINE` matches the string’s contents; the last matching added line overwrites the genuine `4` in the diff’s `new` map. Thus even a decrease that **does change a line PIN_LINE reads** need not HOLD. An ordinary `#` comment does not bypass it.

3. **High — “Read-only” calls are accepted by spelling, without resolving their binding.** `scripts/check-plan-code.py:2920–2921`. **Fix-induced: yes.**

   Append:

   ```python
   def adjust_pins():
       def dict(pins):
           pins["scripts/check-vocabulary-collisions.py"] = 4
       dict(EXPECTED_MUTATIONS)

   adjust_pins()
   ```

   **Reproduced against the real source:** shape problems `[]`, effective pin **5 → 4**. No pin declaration changes. This is ordinary Python, outside the self-test exemption and the documented dynamic-access exclusions.

4. **Medium — Ordinary typed-total assertions still escape the scan.** `scripts/check-plan-code.py:2939–2950`. **Fix-induced: yes.**

   Each concrete input returns `[]` from `typed_total_sites(src, 2986)`:

   ```python
   assert f"{declared_total()}" == "2986"
   assert declared_total() == 2900 + 86
   ```

   So does:

   ```python
   N = 2986
   assert declared_total() == N
   ```

   Conversely, `timeout(2986)` returns `[1]`: unrelated integers trigger the guard. A dictionary nested inside a call **is caught**:

   ```python
   case("t", declared_total(), {"total": 2986}["total"])
   ```

   The implementation detects matching integer literals in certain syntactic contexts, not typed-total dependencies.

Additional checks:

- Direct class-body writes are rejected.
- `exec`, `globals()`, and a second module importing and mutating the dictionary all bypass detection, as documented. Those exclusions are accurate, but make the unrestricted completeness claim untenable.
- The exact importlib block at `scripts/check-plan-code.py:6653–6657`, executed with a missing staged sibling, raises `FileNotFoundError`. It fails closed.
- Foreground baseline runs passed: **267/267** plan-code cases; **209/209** merge-ready cases.
- Counterexample results above establish source-check/runtime/HOLD behavior; they are not claims of full reduced-manifest sweep success.
- Worktree unchanged. No files under `.claude/plans/` accessed.
