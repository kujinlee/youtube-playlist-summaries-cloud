<!-- codex-review: model=gpt-6.1-sol -->

**Medium — The new failed-control mutation survives nondeterministically.** `scripts/check-plan-code.py:3559–3577`; manifest entry at `scripts/mutations/check-plan-code.json:1635`.

The fixture times two tiny subprocesses and checks only which is costliest. Deleting `control_seconds.pop(...)` remains undetected whenever the green subprocess takes longer: the refusal still names `zzz.py`, although the failed control contributed to its estimate.

Executed evidence: over a green **239/239** control, this mutation initially returned **0, 239/239 passed**. Three repetitions returned **1, 0, 0**; only the first failed its named case. This makes the mutation gate flaky and leaves the fold incompletely protected. Use deterministic timings and assert that the failed control contributes zero cost.

**Low — Backlog #208 contradicts the shipped diagnostic behavior.** `docs/backlog.md:236` still claims a partial run cannot construct `Measured` or print a tally, calling that guarantee structural.

Executed `CI=true python3 scripts/check-plan-code.py --mutate . --only scripts/check-merge-ready.py`: exit **0**, **16 killed / 16 attributed**, with a tally explicitly labeled **DIAGNOSTIC**. Update the retained rationale and obsolete “Remains: … `--file X` filter” text.

Other verification at HEAD `90e697ed`:

- Harness self-test: **239/239 passed**.
- `CI=true check-main-drivable.py --self-test`: **438/438 passed, 55.75 seconds**, below 120 seconds.
- All **133** entries’ anchors bind exactly once.
- Of **20 new/rebound entries**, **19** failed every named case; the remaining entry flakes as above. The unchanged 113 were binding-checked, not rerun.
- Real unscoped local run: **exit 2**, `REFUSED LOCALLY`, nothing measured.
- Two-target probes preserved earlier control failures and excluded their cost; production fold behavior held.
- Whole-manifest checks precede `--only` filtering; executed slice output clearly names its scope.

VERDICT: NOT CONVERGED
