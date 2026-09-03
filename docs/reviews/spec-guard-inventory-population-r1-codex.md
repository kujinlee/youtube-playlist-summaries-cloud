# Spec review — guard inventory population — round 1 — Codex half

**Subject:** `docs/superpowers/specs/2026-09-02-guard-inventory-population-design.md` v1, commit
`1b649324`, branch `fix/guard-inventory-population`.
**Date:** 2026-09-02. **Backlog:** #72, #73.

**Provenance.** Dispatched via `scripts/codex-review.py --prompt-file`, never a shell string.
`gpt-5.6-sol`, `gpt-5.6-terra` and `gpt-5.6-luna` each returned **HTTP 400**; the wrapper fell through
to **`gpt-5.5`** unaided and captured a 4,143-character final message.
Verdict file: `docs/reviews/verdicts/r1-codex.verdict.json`, `gate_ran=true`. The gate ran.

**VERDICT: NOT CONVERGED** — 1 Blocking, 2 High, 2 Medium.

---

## Adjudication

Every finding was re-checked against the code by the author before being accepted. This repo's record
is that a reviewer's finding is a **lead, not a verdict**. All five reproduced.

### Blocking — `evaluate` is declared unchanged but `discover_guards` now needs docstrings

Spec §5 says `discover_guards` "takes the script *texts*, not just paths", then §5's closing line lists
`evaluate` among the functions that are **untouched**. The live code is
`for rel in discover_guards(list(texts))` at `scripts/check-ratchet-contract.py:174`.

**CONFIRMED.** A path list carries no docstrings, so the opt-out rule is unreachable from the live
evaluation path unless `evaluate` changes. The fix is one token — pass `texts` rather than
`list(texts)` — but the spec as written is self-contradictory, and §5 is the section a plan would be
built from.

### High — the declaration grammar accepts quoted examples and code blocks

`NOT_A_GUARD_RE = re.compile(r"NOT-A-GUARD:[ \t]*(\S[^\n]*)")` matches anywhere in the docstring.

**CONFIRMED BY EXECUTION.** Six inputs, three wrong:

| Input | Result | Correct? |
|---|---|---|
| `NOT-A-GUARD: a page generator, not a gate.` | EXCLUDED | ✅ |
| `Guards opt out by writing "NOT-A-GUARD: <reason>" in the docstring.` | EXCLUDED, reason=`'<reason>" in the docstring.'` | ❌ |
| indented code block containing `NOT-A-GUARD: sample value` | EXCLUDED | ❌ |
| `NOT-A-GUARD:` with the reason on the next line | IN | ✅ (the `[ \t]` near-miss holding) |
| `This file is NOT A GUARD in any sense.` | IN | ✅ |
| `not-a-guard: lowercase attempt` | IN | ✅ (uncertain whether this is desirable) |

⚠ **Sharper instance the review did not state, found while verifying it.**
`check-ratchet-contract.py` must document its own `NOT-A-GUARD:` rule the way it documents
`NO-CALLER:` — and under this grammar **that documentation would remove the contract from its own
inventory**. Checked whether the existing `NO-CALLER:` already suffers this: it does not, because no
guard's module docstring happens to quote it (`NO_CALLER_RE` over all 26: zero matches). That is luck,
not design, and the new rule has higher stakes — `NO-CALLER:` skips one rule, `NOT-A-GUARD:` removes
the file entirely.

### High — `build-m4-schema.py` is classified OUT but behaves as a fail-closed guard

**CONFIRMED**, quoting the file: `FAILS IF` block at `scripts/build-m4-schema.py:31-34`;
`assert_end_state` errors raise at `:245`; `main()` returns `1` at `:381-385` and `2` for CANNOT RUN
at `:378-380` — the exact fail-closed discipline this project requires of a guard. It is also depended
on by a guard path: `scripts/gen-m4-manifest.py:193-197` runs it and raises if it fails.

⚠ **The finding is deeper than the one file, and this is the most important result of the round.**
Spec §4 sorts 19 files into "generators / library modules / tools / builders" and assigns 2 IN and
17 OUT — but **states no criterion**. §4.1 argues `codex-review.py` OUT on "it runs a gate rather than
being one", which is a criterion applied to exactly one file and never generalised. So the split was
assigned by feel, and `build-m4-schema.py` is where feel diverges from the code.

Consequence: the claimed post-change count of **28 is unearned**, and falsifier F2 ("count is exactly
28") would have locked in whatever number the unstated criterion happened to produce. The repair is
not to move one file — it is to state the criterion and **derive** all 19 verdicts from it.

### Medium — §5's change surface omits work §9 requires

**CONFIRMED.** §5 lists only `check-ratchet-contract.py` plus 17 docstring lines; §9 requires mutation
manifest entries and an `EXPECTED_MUTATIONS` rise. Additionally: `EXPECTED_MUTATIONS`
(`scripts/check-plan-code.py:457-497`) has **no `scripts/check-ratchet-contract.py` key at all**, so
this is a new entry rather than an increment — a fact neither §5 nor §9 records.

### Medium — §9's self-test-count claim is false

**CONFIRMED.** §9 says `check-selftest-counts.py` "ratchets the total, so its pinned count moves in
the same commit". Its `POPULATION` at `scripts/check-selftest-counts.py:83-93` pins exactly nine
scripts and **`check-ratchet-contract.py` is not among them**; the contract's usage block
(`:23-25`) declares `--self-test` without the canonical `# N cases` form. **Nothing ratchets that
count today.** The spec's warning against "correcting it toward a remembered number" was guarding a
mechanism that does not exist.

---

## Author self-review, recorded in the same round

**High — §5's change list misses every place the old population is stated as fact.** Found by the
author before Codex reported, while trying to falsify §5's "zero code repairs" claim. Four sites:

- `.github/workflows/ci.yml:212-215` — *"a library, not a guard, so `check-ratchet-contract.py`
  neither sees it nor should: **its population is `glob("check-*.py")`**"*, used to justify a CI step;
- the `page_chrome` step below it, repeating the reasoning;
- `scripts/page_markup.py:42`; `scripts/explainer-serve.py:70`;
- **`docs/dev-process.md:145`** — the process spine — which repeats *"the population is the
  FILESYSTEM"* **and** manually quotes `(--self-test: 21 cases)`.

Leaving these makes the repo assert a population the code no longer has: the exact defect this spec
exists to fix, reintroduced by the fix.

**Checked and found clean:** `scripts/check-guard-coverage.py` derives from `SCHEMA.glob("0*.sql")`
and a hand-maintained `GUARDS` dict about **schema** objects — a different population entirely, no
impact. `scripts/check-selftest-counts.py:163` already globs `scripts/*.py`, which is supporting
evidence for the widening rather than a conflict: a sibling gate already treats every script as the
population.

---

## Disposition

All five Codex findings and the author finding are **accepted**. None is disputed. Round 1 does not
converge; a v2 must state a guard criterion (High #3) before the 17/2 split and the count 28 mean
anything, and must fix the `evaluate` contradiction (Blocking) and the grammar (High #2).

The Claude half of this round is at
[`spec-guard-inventory-population-r1-claude.md`](spec-guard-inventory-population-r1-claude.md).
