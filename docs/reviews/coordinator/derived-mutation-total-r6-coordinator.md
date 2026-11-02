# Round 6 — `derived-mutation-total` (PR #455, backlog #359) — coordinator — NOT CONVERGED (Codex); F1 is a CLASS fix of exception formatting at the sibling boundary; ladder: r5's unit scored `continued`, next route REDESIGN

REVIEW GAP: claude — alternation. Round 6 alternates to the Codex half alone (rounds 2+ alternate, `review-method.md` → *Round topology*; backlog #339).

Codex half: `docs/reviews/codex/derived-mutation-total-r6-codex.md` (verdict `docs/reviews/verdicts/derived-mutation-total-r6-codex.verdict.json`), which reviewed `48fd9cb7`.

```yaml
round: 6
fixes_nontrivial: true
subject: derived-mutation-total
halves:
  codex: ran
  claude: gap
findings:
  - {id: F1, severity: High, aim: instrument, fix_induced: true, component: sibling-import, disposition: fixed}
```

**What Codex found.**
- **F1 (High):** the handlers at `check-merge-ready.py:487`, `:935` and `:1028-1029` interpolated `{exc}` OUTSIDE the
  protected `try`. That calls the `__str__` the sibling defined. Codex's `Broken` (`__str__` raises `SystemExit(0)`)
  raised by the dashboard import, by `exemption_reason`, or by `pin_display` left `main()` at **rc 0 with no verdict**
  on a pin falling 5 -> 4. The well-behaved control still gave HOLD rc 3.
- Codex marks it fix-induced for the dashboard wrappers; the pins-reader formatting existed at `0eec9d38`.
- Codex also checked and found nothing else: both in-process importers use `_import_sibling`; no sibling raise
  reaching a bare `except Exception` produced a pass value; a failed import is not cached; neither deletion
  gave an independent defect.

**F1: FIXED as a class.** ONE helper, `_describe(exc, text=True)`, touches no sibling code.
- The name is read from `type.__dict__["__name__"].__get__(type(exc))`, so a metaclass `__name__` property and an
  overridden `exc.__class__` are both skipped (`type.__getattribute__` would NOT do: it finds the metaclass property first).
- The message is `str(exc)` inside its own `try`, coerced to an exact `str`; anything that fails prints
  `<unprintable>`. Only `KeyboardInterrupt` passes through.
- **Every formatting site routed** (grep: `{exc`, `str(exc`, `repr(exc`, `%s`, `exc.args`, `__class__.__name__`, traceback):

| Site | Was | Now |
|---|---|---|
| `_import_sibling` | `{exc.__class__.__name__}: {exc}` | `_describe(exc)` |
| `pins_at` (pin_display call) | same | `_describe(exc)` |
| `granted_escapes` (exemption_reason call) | same | `_describe(exc)` |
| `main()`, escape cross-check NOT RUN | `exc.__class__.__name__` | `_describe(exc, text=False)` |
| `main()`, collection error CANNOT RUN | `{exc.__class__.__name__}: {exc}` | `_describe(exc)` |
| `main()`, NO-REVIEW matcher failed | `exc.__class__.__name__` | `_describe(exc, text=False)` |

  The remaining `{exc}` / `__class__` uses are all inside `--self-test` (lines in the suite body, catching the
  script's own `main()`), where the exception is the suite's own; none is on the production path. No `repr(exc`,
  `%s`, `exc.args` or traceback printing exists in the file.

**Red before green.** Three cases through the REAL `main()` on a pin falling 5 -> 4, each with Codex's `Broken`:
the dashboard import, `exemption_reason`, and the pins reader's `pin_display`. With the production edits reverted
the suite was **238/241**, the three red, each `got ('ESCAPED SystemExit(0)', False)`; with the helper it is
**241/241**. The adjacent negative ("a well-behaved COPY of the dashboard gate still HOLDS the fall, rc=3") stayed
green throughout. A fourth case probes `_describe` directly with an exception whose metaclass `__name__`,
`__class__` and `__str__` each exit; it expects `Evil: <unprintable>`.

**Mutation entry** (`check-merge-ready`, pin 91 -> 92): "`_describe` calls `str(exc)` unguarded" (the guard narrowed
to `ZeroDivisionError`) goes red via the dashboard-import `main()` case. One older entry's anchor
(`PinsUnreadable(f"...{exc.__class__.__name__}: {exc}")`) was re-bound to the helper call. Sweep:
`--mutate . --only scripts/check-merge-ready.py --allow-long-local` killed **92 of 92**, all 92 attributed to the case
each names, 0 survivors. A diagnostic slice; the full sweep runs in CI.

## HOLD triage (for the merge-time HOLD comment)

Codex re-confirmed the r5 triage: `failure_path_removals` against `origin/master` reports the same five
`check-merge-ready.py` lines and one `check-plan-code.py` line, and the actual pin comparison reports no falls. **The
same six lines are all FALSE HOLDs**, with the before/after as quoted in the r5 coordinator document.
This fold changes handler text only (`_describe` replaces the interpolation; each handler keeps its `code = 2`).

## Ladder (decision log)

- **r5's row is scored `continued`.** r6 F1 is its named failure observation: an input that RAISES in the sibling's
  import or call and leaves rc 0. The bet lost, on the formatting of the caught error rather than on the catch.
- **Next route: REDESIGN**, written before round 7: no error text is built from a sibling's exception by
  interpolation. The unit text was copied exactly. `check-decision-scheme` gave **rc 0**, WARNs only.
