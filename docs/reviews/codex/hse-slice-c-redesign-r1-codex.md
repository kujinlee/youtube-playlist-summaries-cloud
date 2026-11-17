<!-- codex-review: model=gpt-6.1-sol -->

1. **MAJOR — `scripts/check-shipping-sets.py:512`: `-c` consumes the interpreter without recording an outcome.**

   Concrete `scripts/main.py`:

   ```python
   import subprocess
   subprocess.run(["python3", "-c",
                   "__import__('runpy').run_path('scripts/secret.py')"])
   ```

   In a temporary repository, `scripts/secret.py` existed but the map and declaration carried only `scripts/main.py`. Runtime printed `EXECUTED SECRET`. Both `--map` and `--closure` returned **rc 0, `0 gaps`**, with **no unresolved line**.

   `read = True` suppresses the unresolved branch, although no edge was read. This contradicts the explicitly promised census of `-c` argv. **Redesign causality:** pre-existing omission, left uncovered by the new census; reproduced against both revisions.

2. **MAJOR — `scripts/check-shipping-sets.py:551`: dynamic module loads bypass the package and missing-outcome census.**

   Concrete `scripts/main.py`:

   ```python
   import importlib
   importlib.import_module("secret")
   ```

   Temporary repository contained `scripts/secret/__init__.py`, printing `EXECUTED PACKAGE`; the map and declaration carried only `scripts/main.py`.

   Runtime printed `EXECUTED PACKAGE`. Both commands returned:

   ```text
   --map:     rc 0, 0 gaps
   --closure: rc 0, 0 gaps; no unresolved line
   ```

   The module branch invents `scripts/secret.py` and skips `groups`; closure filters that nonexistent file away. The directory check only handles import statements. Likewise, `importlib.import_module("missing_sibling")` produced no unresolved line despite neither candidate existing. **Redesign causality:** pre-existing omissions that the new outcome census fails to close; the package fixture also passes both base commands.

3. **MINOR — `scripts/regen-pages.py:886`: the crash case now accepts additional failure names.**

   Concrete temporary mutation: append this immediately before `_crash_guarded` returns `1`:

   ```python
   print("  [FAIL] EXTRA")
   ```

   Ran the actual base and head crash-case blocks against the same mutated guard, using the actual consumer parser extracted into the temporary fixture.

   **Observed:** head case **PASS**; base case **FAIL**, because the parsed names were `[CRASH_CASE, "EXTRA"]`. Checking only the first output line loses the former check against additional failure markers. **Redesign causality:** introduced by replacing `parse_fail_names(out)` with `out.split("\n")[0]`.

Required checks passed: shipping self-test **134/134**, live map and closure **0 gaps**, regen self-test **121/121**. Comparing executable edges across tracked Python files found **no live-tree edge changes**. All fixtures and script copies were outside the repository.

## Loosening answers
LOOSENING-CHECK d33473a96a90: not a loosening
LOOSENING-CHECK 190b73aac639: not a loosening
LOOSENING-CHECK 939acd9343c1: not a loosening
LOOSENING-CHECK cc245bcb0786: not a loosening
LOOSENING-CHECK 19469b8e02fd: not a loosening
LOOSENING-CHECK c831b4186cd2: not a loosening
LOOSENING-CHECK f5afa5051b4a: not a loosening
LOOSENING-CHECK ff1226fbb8bc: not a loosening
LOOSENING-CHECK a34553d561d3: not a loosening
LOOSENING-CHECK 11b86e8a177d: not a loosening
LOOSENING-CHECK c4530de76b8a: finding: additional [FAIL] lines after the expected first line now pass; master rejected their additional parsed failure names
LOOSENING-CHECK 63c2d7b9967f: not a loosening
LOOSENING-CHECK 2b345742f57d: not a loosening
LOOSENING-CHECK 629172a8b7e0: not a loosening
LOOSENING-CHECK 33af64a6b800: not a loosening
LOOSENING-CHECK b27c359b9752: not a loosening
LOOSENING-CHECK 463867463adb: not a loosening
LOOSENING-CHECK e7535ba71eed: finding: the replacement expectation accepts output containing additional [FAIL] names after CRASH_CASE, which master's parsed-name expectation rejected
LOOSENING-CHECK 6b6b1d7f84eb: not a loosening
LOOSENING-CHECK ad4c58b480b5: not a loosening
VERDICT: NOT CONVERGED
