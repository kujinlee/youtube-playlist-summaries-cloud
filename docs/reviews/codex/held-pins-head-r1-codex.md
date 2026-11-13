<!-- codex-review: model=gpt-6.1-sol -->

### R1-F1 — High — `git archive` can rewrite HEAD’s harness and conceal lowered pins

**Location:** scripts/check-merge-ready.py:1402

**Scenario:** `git archive` honors `export-subst`. The imported harness can therefore differ from HEAD’s actual blob, even on a clean working tree. This introduces a false pass that master refused.

**Repro:** In a temporary real repository, mark `scripts/check-plan-code.py export-subst` in `.gitattributes`. Immediately before initializing `EXPECTED_MUTATIONS`, insert:

```python
PINS_FILE = (
    "scripts/mutations/low.py"
    if "$Format:%s$" == "$" + "Format:%s$"
    else "scripts/mutations/expected_mutations.py"
)
```

Commit `low.py` with one lowered pin and leave the displayed pins unchanged. The actual harness selects `low.py`; archive substitution changes the comparison and makes the archived harness select the unchanged display.

Measured result: HEAD’s actual harness held **4**, the display held **5**, and `pin_falls(*pin_pair(...))` returned **`[]`**. Master’s working-tree import sees the lowered value and refuses the mismatch.

**Fix:** Materialize exact HEAD blobs without archive attribute transformations, or verify all extracted files against their committed blobs before importing. Add this clean-tree regression case.

### R1-F2 — Medium — Fileless modules escape isolation and survive failed imports

**Location:** scripts/check-merge-ready.py:1383 and :1391

**Scenario:** `own()` treats an ordinary module without `__file__` or `__path__` as an interpreter module. Such modules can originate in working-tree code or be created during HEAD’s import. They remain visible during isolation and survive cleanup, including exceptional exits.

**Repro:** Executed this sequence:

```python
try:
    with gate._isolated_import():
        mod = types.ModuleType("_review_redir")
        mod.PINS_FILE = "working-tree-pins.py"
        sys.modules["_review_redir"] = mod
        raise RuntimeError("failed head import")
except RuntimeError:
    pass

with gate._isolated_import():
    print(__import__("_review_redir").PINS_FILE)
```

It printed `working-tree-pins.py`. The second isolated import reused a module created during the failed first import. A preloaded fileless redirect module likewise bypasses hiding. Thus `sys.modules` is not restored exactly, and later cases can inherit configuration absent from their archived HEAD.

**Fix:** Identify interpreter-owned fileless modules positively rather than trusting every fileless module. Restore the saved module mapping by removing every newly introduced entry before reinstating saved entries. Test both successful and exceptional exits, followed by a second import whose HEAD lacks the module.

Both requested self-tests passed:

- `check-merge-ready.py`: **354/354**
- `check-plan-code.py`: **418/418**

The six new mutation entries do not exercise either witness above.

## Loosening answers
LOOSENING-CHECK c47564441466: finding: the branch accepts an export-subst-transformed archived harness whose held pins match the display while the actual HEAD harness holds lowered pins; master refused that mismatch.
VERDICT: NOT CONVERGED
