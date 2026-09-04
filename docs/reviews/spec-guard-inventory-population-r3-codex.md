# Spec review — guard inventory population — round 3 — Codex half

**Subject:** `2026-09-02-guard-inventory-population-design.md` **v3** (`abb4c2b5`), branch
`fix/guard-inventory-population`. **Scoped to v3's own new material.**
**Date:** 2026-09-02. **Backlog:** #72, #73.

**Provenance.** `scripts/codex-review.py --prompt-file`; `-sol`/`-terra`/`-luna` HTTP 400, fell
through to **`gpt-5.5`**; 4,606-char final message. `verdicts/r3-codex.verdict.json`, `gate_ran=true`.

**VERDICT: NOT CONVERGED** — **0 Blocking**, 3 High, 1 Medium, 1 Low.

> First round with no Blocking. ⚠ **A decaying severity curve from ONE half is not convergence** —
> this repo has a memory saying exactly that. The Claude half decides the round.

---

## High — F8 is *still* unsatisfiable, for the third distinct reason

`grep -rn discover_ratchets scripts/ …` recurses into `scripts/__pycache__/`, and compiled `.pyc`
files contain the old symbol.

```
scripts/page_markup.py:45:(`discover_ratchets:67` …
Binary file scripts/__pycache__/page_markup.cpython-314.pyc matches
Binary file scripts/__pycache__/check-ratchet-contract.cpython-314.pyc matches
```

⚠ **This falsifier has now been wrong three times in three versions**, each time for a different
reason: v1's F6 was too narrow to see `docs/`; v2 widened it into a grep that historical text makes
unsatisfiable; v3 scoped the docs and left `__pycache__`. **One cause: the grep was authored, not
run.** v4 must fix the *practice* — every falsifier containing a shell command is executed against
the real tree before it is written down — not just this line.

## High — F5 and F6 do not distinguish v1/v2 from v3

Both are phrased against the new `NOT_A_GUARD = …` spelling, so their probes stay IN under the old
docstring grammar too.

```
probe                                    v1_excludes  v2_excludes
F5 nested NOT_A_GUARD assignment            False        False
F5 empty NOT_A_GUARD assignment             False        False
F6 doc documents new AST rule               False        False
F6 doc demonstrates new AST rule            False        False
control old marker flush-left               True         True
```

They catch a bad implementation of v3 but would not catch a **reversion to text matching** — the
failure mode two rounds were spent eliminating. ⚠ **Accepted with a narrowing:** a falsifier's job is
to catch a bad implementation of the current spec, not to re-litigate history. What is genuinely
missing is a probe asserting that a **docstring containing the old `NOT-A-GUARD:` marker leaves the
file IN**, which is what a reversion would break. v4 adds that as F6b.

## High — §7 omits a living site, and it is the guard that gates this review process

`scripts/check-review-rounds.py:46-48`:

> *"⚠ IT IS A RATCHET, and `check-ratchet-contract.py` discovers ratchets two ways: a CI step, or the
> word "ratchet" in this docstring. … **Both are now true.**"*

The change makes that false. §7's job is precisely this class, and the omitted file is the guard that
enforces review-round completeness — including for this round.

## Medium — §3.2 leaves real declaration shapes undecided

*"Module-level assignment … Nothing else counts"* does not settle `AnnAssign`, `Final[str]`, implicit
concatenation, or rebinding.

```
case              Assign-only   Assign+AnnAssign
exact                 True            True
annotated str        False            True
Final                False            True
implicit concat       True            True
rebind empty          True            True
```

**Independently measured by the author before this review landed**, with the same result and one
addition: this repo is typed throughout, so `NOT_A_GUARD: Final[str] = "…"` is the shape an
implementer would naturally write, and it silently does not declare. Fails **closed** (file stays IN,
CI red), so no false green — but it is a trap. v4 decides explicitly.

## Low — §7 says "Ten" over eleven rows: the FIFTH instance of the corpus error

Counted: 11 data rows; prose says *"Ten."* (`:298`). Confirmed by the author —
`grep -c '^| \`'` over §7 returns **11**.

⚠ **§12 claims the error occurred four times. This is the fifth, inside the section documenting it**,
and the `check-review-rounds.py` miss above makes the true site count **twelve**. v4 stops printing a
literal and derives the count, or drops it.

---

## Disposition

All five accepted; none disputed; all re-verified by the author. Folding into v4 with the Claude half.
