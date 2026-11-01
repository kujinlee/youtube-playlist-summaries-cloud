# Round 5 — `derived-mutation-total` (PR #455, backlog #359) — coordinator — NOT CONVERGED (Claude); F1 is a CLASS fix at both in-process importers, F2 and F3 folded; ladder: the DEFER unit is CLOSED and r5 F1 opens its own unit

REVIEW GAP: codex — alternation. Round 5 alternates to the Claude half alone (rounds 2+ alternate, `review-method.md` → *Round topology*; backlog #339).

Claude half: `docs/reviews/claude/derived-mutation-total-r5-claude.md`, which reviewed `0eec9d38`.

```yaml
round: 5
fixes_nontrivial: true
subject: derived-mutation-total
halves:
  codex: gap
  claude: ran
findings:
  - {id: F1, severity: High, aim: instrument, fix_induced: false, component: sibling-import, disposition: fixed}
  - {id: F2, severity: Low, aim: instrument, fix_induced: true, component: sibling-import, disposition: fixed}
  - {id: F3, severity: Info, aim: instrument, fix_induced: true, component: sibling-import, disposition: fixed}
```

**What Claude found.**
- **F1 (High, pre-existing on master):** r4 fixed fail-open at ONE in-process importer, `_pins_reader`. The sibling
  importer `_dashboard_gate` had the same hole. Appending Codex's r4 input (`if __name__ != "__main__": raise
  SystemExit(0)`) to `check-dashboard-entry.py` left `main()` at **rc 0 with no verdict** on a head whose pin falls
  5 -> 4. That is an instance-not-class fix, and it is the DEFER row's named failure observation.
- **F2 (Low):** the bound text did not say that non-raising sabotage is out of scope.
- **F3 (Info):** the `sys.modules.pop` and the `mod.pin_display` probe in `_pins_reader` were unwitnessed and
  unobservable. Deleting either left the suite at 234/234.

**F1: FIXED as a class.** Design: **one helper, `_import_sibling(src, name, error)`, used by both importers.**
- It wraps the spec, the `module_from_spec`, the `sys.modules` registration and `exec_module`. It catches
  `BaseException`, re-raises only `KeyboardInterrupt`, and raises `error`.
  - `_pins_reader` passes `PinsUnreadable`.
  - `_dashboard_gate` uses the default, the new `SiblingUnusable(Exception)`.
  - `main()`'s existing `except Exception` handlers turn either one into CANNOT RUN, rc 2. At `:1141` the escape
    cross-check instead prints "NOT RUN" and leaves the gate verdicts standing.
- **The CALL is wrapped too.** `granted_escapes` catches the `exemption_reason` call the way `pins_at` catches
  `pin_display`, and raises `SiblingUnusable`.
- **`DASHBOARD_GATE` is now a module global**, like `PINS_READER`, so a case can point it at a copy.
  `_dashboard_gate` takes the path, under `lru_cache(maxsize=4)`.
- **Every in-process importer, enumerated.** The grep covered `importlib`, `spec_from_file_location`,
  `exec_module`, `exec(`, `runpy`, `__import__` and `import_module`. It found exactly two sites, the two above, and
  both now go through the helper. Every other sibling is run as a subprocess.

**F3: DELETED, not witnessed.** The helper did not make either line observable.
- The probe is redundant, because `pins_at` catches the later `AttributeError`.
- The pop is unobservable, because `lru_cache` does not cache a raised call.
- `_pins_reader` is now one line through the helper. "A reader with no `pin_display`" is still CANNOT RUN, at the
  call, and its case still passes.

**F2: FIXED.** One sentence was added in three places:
- `_import_sibling`'s docstring, as a BOUND;
- the *THE MUTATION PINS, BY THEIR DISPLAY* block in `check-merge-ready.py`;
- the *THE PINS ARE THEIR DISPLAY* block in `check-plan-code.py`.

The sentence: code that ends the process WITHOUT raising (`os._exit`, an `atexit`/thread/signal hook), or that
rebinds merge-ready's globals, is not caught. The same goes for a side effect that survives a caught raise. The
reason given is that this script extends the same trust to its own source, which the same PR can edit.

**Red before green.**
- **In the suite.** The cases were added on a tree that had only the `DASHBOARD_GATE` parameterisation and no
  catch. The result was **235/237**, with two red:
  - `⭐ main() is CANNOT RUN, rc=2, when importing the dashboard gate raises SystemExit (r5 Claude F1)`: got
    `('ESCAPED SystemExit(0)', False)`;
  - `⭐ ...and when the gate's exemption_reason itself raises SystemExit`: got `('ESCAPED SystemExit(0)', False)`.
  - The adjacent negative stayed green: "a well-behaved COPY of the dashboard gate still HOLDS the fall, rc=3".
  - With the helper, the result is **237/237**.
- **In a real process.** The reviewer's `scratchpad/r5/driver.py` drove the real `main()` over a `git archive` of
  each tree, with a pin falling 5 -> 4:

| tree | `check-dashboard-entry.py` | process rc | verdict |
|---|---|---|---|
| `cc50838d` (before) | unmodified | 3 | HOLD |
| `cc50838d` (before) | Codex's append | **0** | *(none)* |
| fold (after) | unmodified | 3 | HOLD |
| fold (after) | Codex's append | **2** | CANNOT RUN — the NO-REVIEW matcher failed (SiblingUnusable) |

**Mutation entries** (`check-merge-ready`, pin 89 -> 91).
- **Rebound:** r4's "the reader's import catches only Exception". Its anchor (`sys.modules.pop`) was deleted with
  F3. It now narrows the HELPER's catch, and it names TWO cases that must both go red: the pins reader's case and
  the dashboard gate's `main()` case. That witnesses that the helper is shared.
- **New:** "the dashboard gate imports its sibling RAW, bypassing the fail-closed helper". It goes red via the
  dashboard `main()` case.
- **New:** "the dashboard gate's exemption_reason CALL catches only Exception". It goes red via the
  `exemption_reason` case.
- **Sweep:** `--mutate . --only scripts/check-merge-ready.py --allow-long-local` killed **91 of 91**, all 91
  attributed to the case each names, with 0 survivors. This is a diagnostic slice; the full sweep runs in CI.

## HOLD triage (for the merge-time HOLD comment)

r5 Claude ran `check-merge-ready`'s own `failure_path_removals` over `origin/master...HEAD`. It flagged five lines
in `check-merge-ready.py` and one in `check-plan-code.py`. It found no falling pin. **Both "loosens a gate" lines
are FALSE HOLDs**, and each before/after is quoted in the review's *HOLD triage* section:

1. **`check-merge-ready.py` — the CANNOT RUN message.**
   - Before: `could not read the branch's diff (...)`.
   - After: `could not read the branch's diff or its mutation pins (...)`.
   - Still `code = 2`. The guarded `try` now also covers `pin_pair`, so the path covers MORE.
2. **`check-merge-ready.py` — two `hold_reasons(...)` cases.**
   - Each now passes `pins=({}, {})`, because `pins` became a required keyword.
   - The expected values are unchanged.
3. **`check-merge-ready.py` — two removal cases.**
   - Before: they drove the retired diff-line proxy `H(...)`.
   - After: they drive the pure rule `pin_falls(...)`, with the same expected strings.
   - The wiring is still witnessed by the `main()` falling-pin case, by the no-`check-plan-code.py` removal case,
     and by the `is removed` mutation entry.
4. **`check-plan-code.py` — one case.**
   - Before: `_evT.files["scripts/thing.py"]["tail"]`.
   - After: `.get("scripts/thing.py", {}).get("tail", "")`.
   - The expected value is unchanged. A missing key used to crash the suite; it now fails as a NAMED red case,
     which is stronger.

**Re-measured after this fold**, with `failure_path_removals` over `git diff -U<FAIL_WINDOW> origin/master` of
`scripts/`. It flags the **same six lines** (5 in `check-merge-ready.py`, 1 in `check-plan-code.py`), so the fold
adds none against master.
- Measured against the r4 head instead, the fold flags 6 lines. They are `_pins_reader`'s old catch body: it moved
  into `_import_sibling`, and the F3 probe and pop were deleted.
- `_pins_reader` itself was added by this branch, so those lines never existed on master, and the HOLD compares
  against master.

## Ladder (decision log)

- **The DEFER row is scored `continued`.** Its observed field is r5 F1, which is exactly its named failure
  observation: "no input ends check-merge-ready without a verdict or with rc 0 on a falling display pin". **The
  bet lost.**
- **No route follows DEFER on the same unit**, and the tool refuses one. With the row scored and left open,
  `check-decision-scheme` gave **rc 1: trigger 2 NON-TERMINATION**.
- **The unit was closed instead.** The DEFER row now records `rounds_at_termination: 5`. Trigger 11 WARNs: set down,
  not repaired. The unit's remaining finding, the witness at the point of consumption, is backlog #431.
  - ⚠ **That is earlier than the tool's guidance**, which is to close a unit only at the subject's final round.
    Round 6 (Codex) follows. If r6 finds something more in the falling-pin unit, it cannot be logged against that
    unit; it becomes a new one.
- **r5 F1 is its own unit's first bet:** "check-merge-ready's in-process sibling imports fail closed", route
  `accrete`, written before round 6.
  - The bet: no input that RAISES in either sibling's import or call leaves rc 0, or leaves no verdict, on a falling
    display pin; and a well-behaved sibling draws no false CANNOT RUN.
  - Named failure observation: any such input, or a third importer that bypasses the helper.
  - Trigger 12 WARNs (LADDER RESTARTED) and asks whether this is separate work. It is: a different component, the
    import boundary, not the pin witness.
- `check-decision-scheme` gave **rc 0**, with WARNs only.
