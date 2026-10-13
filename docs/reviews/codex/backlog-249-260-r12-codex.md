<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established.

## High

**H1 — `exception_headings` invents headings and can still lose the real one.**  
At `scripts/check-plan-code.py:525–582`, real CPython stderr from:

```python
raise RuntimeError("real\n  continuation\nValueError: MESSAGE_ONLY")
```

produces:

```python
[("RuntimeError: real", False), ("ValueError: MESSAGE_ONLY", False)]
```

Only one exception was raised. The indented message continuation becomes a fictitious frame block. Ordinary stderr `"  connecting\nREADY\n"` likewise produces `[("READY", False)]`.

Conversely, a valid exception class named `Échec` produces **no heading**. Through real `run_mutations`, raising it with `ROOT_MARKER` followed by 60 continuation lines leaves **neither its type nor its marker anywhere in the report**. This reproduces the lost-heading harm the change claims to repair. Claims 2 and the diagnostic guarantee are refuted; distinguish frame structure from message indentation and cover Unicode identifiers.

**H2 — the empty-stderr message still asserts an unsupported cause.**  
At `scripts/check-plan-code.py:2883`, replacing the fixture’s executable statement with:

```python
import os
os._exit(1)
```

makes real `run_mutations` report:

> stderr is EMPTY, so the suite RAN and its PRINTER is the subject

No case ran and no printer malfunctioned. A child writing only whitespace before exiting 1 receives the same diagnosis. The mutation is correctly refused, but its explanation confidently identifies the wrong subject. Claim 3 is refuted. Report the observed absence of stderr without inferring suite execution or a printer defect.

**H3 — a fifth world remains falsely green: a traceback supplies the failure name.**  
Through real `run_mutations`, a fixture that immediately raises:

```python
raise RuntimeError("no cases ran\n[FAIL] fabricated: got 0 want 1")
```

returns, both with `expect` omitted and with `expect="fabricated"`:

```text
ok=True, caught=True, fails=['fabricated'], attributed=True, reports=0
```

No test case executed. The traceback’s message satisfies `bool(fails)` and exact-name attribution.

This exposure is inherited, rather than introduced by this repair. Nevertheless, it refutes broad false-green closure: the 2×2 proves closure over **empty parsed failures**, not over crashes generally. Narrow the claim or strengthen the child-result contract.

## Medium

**M1 — the architecture artifact’s evidence does not support its stated width rationale.**  
`docs/reviews/architecture-review-2026-10-13.md:275–293` says three sites survived a filter requiring absence to answer permissively, then establishes that `gate_ran` answers conservatively. It cannot survive that filter as stated.

The remaining rationale also overclaims:

- Two **callers** do not establish an adapter count. The cited skill says “One adapter = hypothetical seam. Two adapters = real seam.”
- #178’s original remedy imports a validating verdict **reader** from `check-review-rounds`. `check-review-decision._validate` validates finding fields—`severity`, `aim`, `fix_induced`, `disposition`, and `component`—rather than `dirty` or `gate_ran`. Calling it on a valid verdict record raises “has no `severity`”.
- The same artifact still calls F1’s width **UNMEASURED** at line 240.

These contradictions invalidate the published justification; they do not establish that option B should be selected.

## Low

**L1 — mutation descriptions misidentify their edits.**  
In `scripts/mutations/check-plan-code.json`:

- Entry 720 says it selects the **FIRST** traceback block; its replacement returns `out[-1:]`, selecting the **LAST**.
- Entry 721 says it drops frame/blank skipping; its edit removes `EXCEPTION_LINE` validation and leaves skipping intact.

Both mutations are falsifiable, but their names describe different severances. Correct the descriptions.

## Checked and found SOUND

- Independently reproduced the complete before/after 2×2. Only B changes; C and D remain green.
- Injected `rc == 2` with a matching `[FAIL]` line: it records `measured=False` and bypasses attribution.
- Real-child probes handled explicit and implicit exception chains, top-level SyntaxError with caret, bare KeyboardInterrupt, and sequential parent/subprocess tracebacks. ExceptionGroup and BaseExceptionGroup return nothing within the declared bound.
- Self-test: **264/264**. Binding: **1,549 anchors / 1,541 entries**. Declared sum: **1,541**; this guard’s declaration: **139**.
- Independently counted **358 literal `.get` calls across 33 files**.
- All **17 scoped mutation controls** returned one killed and one attributed: `603,604,605,609,619,623,625,719–728`. No fourth ambient-pass case established.
- Both #276 experiments reproduced control → mutation → restored control: **27/27** and **119/119** throughout. They demonstrate missing label assertions; the current production labels themselves are correct.
- Constructed-world `main()` calls and rebinding support ADR-0014 compliance. Compliance does not establish exhaustive assertions.
- No unqualified resurrection of the withdrawn figures established in the reviewed changes and inspected code comments.

## CANNOT RUN

The full local mutation sweep and independent CI replay are **NOT RUN**. The local sweep was excluded under the supplied timeout constraint; CI green remains supplied evidence. **Treat these as NOT RUN, not passes.**

The complete nine-site/eight-guard inventory was not independently reproduced; its two coordinator-verified instances were reproduced.

## Instruments

Prepared `.venv/bin/python`, venv-first mutation `PATH`, commit bodies and range diff, AST enumeration, real CPython subprocess stderr, direct production-function probes, isolated control/mutation/restoration copies, and seventeen population-stride mutation shards.

No repository files changed. No review file written.
