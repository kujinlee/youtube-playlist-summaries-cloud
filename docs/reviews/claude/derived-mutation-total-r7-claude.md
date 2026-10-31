# Round 7 — `derived-mutation-total` (PR #455, backlog #359) — Claude adversarial half — NOT CONVERGED

Reviewed: head `68acb982`, diff `48fd9cb7..HEAD` (`_describe`, six routed sites, three `main()` cases + one probe
case, one mutation entry). Read first: `docs/reviews/coordinator/derived-mutation-total-r6-coordinator.md`,
`docs/reviews/codex/derived-mutation-total-r6-codex.md`.

**The bet to refute:** *"no error text is built from a sibling's exception by interpolation any more; nowhere does
sibling code run outside a fail-closed boundary."*

**Refuted, on both halves.** The first half fails inside `_describe` itself (F1, fix-induced). The second half
fails on the sibling's RETURN VALUES. `pins_at` and `granted_escapes` guard the CALL, then hand the sibling's
object to code outside any `try`, and that code calls its dunders (F2, F3).

## Method

I measured each finding through the REAL `main()`, using the suite's own fake `_run`, on a head whose pin
falls `scripts/a.py` 5 → 4. I ran a scratch copy of `scripts/` and `.github/`, with a probe block appended to
`_self_test_body` and reusing `_main`, `_gate_main`, `_fake` and `_syn`. The worktree is untouched. In the
table, `ESCAPED SystemExit(0)` means `main()` did not return. Under `sys.exit(main(...))` the process then
exits **rc 0 with no verdict**. I checked this separately: an escaping `SystemExit(0)` gives rc 0, and an
uncaught `KeyboardInterrupt` subclass gives rc 130.

| Probe | Input (sibling-side) | Result |
|---|---|---|
| P0 control | real `check-plan-code` reader | rc 3 HOLD |
| P1 | `pin_display` returns `dict` subclass, `__iter__` raises `SystemExit(0)` | **ESCAPED SystemExit(0)** |
| P8 | same, `__contains__` raises | **ESCAPED SystemExit(0)** |
| P2 | values are `int` subclass, `__lt__` raises | **ESCAPED SystemExit(0)** |
| P4 | values are `int` subclass, `__format__` raises | **ESCAPED SystemExit(0)** |
| P3 | values are `int` subclass, `__lt__` returns `False` | rc 0 READY (fall hidden) |
| P5 | `pin_display` returns `None` | ESCAPED TypeError (real rc 1, traceback) |
| P6 | `pin_display` returns `sorted(d.items())` | ESCAPED TypeError (real rc 1, traceback) |
| P7 | returned `dict` subclass, `__del__` raises `SystemExit(0)` | rc 3 HOLD (unraisable, ignored) |
| P16 | module `__class__` swapped, `__getattribute__` exits | rc 2 CANNOT RUN (inside the `try`) |
| P9 | `exemption_reason` returns object whose `__bool__` exits, gates green | rc 3 HOLD (`is not None` calls nothing) |
| P10 control | dashboard gate REFUSES (rc 1), real gate | rc 1 NOT READY |
| P11 | gate refuses + `exemption_reason` returns object whose `__bool__` exits | **ESCAPED SystemExit(0)**: NOT READY becomes rc 0 |
| P12 | dashboard import raises `Broken`, `Broken.__name__ = _S('Broken')`, `_S.__format__` exits | **ESCAPED SystemExit(0)** |
| P13 | gate refuses + `exemption_reason` raises that `Broken` (the `text=False` site) | **ESCAPED SystemExit(0)** |
| P14 | `pin_display` raises a `KeyboardInterrupt` subclass | escapes; real rc 130 |
| P15 | exception `__str__` raises `KeyboardInterrupt` | escapes; real rc 130 |

Results of calling `_describe` directly:
- A `__str__` returning a str subclass gives `'_E1: boom'`. The `str.__str__` coercion works.
- A non-str `__str__` gives `'_E2: <unprintable>'`.
- `BaseExceptionGroup([SystemExit(0), ValueError])` gives `'BaseExceptionGroup: g (2 sub-exceptions)'`.
- A **str-subclass `__name__` ESCAPES**. `type.__name__`'s setter stores the subclass as-is. I measured this
  directly: the stored type is `_S`.

## Findings

### F1: High, fix-induced. `_describe` formats the sibling's class NAME with sibling code
`scripts/check-merge-ready.py:478`, `:484`, `:491`. `type.__dict__["__name__"].__get__(type(exc))` skips a
metaclass property, but it returns whatever object was assigned to `__name__`. The setter accepts any str
subclass. The name then goes through `format()` in two places: `f"{name}: {msg}"` at `:491`, and the callers'
`f"(...{_describe(exc, text=False)})"` at `:1192` and `:1241`. Both run outside any guard.

**Input:**

```python
class _S(str):
    def __format__(self, spec): raise SystemExit(0)
class Broken(Exception): pass
Broken.__name__ = _S("Broken")
raise Broken("x")   # at import (P12) or from exemption_reason (P13)
```

This leaves `main()` at rc 0 with no verdict. It is the r6 F1 class, one attribute over. The docstring's claim
*"touching no sibling code"* is false for the name. The `msg` path already has the cure, `str.__str__(...)`
inside the `try`. The name never received it.

**Fix:** `name = str.__str__(type.__dict__["__name__"].__get__(type(exc)))` inside the existing `try`. Add a case
with this input through `main()`.

The direct probe case does not cover this. `Evil` uses a metaclass property, which the descriptor read already
skips. The name-side `except BaseException` has no mutation entry either: only the `msg` guard is mutated.

### F2: High, not fix-induced (introduced earlier in this PR with the in-process reader). `pin_display`'s return value is used unvalidated outside the boundary
`pins_at` (`:956`) returns `reader.pin_display(...)` as-is. `pin_falls` (`:974-978`) is reached from `main()` at
`:1245` with no `try`. It calls `__iter__` (`sorted(old)`), `__contains__` (`in new`), `__getitem__`, `__lt__`
and `__format__` on the sibling's objects.

**Input:** P1, P2, P4 or P8, for example `class _D(dict): __iter__ = lambda s: (_ for _ in ()).throw(SystemExit(0))`
returned from `pin_display`. Each one leaves rc 0 with no verdict on a 5 → 4 fall.

The ordinary-edit variant matters too. If `pin_display` is refactored to return `None` or a list of pairs
(P5, P6), `main()` crashes with a `TypeError` traceback at rc 1. That reads as NOT READY for the wrong reason,
where CANNOT RUN is the right answer. That variant is Low on its own, but the same fix closes it.

`check-plan-code` does not use `pins_at`; only merge-ready does. Nothing between the call and `pin_falls` copies
or checks the result: `pin_pair` returns the tuple directly.

**Fix:** validate inside `pins_at`'s `try` and copy into builtins. `type(d) is dict`, and every key/value with
`type(k) is str and type(v) is int`. Checks on exact `dict`/`str`/`int` call no Python-level code. Anything else
raises `PinsUnreadable`, which gives CANNOT RUN.

### F3: High, not fix-induced (the cross-check predates the PR; r5 extended the call guard but not to the value). `exemption_reason`'s return value is truth-tested outside the boundary
`escape_diagnosis` at `:1079` and `:1082` evaluates `granted.get(want)` and `granted.get(other)` for
truthiness. That calls the sibling value's `__bool__`, after `granted_escapes`' `try` has closed. The path only
runs when a gate REFUSED.

**Input:** P11. The dashboard gate exits 1, and `exemption_reason` returns an object whose `__bool__` raises
`SystemExit(0)`. A **NOT READY (rc 1) becomes rc 0 with no verdict**. This is worse than the pin case: the
input converts a refusal into the merge-ready exit code. The `main()` NO-REVIEW path is safe (P9), because
`is not None` calls nothing and `bool(nr)` is on a real bool.

**Fix:** inside `granted_escapes`' `try`, require each value to satisfy `v is None or type(v) is str`, else raise
`SiblingUnusable`.

### F4: Info, within the bound. A sibling that LIES
P3: the values compare as "not less", so the fall is hidden and the result is READY rc 0. Any reader whose
answer is trusted has this property. A PR can also simply edit `pin_display` to return fewer pins: that is the
same trust the script extends to its own source. F2's exact-`int` check removes the dunder channel. Returning
wrong plain ints remains possible, and that is inherent.

The bound in `_import_sibling`'s docstring lists `os._exit`, hooks, global rebinding and surviving side effects.
It does not name "a sibling returning a wrong answer". I suggest saying so in one clause, so the bound
enumerates what it does not witness. I am not filing it as a defect.

### F5: Info, by design. A forged `KeyboardInterrupt` escapes
P14 and P15: a sibling can raise a `KeyboardInterrupt` subclass, or have `__str__` raise one, and `_describe` /
the call guards re-raise it. The real exit code is 130, so this fails closed: it is not READY and not 0. The
docstring's stated choice, *"the operator stopping the run is not an answer"*, covers it. No action.

### Checked, nothing found
- **`__del__` on returned objects (P7):** exceptions in `__del__` go to the unraisable hook. The result was
  HOLD rc 3.
- **Exception chaining / `__traceback__`:** every conversion uses `from None`. No production path prints a
  traceback or reads `__context__`/`__cause__`. Dropping the caught exception frees sibling frames, which again
  only reaches `__del__` (see P7).
- **Module `__getattr__`/`__getattribute__` (P16):** the only attribute reads on the sibling module,
  `reader.pin_display` (`:956`) and `gate.exemption_reason` (`:1050`), are inside their `try`. The result was
  CANNOT RUN rc 2. `lru_cache` hashes the `Path`, not the module.
- **Six-site completeness:** I grepped the whole file for `{exc`, `exc.`, `__class__`, `str(exc`, `repr(` and
  `traceback`. The production sites are `:513`, `:960`, `:1054`, `:1192`, `:1233` and `:1241`, which is all six.
  The remaining `{exc}`/`__class__` uses (`:1756`, `:2017`, `:2075`, `:2163`, `:2176`, `:2195`, `:2227`,
  `:2259`) are inside `--self-test` and catch the suite's own calls. The list is complete, **but F1 shows a
  routed site is not yet a safe site.**
- **`BaseExceptionGroup`** is caught by `except BaseException` and described correctly. A group containing
  `KeyboardInterrupt` is not itself a `KeyboardInterrupt`, so it is converted rather than re-raised. That is
  consistent with failing closed.

## Bound question (item 5)
F1, F2 and F3 use only synchronous dunders on objects the sibling hands back. They need no `os._exit`, no hooks,
no rebinding of this script's globals, and no surviving side effect. The stated bound does not cover them, and
r6 Codex F1, a `__str__` that exits, was accepted on exactly this standard. They are in scope.

**The shared repair is one rule:** nothing the sibling returns or raises leaves a sibling `try` unless it has
been reduced to exact builtins: `str.__str__` for strings, and `type(x) is …` checks for containers and numbers.
The r6 redesign applied that rule to `msg` only.

## Gates run (foreground)
- `python3 scripts/check-merge-ready.py --self-test`: **241/241**, rc 0.
- `python3 scripts/check-plan-code.py --self-test`: **281/281**, rc 0.

**NOT CONVERGED.**
