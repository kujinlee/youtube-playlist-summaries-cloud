<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established.

## High

**H1 — The “exactly two bounds” claim is false: real exception names can disappear, and message text can still become a fabricated exception.**

At `scripts/check-plan-code.py:534–577,606–657`, real prepared-venv children demonstrate both directions:

```python
raise type("bad-name", (Exception,), {})("ROOT_MARKER")
```

CPython prints a genuine traceback, including frames and `bad-name: ROOT_MARKER`. `exception_headings` returns `[]`. Likewise, a class with `__module__ = "bad-module"` prints `bad-module.Err: ROOT_MARKER` and returns `[]`.

Python permits dynamically created exception classes whose printed names are not dotted identifiers. Therefore, `part.isidentifier()` does **not** accept exactly the right set. Through real `run_mutations`, adding 80 message continuation lines leaves **neither `bad-name` nor `ROOT_MARKER` anywhere in the report**.

Conversely:

```python
raise RuntimeError('real\n  File "fake", line 1\nValueError: MESSAGE_ONLY')
```

returns:

```python
[("RuntimeError: real", False), ("ValueError: MESSAGE_ONLY", False)]
```

Only `RuntimeError` was raised. Real `run_mutations` reports both as exceptions named by stderr. A frame-shaped message continuation defeats the frame-marker repair.

These behaviors predate this fold, but refute its newly stated bounds and validation claims. Document these additional limits; the existing bounds do not cover them.

**H2 — A fourth world reaches the newly exhaustive THREE-world diagnostic.**

At `scripts/check-plan-code.py:3025–3036`, I used a real child that executes a passing assertion, prints `1/1 passed`, then exits 1 during cleanup:

```python
def test_value():
    assert 1 == 1

test_value()
print("1/1 passed", flush=True)
import os
os._exit(1)
```

Its unmutated control passes. The cleanup mutation produces:

```text
caught=True, fails=[], attributed=False, measured=True
```

The diagnostic nevertheless says “THREE WORLDS PRODUCE THIS.”

This child reached its case, reported it correctly, and named no failure on stderr. **A failure after successful cases** is a fourth producer. Neither the exhaustive enumeration nor the claim that every entry for the file remains unattributable until its reporting is fixed follows from this observation.

## Medium

**M1 — #276’s corrected measurement still misclassifies three sites and includes test fixtures in its guard population.**

The amended `docs/backlog.md:291` publishes **11 unasserted / 15 asserted / 0 cannot-run**.

I exchanged the expressions at all **26 named sites**, in a full checkout with the prepared venv and TypeScript available. All 16 guards had green controls before and after. The observed split was **14 green / 12 nonzero**, with no cannot-run—not the published split.

Three sites explicitly called asserted remain green:

| Site | Control → exchanged → restored |
|---|---|
| `check-test-counts.py:204` | 27/27 → 27/27 → 27/27 |
| `check-paid-caller-arrival.py:444` | 32/32 → 32/32 → 32/32 |
| `check-paid-caller-arrival.py:446` | 32/32 → 32/32 → 32/32 |

There are also problems with interpreting the nonzero results as “asserted”:

- `check-ci-watched.py:234` crashes with `TypeError: 'NoneType' object is not subscriptable`. This establishes a kill, not an assertion distinguishing the message’s worlds.
- `check-banner-armed.py:1958` and `:1962` assign fixture text inside `_self_test`’s `_flush_scenario`. Exchanging those fixtures changes the constructed scenarios; their red results do not establish coverage of production message selection.

This finding concerns the filed row’s evidence and denominator, not merely #276 remaining open. Reclassify the measurements and exclude fixture mutations from claims about production message assertions.

## Low

**L1 — #276’s population arithmetic remains inconsistent.**

`docs/backlog.md:291` states **47 total sites**, **26 non-cosmetic sites**, and a further **25 cosmetic sites** excluded. The latter two sum to **51**, not 47. At least one figure or its stated relationship needs correction.

**L2 — The architecture correction retains a stale membership claim.**

`docs/reviews/architecture-review-2026-10-13.md:281–284` correctly identifies the two survivors as `mut.get("expect")` and `rec.get("dirty")`, explicitly excluding `gate_ran`.

At `:286–287`, it immediately says **“ONE OF THE TWO IS MIS-GRADED”** and identifies `gate_ran`. That site is no longer one of the two. Describe it as an excluded candidate.

## Checked and found SOUND

- **Counts independently reproduced:** self-test **291/291**; this manifest **147 entries**; loaded population and declared sum both **1549**; binding **1557 anchors / 1549 entries**.
- **Exactly five manifest entries changed**, structurally compared against the parent: in-file zero-based indices **135,143,144,145,146**; global shard positions **725,733,734,735,736**.
- All five `--shard0 K/1549` runs returned **1 killed / 1 attributed / 0 survivors**. Separate staged-suite runs confirmed their named expectations failed for the edited observations:

  | Shard | Red cases | Relevant behavior |
  |---|---:|---|
  | 725 | 4 | Empty/whitespace observation wording |
  | 733 | 2 | Enumeration and searched stream |
  | 734 | 1 | Third world’s description |
  | 735 | 6 | Exchanged empty/whitespace arms |
  | 736 | 3 | Whitespace description and character count |

  No ambient attribution established.
- **Empty/whitespace split:** newline-only stderr reports whitespace and **1 character**; three U+3000 spaces report **3 characters**. BOM and NUL correctly enter the non-whitespace branch. No wrong ternary arm established.
- **Producer count:** AST enumeration found **89 `[FAIL]` print sites**, all without `file=`; no `[FAIL]` `.write` emitter found.
- **Anonymous-exposure measurement:** exchanged LOCAL/PRODUCTION expressions at `:635` reproduced **74/74 → 74/74 → 74/74**. The assignment is at `:635`; `:631` is the branch header.
- Both `check-review-recorded` message exchanges failed their relevant cases, with **196/196** controls before and after.
- The architecture enumeration now adds to two, and its remaining-site count is one.
- `check-docs`, `check-arch-findings`, and `check-withdrawal` passed. These passes do not validate the findings above.

## CANNOT RUN

**Treat these as NOT RUN, not passes.**

- Full local `--mutate .` sweep: excluded under the supplied timeout constraint. Five scoped shards do not establish population-wide mutation coverage.
- Independent CI replay: NOT RUN; supplied CI results remain supplied evidence.
- The original uncommitted #276 finder is absent. Its exhaustive inventory and cosmetic classification could not be replayed. The **26 named-site experiments were completed**, but do not establish that the inventory contains every relevant site.

## Instruments

Prepared `.venv/bin/python` **3.12.9**, with `.venv/bin` first on mutation `PATH`; commit message read first; both round-12 reviews; committed subject and wider-range diffs; structural JSON comparison; production-function probes with real children; five population-stride shards; isolated staged red-set measurements; a full temporary checkout for 26 expression exchanges with 16 before/after controls; AST enumeration; three documentation gates.

Reviewed HEAD `d56a00ae`. Repository remained clean. **No review file written.**
