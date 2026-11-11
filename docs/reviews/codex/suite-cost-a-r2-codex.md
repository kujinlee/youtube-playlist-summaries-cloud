<!-- codex-review: model=gpt-6.1-sol -->

### R2-F1 — Medium — fix_induced: yes — Re-entrant sibling import disables the outer dependency recorder

`scripts/goal-tree.py:247–251`

**Input:** A calls `_sibling("B")`, then reads a data file at import time. Import A, change only that data file from `1` to `2`, and request A again.

**Result:** Cached A returned **1**; a fresh import returned **2**. B replaces the shared `_SIBLING_READS` and resets it to `None`, so A’s subsequent reads never enter its key. Ordinary nested `spec.loader.exec_module()` imports passed; re-entering `_sibling` fails.

### R2-F2 — Medium — fix_induced: yes — Concurrent imports lose dependencies and leave bytecode settings changed

`scripts/goal-tree.py:244–252`

**Input:** Use thread events to overlap two sibling imports. T1 enters first, T2 enters second, T1 finishes, then T2 reads a data file and finishes.

**Result:** T2’s data read was omitted from its key; after changing the file, its cached value remained **1**. The process also retained `dont_write_bytecode=True` and T1’s already-deleted temporary `pycache_prefix`. T2 saved T1’s temporary settings and restored them after T1 restored the originals.

Both findings use constructed callers; I found no current production caller exercising these overlaps.

Verification completed:

- Self-test: **434/434 passed**.
- Two exact mutations hand-checked in scratch: skipping sibling-own bytes and retaining the real `pycache_prefix`. Both failed their named same-stamp case, **432/434**.
- `sys.modules` and custom-finder probes returned cached **1**, fresh **2**. These fall within the documented plain-import exclusion.
- After import, **1,000 unrelated opens** caused no key growth; recording was inactive. Permanent hooks retain callback overhead.
- Deleting a recorded dependency caused a miss and re-execution; the sibling then raised `FileNotFoundError`. Lookup itself handled absence correctly.
- Serial success and exception paths restored both bytecode settings.
- Master `bd1284b4`, one cold/warm pair: **10.972 s / 5.617 s**, both **428/428**. Warm bytecode materially helped, but this does **not establish** that round 1’s historical 2.7 s measurement was warm.

Repository unchanged; no GitHub writes or `.claude/plans/` reads.

VERDICT: NOT CONVERGED
