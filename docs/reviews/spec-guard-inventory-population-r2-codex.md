# Spec review — guard inventory population — round 2 — Codex half

**Subject:** `docs/superpowers/specs/2026-09-02-guard-inventory-population-design.md` **v2**,
branch `fix/guard-inventory-population`. **Scoped to round 1's own fixes.**
**Date:** 2026-09-02. **Backlog:** #72, #73.

**Provenance.** `scripts/codex-review.py --prompt-file`. `gpt-5.6-sol`, `-terra` and `-luna` each
returned HTTP 400; the wrapper fell through to **`gpt-5.5`** and captured a 2,798-character final
message. Verdict: `docs/reviews/verdicts/r2-codex.verdict.json`, `gate_ran=true`.

**VERDICT: NOT CONVERGED** — 1 Blocking, 2 High, 1 Medium, 1 Low.

> **The scoping paid.** Round 2 was aimed at round 1's own fixes on the measured expectation that a
> fix is where the next defect lives. The Blocking is a defect **in round 1's fix**, and the Claude
> half found the same class independently (its H2).

---

## Blocking — the flush-left grammar still excludes an indented example, because dedenting flattens it

§3.1's measurement table claims `(?m)^NOT-A-GUARD:` leaves an indented example IN. **That is true only
when the example is indented *relative to other body text*.** When the docstring body shares the
example's indentation — the common case for a uniformly-indented docstring — `ast.get_docstring`'s
`cleandoc` strips the common prefix and the example lands at column zero.

**CONFIRMED by the author, executed:**

| Docstring | cleaned value | v2 grammar |
|---|---|---|
| example indented under prose *(what §3.1 tested)* | `'…\n\nExample::\n\n    NOT-A-GUARD: a page generator'` | IN ✅ |
| **whole body shares the example's indent** | `'The contract.\nExample::\nNOT-A-GUARD: sample value'` | **EXCLUDED ❌** |
| example written flush in the body | same as above | **EXCLUDED ❌** |

⚠ **The author's §3.1 measurement had the same corpus defect §4.3 criticises in v1** — the "indented
example" dimension was enumerated from **one instance** rather than from the rule. Third instance of
that error in this slice.

**Consequence for the design, not just the table:** no text-position rule can work. After `cleandoc`,
a declaration and a demonstration of a declaration can be **byte-identical**. Tightening the regex
again would be the fourth attempt at a rule the input cannot support.

**Resolution adopted for v3 (measured, 8 cases):** the declaration becomes a module-level assignment
read via AST —

```python
NOT_A_GUARD = "a page generator; its product is an artefact"
```

Correct on all eight probes: genuine declaration EXCLUDED; docstring documenting the rule, example at
**any** indentation, a comment, an assignment nested in a function, an empty reason, a non-string
value, and an unparseable file all stay **IN**. Prose cannot forge an AST node.

⚠ **This also retires §3.2.** `NO_CALLER_RE` remains text-based and carries the identical latent hole:
a docstring example showing `NO-CALLER: <reason>` would opt a guard out of R3. Measured: zero of 26
guards carry such a declaration and none has such an example, so nothing is broken today — but it is a
real defect in existing code, surfaced by this work.

---

## High — F8 is unsatisfiable by construction

F8 requires `grep -rn discover_ratchets scripts/ .github/ .claude/ docs/` to return nothing. **It
cannot**: legitimate historical text under `docs/` contains the token, including
`docs/reviews/architecture-review-2026-08-30.md:73` and F8's own row in this spec.

⚠ v1's F6 was too narrow (it could not see `docs/`); v2 widened it into a falsifier that can never
pass. **Both failures are the same mistake** — writing the grep before checking what it returns. v3
must scope it to *executable* sources plus the living process documents, and name the historical
exclusions explicitly.

## High — §5 claims a complete change surface that §10 then extends

§5 is titled *"The complete change surface"*; its outside-file list ends at the 16 declarations, the
§7 sites and the mutation manifests. §10 then requires adding a `# N cases` declaration **and** adding
`check-ratchet-contract.py` to `check-selftest-counts.POPULATION` (`:83-93`, which lacks it today).

⚠ **This is the same self-contradiction round 1 found in v1's §5, recurring in the section written to
fix it.** A "complete" claim that another section extends is worse than no claim.

## Medium — §7's "every site" is still incomplete

`scripts/check-test-counts.py:31-33` — *"This is a ratchet … discoverable by it (that script finds
ratchets by this very word, from two independent sources…)"* — a **live script docstring** stating the
deleted mechanism, absent from §7's nine rows. Tenth site.

## Low — §7 misquotes the CI row

The table presents `.github/workflows/ci.yml:212-215` and `:220-223` as two `glob("check-*.py")`
claims. Exact grep returns only `ci.yml:213`. The `page_chrome` step states the same *conclusion*
without the quoted mechanism. The row is right that both go false; its evidence is imprecise.

---

## Disposition

All five accepted; none disputed. Every one re-verified against the code by the author before
acceptance. Folding into v3 with the Claude half's findings.

Claude half: [`spec-guard-inventory-population-r2-claude.md`](spec-guard-inventory-population-r2-claude.md).
