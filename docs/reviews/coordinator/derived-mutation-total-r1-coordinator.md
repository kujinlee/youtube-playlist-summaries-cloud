# Round 1 — `derived-mutation-total` (PR #455, backlog #359) — coordinator — NOT CONVERGED (both halves); ACCRETE

Codex half: `docs/reviews/codex/derived-mutation-total-r1-codex.md`. Claude half: `docs/reviews/claude/derived-mutation-total-r1-claude.md`. Both reviewed `9fad9a10`.

```yaml
round: 1
fixes_nontrivial: true
subject: derived-mutation-total
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: High, aim: instrument, fix_induced: true, component: pin-shape, disposition: fixed}
  - {id: X2, severity: Medium, aim: instrument, fix_induced: true, component: total-scan, disposition: fixed}
  - {id: M1, severity: Medium, aim: instrument, fix_induced: true, component: pin-shape, disposition: fixed}
  - {id: L1, severity: Low, aim: instrument, fix_induced: true, component: total-scan, disposition: fixed}
  - {id: L2, severity: Low, aim: instrument, fix_induced: true, component: pin-drift, disposition: fixed}
  - {id: L3, severity: Low, aim: instrument, fix_induced: true, component: pin-drift, disposition: fixed}
  - {id: L4, severity: Low, aim: instrument, fix_induced: true, component: pin-drift, disposition: fixed}
  - {id: L5, severity: Low, aim: instrument, fix_induced: false, component: narration, disposition: fixed}
```

**Both halves agree on the core, and it refutes the PR's central claim.** *"Every way coverage could shrink unnoticed
before is still caught"* is false. With the typed total gone, a falling pin is seen only by `check-merge-ready`'s
`PIN_LINE`, which is a rule over diff LINES. Two inputs lower a pin with no line it matches, and both stay green and READY:
- a duplicate key: Python keeps the LAST value (Codex X1, multi-line; Claude S1, single-line);
- a later `EXPECTED_MUTATIONS[k] -= 4` (Claude S2).

On the base, both forced an edit to the literal, and `PIN_TOTAL` then HELD it.

**What they found besides:**
- **X2 / L1:** the regex that refuses a typed total missed a trailing comma, `2_981`, `assert declared_total() == N` and `declared_total() == N, True`.
- **L2:** the case "pins that match … not even a total" could never be attributed, because its mutants crashed the suite earlier, at the `_evT.files[...]` read.
- **L3:** on a consistent tree, the on-disk per-file case cannot tell itself from a total-only comparison.
- **L4:** the `pin_drift` docstring said the totals line is LAST. `mutate_delivered` appends home-escape findings after it.
- **L5:** the old narration still said "THIS CASE caught it" and "this literal is the outside observer", above a case that is gone.

**Fold:**
- **X1 / M1: the FIX is SHAPE, and it makes PIN_LINE complete over this file.** `pin_shape_problems` (pure, `ast`) refuses each of the following:
  - anything but ONE module-level dict display;
  - a `**` spread;
  - a non-string key, a duplicate key, or a non-int value;
  - any pin whose line `PIN_LINE` does not read as exactly that key and that value. `PIN_LINE` is IMPORTED from `check-merge-ready`, not copied. A match on the key's line also puts the pair on one line.
  - any use of the name outside `_self_test_body` that is not on a read-only allowlist. This covers a write, a `del`, `.update`/`.pop`/`.setdefault`, `|=`, an alias, a rebinding, `global`, or an import.

  The BOUND is stated: dynamic access is not seen (`globals()`, `setattr`, another module).
  - Cases: S1, S2, a split pin, Codex's duplicate multi-line key, nine other write forms, and non-literal pins.
  - Adjacent negatives: the REAL file (`[]`), and a minimal display that the self-test's own writes touch (`[]`).
  - Red before green: both reviewers' edits were applied to the REAL dict in a scratch copy. Each went 265/267, red on `the pins in THIS file are one display…`.
- **X2 / L1:** `typed_total_sites` reads the int LITERAL equal to the derived total wherever it is compared, passed or asserted.
  - It covers all four reviewer spellings, plus a comparison outside any call.
  - Negative: `N + 1`, and the total as plain data.
  - Measured: no literal from 2800 to 3300 is hit in the real file.
  - The retired regex missed all five spellings (measured).
- **L2:** the read is now `.get(...)`, so the `if drift:` → `if True:` mutant gives a red case and not a `KeyError`. It goes red via the named case (235/267). An entry was added.
- **L3:** the case's comment names the synthetic "+1/-1 swap" case as the one that pins the per-file direction.
- **L4:** the docstring now says the totals line follows the per-file lines, and that home-escape findings may come after it.
- **L5:** a HISTORY note sits ABOVE the narration block, and the two sentences are rewritten in the past tense.
- **Mutation entries (+5):**
  - a duplicate key;
  - a write outside the display;
  - a pin line PIN_LINE cannot read;
  - the AST scan's Compare branch;
  - `if drift:` → `if True:`.

  Each is red via the case it names in a scratch copy. 2/2/2/1/32 cases were red, and the named case was always among them.
- **Sweep:** `--mutate . --only scripts/check-plan-code.py --allow-long-local` gave `147 mutation(s), 147 killed, 147
  attributed to the case each names, 0 survivor(s)`. That is a diagnostic slice. The full sweep is CI's.

**Counts:** check-plan-code 253 → 267 cases and 142 → 147 entries; check-merge-ready unchanged (209 cases, 84 entries);
derived total 2981 → 2986. **Route: ACCRETE** (round 1).
