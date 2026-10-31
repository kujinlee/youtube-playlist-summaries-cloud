# Round 7 — `derived-mutation-total` (PR #455, backlog #359) — coordinator — NOT CONVERGED (Claude); F1-F3 are ONE class, fixed by ONE rule at ONE boundary; ladder: r6's REDESIGN scored `continued`, next route SPLIT with the stop pre-committed

REVIEW GAP: codex — alternation. Round 7 alternates to the Claude half alone (rounds 2+ alternate, `review-method.md` → *Round topology*; backlog #339).

Claude half: `docs/reviews/claude/derived-mutation-total-r7-claude.md`, which reviewed `68acb982`.

```yaml
round: 7
fixes_nontrivial: true
subject: derived-mutation-total
halves:
  codex: gap
  claude: ran
findings:
  - {id: F1, severity: High, aim: instrument, fix_induced: true, component: sibling-import, disposition: fixed}
  - {id: F2, severity: High, aim: instrument, fix_induced: false, component: sibling-import, disposition: fixed}
  - {id: F3, severity: High, aim: instrument, fix_induced: false, component: sibling-import, disposition: fixed}
  - {id: F4, severity: Info, aim: instrument, fix_induced: false, component: sibling-import, disposition: fixed}
  - {id: F5, severity: Info, aim: instrument, fix_induced: false, component: sibling-import, disposition: declined}
```

**What Claude found.** Each High is a value or exception the sibling hands back, which leaves the guarded `try`
and has a dunder called later, outside any boundary. On a pin falling 5 -> 4, each left `main()` at **rc 0 with no
verdict**.
- **F1 (fix-induced):** `_describe` read the class name through `type`'s descriptor, but `type.__name__`'s setter
  stores a str SUBCLASS as-is, and its `__format__` ran in the f-string (dashboard import, P12; the `text=False`
  site under a refusing gate, P13).
- **F2:** `pins_at` returned `pin_display`'s object as-is, and `pin_falls` ran a dict subclass's
  `__iter__`/`__contains__` (P1, P8) and an int subclass's `__lt__`/`__format__` (P2, P4). Ordinary edits, returning
  `None` or a list of pairs (P5, P6), crashed with a `TypeError` at rc 1.
- **F3:** `escape_diagnosis` truth-tested `exemption_reason`'s value; a `__bool__` that exits turned NOT READY into
  rc 0 (P11).
- **F4, F5 (Info):** a wrong but well-typed answer is trusted (F4: the bound now says so, as the reviewer suggested, so `fixed`); a forged `KeyboardInterrupt` escapes at rc 130, failing closed (F5: by design, `declined`, and the bound names it).

**F1-F3: FIXED as ONE rule, not three patches.** r6's fix induced F1, the second fix-induced round in this unit,
so the route was a redesign of the boundary itself: **nothing a sibling returns or raises leaves the boundary until it
has been reduced to EXACT builtins.**
- **`_cross(call, *args, reduce, error)`** calls the sibling and applies `reduce` inside its own `try`. `reduce`
  checks with `type(x) is …`, never `isinstance`, and returns a fresh copy. Any `BaseException` except
  `KeyboardInterrupt`, whether raised by the sibling or by `reduce` refusing its answer, becomes `error(text)`,
  with the text from `_describe`.
- **`_exact_pins`**: an exact `dict`, exact `str` keys, exact `int` values (a `bool` is refused), copied as
  `{str.__str__(k): int.__int__(v)}`. **`_exact_reason`**: `None` or an exact `str`, copied.
- **`_describe`**: the name is `str.__str__(…)` inside its `try` (measured: `str.__str__` of a subclass returns an
  exact `str` and calls none of its code); the message already was.

| Routed call | Was | Now |
|---|---|---|
| `_import_sibling` (both importers) | its own `try` | `_cross(_load, …, reduce=lambda mod: mod)`; every attribute read on the module happens inside a later `_cross` |
| `pins_at` → `pin_display` | guarded call, raw return | `_cross(…, reduce=_exact_pins)` |
| `granted_escapes` → `exemption_reason` | guarded comprehension, raw values | `_cross(…, reduce=_exact_reason)`, per marker |

**Red before green.** Twelve new cases through the REAL `main()` on a pin falling 5 -> 4. Ten were red at
`68acb982` + cases:

| Probe | Red (before) | Green (after) |
|---|---|---|
| P1 dict `__iter__` exits | `ESCAPED SystemExit(0)` | rc 2 CANNOT RUN |
| P8 dict `__contains__` exits | `ESCAPED SystemExit(0)` | rc 2 |
| P2 int `__lt__` exits | `ESCAPED SystemExit(0)` | rc 2 |
| P4 int `__format__` exits | `ESCAPED SystemExit(0)` | rc 2 |
| P5 `None` | `ESCAPED TypeError` | rc 2 |
| P6 list of pairs | `ESCAPED TypeError` | rc 2 |
| bool values | rc 0 READY (fall hidden) | rc 2 |
| P11 `__bool__` exits, gate refusing | `ESCAPED SystemExit(0)` | rc 2 (cross-check NOT RUN, then the NO-REVIEW matcher CANNOT RUN) |
| P12 str-subclass `__name__`, import | `ESCAPED SystemExit(0)` | rc 2 |
| P13 same, `exemption_reason`, gate refusing | `ESCAPED SystemExit(0)` | rc 2 |

The two adjacent negatives were green throughout: a reader returning a PLAIN dict still HOLDs the fall (rc 3), and a
well-behaved gate under a refusal is NOT READY (rc 1). The existing NO-REVIEW case still HOLDs, so an exact-str
exemption is honoured. Suite: **253/253**.

**Mutation entries** (pin 92 -> 96): `_exact_pins` using `isinstance` (red via the bool case); `_exact_pins`
returning the original object (red via P1); `_exact_reason` accepting any value (red via P11); `_describe` leaving the
name uncoerced (red via P12). Three entries whose anchor was the per-call catch, now gone, are RE-BOUND: the
refused-display fail-open and the two RAW-call bypasses of `_cross`; the shared-catch entry now binds `_cross`'s one
`except`.

**The bound** (in `_cross`'s docstring and both pin blocks): F4, *a sibling returning a WRONG but well-typed answer is
trusted, as master trusts it*; F5, *a forged `KeyboardInterrupt` escapes at rc 130, which fails closed*.

## HOLD triage (for the merge-time HOLD comment)

This fold changes the boundary's shape: the `except BaseException` handlers in `pins_at`, `granted_escapes` and
`_import_sibling` are replaced by calls through `_cross`, whose own handler raises `error`. Those removed handler lines
are on a failure path and will read as removals; each is a MOVE into `_cross`, which raises on the same inputs and
more. The r5/r6 false HOLDs stand as quoted there.

## Ladder (decision log)

- **r6's REDESIGN row is scored `continued`.** r7 F1-F3 are its named failure observation: sibling-controlled code
  running outside a fail-closed boundary (a formatting, a comparison, a truth test).
- **Next route: SPLIT** (a second `redesign` is a RETRY, which `check-decision-scheme` refuses by name). The
  exact-builtin boundary is held as is.
- **⛔ THE STOP FOR ROUND 8, PRE-COMMITTED HERE:** a finding that needs a sibling to DELIBERATELY construct hostile
  objects or exceptions beyond what `_cross` reduces is IN THE BOUND, so it is recorded, not fixed. Only an
  ORDINARY-edit finding (a changed return shape, a renamed function, an ordinary raise), or a value that crosses
  `_cross` unreduced, gets fixed. Named failure observation: such an input, or a sibling call that bypasses `_cross`;
  the route is then DEFER. The unit text was copied exactly; `check-decision-scheme` gave **rc 0**, WARNs only.
