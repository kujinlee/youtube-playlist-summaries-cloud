# Round 4 — `derived-mutation-total` (PR #455, backlog #359) — coordinator — NOT CONVERGED (Codex); F2's fail-open is fixed, F1 is DEFERRED to backlog #431 with its bound stated; ladder: DEFER

REVIEW GAP: claude — alternation. Round 4 alternates to the Codex half alone (rounds 2+ alternate, `review-method.md` → *Round topology*; backlog #339).

Codex half: `docs/reviews/codex/derived-mutation-total-r4-codex.md`, which reviewed `8db213ae` (verdict `docs/reviews/verdicts/derived-mutation-total-r4-codex.verdict.json`, `gate_ran: true`, model `gpt-6-astra`).

```yaml
round: 4
fixes_nontrivial: true
subject: derived-mutation-total
halves:
  codex: ran
  claude: gap
findings:
  - {id: F1, severity: High, aim: instrument, fix_induced: true, component: pin-witness, disposition: deferred}
  - {id: F2, severity: High, aim: instrument, fix_induced: true, component: pin-witness, disposition: fixed}
```

**What Codex found.**
- **F1 (High):** a write in the harness's own manifest loader lowers a pin after the entry assertion. The input:
  right after `entries = json.loads(man.read_text(encoding="utf-8"))`, add
  `if target == "scripts/check-vocabulary-collisions.py": EXPECTED_MUTATIONS[target] = len(entries)`, and delete the
  last entry of `scripts/mutations/check-vocabulary-collisions.json`. Codex measured that the display and the held pin
  were both 5 at entry and the held pin was 4 after loading. `--self-test` gave 279/279, `--mutate --only` killed 4 with
  0 survivors, and `hold_reasons` returned `[]`.
- **F2 (High, fix-induced by r3):** `check-merge-ready` imported the WORKING-TREE `check-plan-code.py` to get
  `pin_display`. Appending `if __name__ != "__main__": raise SystemExit(0)` to that file made `SystemExit` escape
  `main()`'s `except Exception`, so the process exited **rc 0** with no verdict, on a head whose pin fell 5 -> 4.

**Route taken for F1: DEFER, as the decision log pre-committed.** The r4 SPLIT row named this exact failure
observation: "any further gap between the display and the dict the harness uses; the route is then DEFER". No new
guard was added for F1.
- **Master measurement first.** F1's exact edit was applied to a scratch worktree of `origin/master` (`0de20abb`), and
  the last entry of `mutations/check-vocabulary-collisions.json` was deleted there.
  - `python3 scripts/check-plan-code.py --self-test`: **249/249 passed, rc 0**. (A first run was 246/249, because
    the scratch worktree had no `node_modules/typescript`. All three failures were HARNESS_TREE staging cases. With
    `node_modules` linked, all 249 passed. Neither run involved F1.)
  - `python3 scripts/check-plan-code.py --mutate . --only scripts/check-vocabulary-collisions.py --allow-long-local`:
    **rc 0**, "1 file(s), 4 mutation(s), 4 killed, 4 attributed to the case each names, 0 survivor(s)".
  - **Master is GREEN on F1 too.** Deferring F1 loses nothing master had, so this PR does not loosen a gate relative
    to master on this input.
- **The bound is now honest**, in `check-plan-code.py` (the *THE PINS ARE THEIR DISPLAY* block) and in
  `check-merge-ready.py` (the *THE MUTATION PINS, BY THEIR DISPLAY* block). The assertion fixes the INITIAL value, not
  the value later CONSUMED. A write in the harness's own code paths after it, such as a manifest loader or the mutate
  loop, is seen by neither the assertion nor the HOLD. r3's wording, which equated every such write with "rewriting the
  checker's assertions", is withdrawn. Codex was right that this claimed too much.
- **Filed as backlog #431:** "the falling-pin witness: assert that the mutation pins the harness CONSUMES equal its
  display at the point of consumption, not only at entry". It records F1's input, Codex's numbers and the master
  measurement above.

**Route taken for F2: FIXED, because it is a fail-open.** Design: **catch at the import, not a new module.**
- `_pins_reader(src)` wraps the spec, the `exec_module` and the `pin_display` attribute lookup. It catches
  `BaseException`, re-raises only `KeyboardInterrupt`, drops the half-built `sys.modules` entry, and raises
  `PinsUnreadable`. `main()` already turns `PinsUnreadable` into CANNOT RUN (rc 2).
- `pins_at` catches the reader CALL the same way, so a `pin_display` that raises `SystemExit` (or anything other than
  `PinDisplayError`) is also CANNOT RUN.
- `PINS_READER` is now a module global, so a case can point the reader at a copy.
- **Why not a shared side-effect-free module?** It would still be a working-tree file that merge-ready executes, so
  it moves the trust boundary without removing it. It would also need its own `--self-test`, a caller and a manifest
  under `check-ratchet-contract`. The property asked for is that any misbehaving import gives CANNOT RUN and never
  rc 0. Catching at the one call site gives that, and it is what the cases below measure.
- **Bound, stated:** a working-tree `pin_display` that returns plausible wrong numbers without raising is not caught.
  `check-merge-ready.py` is itself working-tree code, so that is the same trust it already extends to its own source.
  The display reader's own cases in `check-plan-code` are what guard it.

**Red before green (`check-merge-ready`).** The new cases were run against the r3 reader body (no catch, and
`except reader.PinDisplayError` only). Six were red at **228/234**:
- Codex's exact input (`SystemExit(0)` at module level): `got 'ESCAPED Sys'`.
- A module-level `ValueError`: `got 'ESCAPED Val'`.
- A MISSING reader: `got 'ESCAPED Fil'`.
- A reader with no `pin_display`: `got 'ESCAPED Att'`.
- A reader whose `pin_display` raises `SystemExit`: `got 'ESCAPED Sys'`.
- **Codex's exact input through the real `main()`**: `got ('ESCAPED SystemExit(0)', False, False) want (2, True, True)`.

The adjacent negative stayed green: a well-behaved COPY of the real reader still HOLDS the fall. With the change, all
cases pass: **234/234**.

**Counts:**
- `check-merge-ready`: 227 -> 234 cases. Pin 87 -> 89, with two entries added: the import's catch narrowed to
  `Exception`, and the call's catch narrowed to `Exception`. Each goes red via the case it names. One entry was
  REBOUND: "a display check-plan-code refuses reads as pinning nothing", whose `raise PinsUnreadable(...)` line
  changed text.
- `check-plan-code`: 279 -> 279 cases. Pin 149 -> 149. Comments only, plus the merge-ready pin.
- Derived total: 2991 -> 2993.

**Sweeps** (`--mutate . --only <file> --allow-long-local`; these are diagnostic slices, and the full sweep runs in CI):
- `check-merge-ready.py`: 89 mutations, 89 killed, 89 attributed to the case each names, 0 survivors.
- `check-plan-code.py`: 149 mutations, 149 killed, 149 attributed to the case each names, 0 survivors.

**Ladder (decision log).**
- The r4 SPLIT row is scored `continued`. Its observed field is r4's two Highs; F1 is the row's named failure observation.
- A DEFER row on the same unit ("mutation pins: the derived total and the HOLD on a falling pin (backlog #359)") is
  written BEFORE round 5. It bets that no input ends `check-merge-ready` with no verdict, or with rc 0 on a falling
  display pin, and that no unchanged or raised pin draws a false HOLD.
- `check-decision-scheme` gave rc 0.
- DEFER is the last rung, so no route follows it on this unit.
