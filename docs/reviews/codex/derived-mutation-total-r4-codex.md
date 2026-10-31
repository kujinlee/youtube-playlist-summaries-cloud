<!-- codex-review: model=gpt-6-astra -->

1. **High — A manifest-loader write lowers coverage after the assertion, with both witnesses green.**  
   **Locations:** `scripts/check-plan-code.py:2433`, `:2986`, `:3573`, `:7084`.  
   **Fix-induced:** yes at PR scope; the post-assertion gap remains after r3.

   Immediately after `entries = json.loads(man.read_text(encoding="utf-8"))`, add:

   ```python
   if target == "scripts/check-vocabulary-collisions.py":
       EXPECTED_MUTATIONS[target] = len(entries)
   ```

   Delete the last entry from `scripts/mutations/check-vocabulary-collisions.json`.

   **Measured:**

   - Initial `own_pin_problems()`: `[]`; displayed and held pin both **5**.
   - After loading: held pin **4**, loader problems `[]`, `pin_drift(...) == []`.
   - Modified checker self-test: **279/279 passed**, rc 0.
   - Real `--mutate ... --only scripts/check-vocabulary-collisions.py`: **4 killed, 4 attributed, zero survivors**, rc 0.
   - In a temporary real Git repository, production `gather` → `pin_pair` → `hold_reasons`: **`[]`**.

   This is an ordinary helper edit that could arise from deriving counts during loading. It changes neither assertion nor comparison. The documented exclusion technically covers it, but equating every post-assertion write with rewriting the checker’s assertions makes the claimed protection too broad. The assertions establish an initial value, not the value subsequently consumed.

2. **High — Importing the working-tree checker can terminate merge-ready successfully before its verdict.**  
   **Locations:** `scripts/check-merge-ready.py:865–873`, `:889`, `:1156`.  
   **Fix-induced:** yes, r3 introduces this in-process import.

   Append to `check-plan-code.py`:

   ```python
   if __name__ != "__main__":
       raise SystemExit(0)
   ```

   `_pins_reader()` executes that module as `_cpc_for_merge_ready`. `SystemExit` escapes `except Exception`, terminating merge-ready with **rc 0**, without HOLD or CANNOT RUN.

   **Measured through production `main()`**, with mocked external commands and diff collection but the real sibling import: Git supplied base pin **5**, head pin **4**; the process exited **0** after printing green prerequisite checks, without a final verdict.

   Therefore “executing nothing” is false: revision blobs are parsed, but the **working-tree** checker executes. This also makes the reader dependent on uncommitted code. The removed subprocess boundary previously allowed the caller to reject an empty or unsuccessful answer.

Additional checks:

- Foreground baselines passed: **279/279** plan-code; **227/227** merge-ready.
- `_suite_owns_the_pins()` is a context manager, not an environment/argv predicate. Explicitly entering and retaining it suppresses mismatches; exiting restores checking. That requires invoking the bypass and rebinding checker state, so I do not count it separately.
- Annotated displays work. Sole assignments inside `if`/`try`, tuple targets, and walruses are refused. Runtime `if` and `globals()` writes accompanying a valid display are detected before execution proceeds.
- No earlier pin snapshot or separate shard dictionary found.
- A real Git rename produced **81 removal HOLDs**. Missing shallow history failed closed. Moving the sole display elsewhere leaves no accepted display.
- No leaked copy processes observed. `_PINS_COPY` prevents recursive copies; timeout cleanup kills the process group. Heavy-load flakiness was not established.
- Worktree unchanged; no `.claude/plans/` files accessed.

**NOT CONVERGED**
