# Round 2 — `derived-mutation-total` (PR #455, backlog #359) — coordinator — NOT CONVERGED (Codex); REDESIGN (the effective pins, not their text)

REVIEW GAP: claude — round 2 alternates to the Codex half alone (rounds 2+ alternate, `review-method.md` → *Round topology*; backlog #339).

Codex half: `docs/reviews/codex/derived-mutation-total-r2-codex.md`, which reviewed `bf7782a8`.

```yaml
round: 2
fixes_nontrivial: true
subject: derived-mutation-total
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: High, aim: instrument, fix_induced: true, component: pin-shape, disposition: fixed}
  - {id: X2, severity: High, aim: instrument, fix_induced: true, component: pin-shape, disposition: fixed}
  - {id: X3, severity: High, aim: instrument, fix_induced: true, component: pin-shape, disposition: fixed}
  - {id: X4, severity: Medium, aim: instrument, fix_induced: true, component: total-scan, disposition: fixed}
```

**What Codex found.** Each input lowers an effective pin while `pin_shape_problems` returns `[]` and the production
`hold_reasons` returns `[]`. Each was reproduced against the real source.
- **X1:** a write in a DEFAULT ARGUMENT of `_self_test_body`, or in a DECORATOR on it. Both run at import, and the
  shape check exempted that function's whole AST.
- **X2:** a real `5 -> 4` beside a string literal that holds the old pin line. `PIN_LINE` read the string's line, so
  the diff's `new` map kept `5`.
- **X3:** a locally shadowed `dict(EXPECTED_MUTATIONS)` that writes. The read-only allowlist trusted the SPELLING.
- **X4:** the typed-total scan hit `timeout(2986)`, and missed arithmetic, an f-string and a name.

**THRASHING HAS ARMED.** The arming condition is two consecutive rounds whose findings came from the previous round's
own fix, in one component. That holds here, per finding:
- **r1 X1, M1** (component `pin-shape`) were caused by r0's retirement of the typed total. Its only backstop was then
  `PIN_LINE`, a rule over the diff's text.
- **r2 X1, X2, X3** (component `pin-shape`) are each in `pin_shape_problems`, which the r1 fold BUILT to fix r1 X1/M1:
  - X1 walks around its `_self_test_body` exemption;
  - X2 walks around the `PIN_LINE` completeness it was written to guarantee;
  - X3 walks around its read-only allowlist.
- **r2 X4** (component `total-scan`) is in `typed_total_sites`, which the r1 fold built to fix r1 X2/L1. It is a second
  component with the same history, one round behind.

**Why patching cannot win.** `pin_shape_problems` tries to prove a RUNTIME value invariant (the dict Python ends up
with) by reading SOURCE text. Python has more ways to change a value than a deny-list of shapes has entries. `PIN_LINE`
in `check-merge-ready.py` has the same weakness, because it reads DIFF text. The base (master) did not have the
weakness: its typed total compared the EVALUATED sum at runtime against a literal whose change was HELD, so every one of
Codex's inputs went red there.

**Route: REDESIGN — compare EFFECTIVE values, not source text.**
- `check-plan-code.py --print-pins` prints `EXPECTED_MUTATIONS` as JSON, as this run holds it after import. It sits
  after every refusal in `main`, so it shares the prefix `--mutate` runs. It is refused beside `--mutate`.
- `check-merge-ready.py` replaces `PIN_LINE` with `pin_pair`:
  - it materialises `scripts/` at the merge base and at HEAD (`git archive` into a temporary directory);
  - it runs `--print-pins` in each;
  - `pin_falls` HOLDS any key whose value falls and any key removed.
  - A side that fails, times out, or prints non-JSON (or anything but `{path: int}`) is `PinsUnreadable`. `main()` makes
    that CANNOT RUN, never a pass.
  - ⚠ The BASE alone may predate the flag; argparse refuses it by an exact message. Its dict is then read by importing
    the module. The base is the reviewed, merged side. The head, the side under review, must answer `--print-pins` or
    the run is CANNOT RUN.
  - `hold_reasons` now takes `pins` as a REQUIRED keyword, so no caller can skip the comparison by omission.
- **The written-reason escape:** none existed. `PIN_LINE` HELD every fall unconditionally. The reason is written at the
  pin by convention, and the HOLD is what puts it in front of the owner. That is kept, and the code says so.
- **`PIN_LINE` had no other use** after `pin_shape_problems`, so it is deleted.
- **`pin_shape_problems` is deleted**, with `PINS_NAME`, `PIN_WRITER_SCOPE`, `PIN_READ_CALLS`, `PIN_READ_METHODS` and
  `_pin_read_only`. Its 8 cases and its 3 mutation entries are RETIRED WITH THEIR SUBJECT, recorded at the pin.
- **`typed_total_sites` is kept, as a CONVENTION guard.** A literal counts only inside a comparison, an `assert`, or a
  `case`/`check` call that also mentions `declared_total` or `EXPECTED_MUTATIONS`. That fixes `timeout(2986)`.
  Arithmetic, an f-string and a name still escape it, and that is now a stated BOUND asserted as a case. It is
  acceptable because a re-typed total no longer protects or loosens anything; it only brings the merge conflict back.

**Red before green.** The new merge-ready cases were run in a scratch copy whose `pin_pair` was replaced by the RETIRED
rule (`PIN_LINE` over a diff of the two sources).
- All seven HOLD inputs went red with `got []`: X1 default argument, X1 decorator, X2 string, X3 shadowed `dict`, r1's
  duplicate key, r1's `-= 4`, and a removed key.
- The four CANNOT RUN inputs went red: broken import, non-JSON, a non-int pin, and a head without the flag.
- The real-git case went red as well (`got []`).
- The adjacent negatives (unchanged, increased) stayed green under both rules.

On the branch, before `--print-pins` existed, the real-file case was red with `HEAD: … unrecognized arguments:
--print-pins`. The plan-code `--print-pins` cases were red, 262/265 (argparse refused the flag), and
`timeout(2986)` was red with `got [1, 2, 4]`. All are green after the change.

**Counts:**
- `check-merge-ready`: 209 → 230 cases; pin 84 → 87. Two entries were rebound to `pin_falls`, one `main()` anchor was
  rebound, and three were added: a non-JSON side failing open, the base-only fallback answering for the head, and
  `main()` never reading the pins.
- `check-plan-code`: 267 → 265 cases; pin 147 → 147. Three were retired; three were added: `--print-pins` printing a
  constant, `--print-pins` beside `--mutate` accepted, and the total scan's mention test dropped. The Compare entry was
  rebound.
- Derived total: 2986 → 2989.

**Sweeps** (`--mutate . --only <file> --allow-long-local`, diagnostic slices; the full sweep is CI's):
- `check-merge-ready.py`: 87 mutations, 87 killed, 87 attributed to the case each names, 0 survivors.
- `check-plan-code.py`: 147 mutations, 147 killed, 147 attributed to the case each names, 0 survivors.
