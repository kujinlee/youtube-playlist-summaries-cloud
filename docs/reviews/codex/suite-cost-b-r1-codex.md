<!-- codex-review: model=gpt-6.1-sol -->

### R1-F1 — High — Per-suite cap exceeds the shard’s total deadline

`scripts/check-plan-code.py:1218,2148`; `.github/workflows/ci.yml:1055`.

**Input:** a green control taking ≥30 s, followed by three hanging mutants of that suite.

**Result:** each mutant receives 600 s, and execution continues after each timeout. Three hangs consume **1,800 s**, exhausting the PR/push job’s **30-minute** limit before controls, other mutants, or setup. Scheduled runs execute both seeds: three hangs consume **3,600 s**, exhausting their **60-minute** limit.

With 254 harness mutations across 24 shards, one shard contains 11 of them. Their timeout allowances alone total **110 minutes**, or **220 minutes under two seeds**. Master allowed 22/44 minutes for those same 11 hangs. The job cancellation remains fail-closed, but the new cap does not bound completion within CI’s deadline. Add a cumulative deadline or stop after a cannot-run.

### R1-F2 — Medium — Internally created seed trees discard the supplied limit

`scripts/check-plan-code.py:2054`.

**Input:** `run_mutations(..., seeds=(3,5), limits={"m.py":333})`, omitting `trees`.

**Result:** the recursive call omits `limits`. A scratch producer probe recorded `[None, None]`; a simulated 200-second suite became CANNOT RUN. Passing explicit seed trees recorded `[333,333]` and caught the mutation through its named case.

The normal `mutate_delivered` path supplies trees, but this supported convenience path silently retains the original false timeout. Forward `limits=limits` and cover this combination.

### R1-F3 — Medium — Re-control accepts degradation that the initial control would refuse

`scripts/check-plan-code.py:2007`.

**Input:** scratch fixture with simulated durations: initial control 30 s, correctly attributed mutant 1 s, restored re-control 200 s.

**Result, running both versions:**

- Master: limits `[120,120,120]`; `ok=False`, `NotMeasured`.
- HEAD: limits `[120,600,600]`; `ok=True`, `Measured`.

The mutant tolerance also widens the control invariant: a restored suite exceeding the initial control’s deadline now certifies the run. Keep the re-control’s deadline consistent with the initial control, or explicitly establish why this degradation preserves trustworthy evidence.

Verification: repository self-test **389/389 passed**. Three new mutations—dropping the ceiling, dropping the seeded mutant limit, and leaking sibling-scope flows—each failed its named case in scratch. Those partial scratch suites additionally reported three missing staging-fixture failures.

`_walks_dir` produced **no master/HEAD differences** across 14 targeted inputs and 10,000 generated inputs. Targeted cases included nested definitions, class bodies, lambdas, comprehensions, rebinding, and `global`/`nonlocal`. Existing unusual answers were preserved: top-level class walkers returned false; rebinding after a lister still tainted its earlier argument.

## Loosening answers
LOOSENING-CHECK 8d2f8bd4cc54: finding: suites completing after 120 seconds but within the derived limit can now contribute caught verdicts, and slow re-controls can certify evidence master refused
LOOSENING-CHECK 3f833ef4b8d9: not a loosening
LOOSENING-CHECK 38f234e35820: finding: run_suite now accepts a larger limit and can return an attributed red after 120 seconds where master returned CANNOT RUN
LOOSENING-CHECK 7dd25f6d44c9: not a loosening
LOOSENING-CHECK af4690f3e18e: not a loosening
VERDICT: NOT CONVERGED
