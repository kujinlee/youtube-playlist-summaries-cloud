<!-- codex-review: model=gpt-6.1-sol -->

No actionable findings at HEAD `e844614d`.

Executed evidence:

- `CI=true python3 scripts/check-plan-code.py --self-test`: **239/239 passed**.
- `CI=true check-main-drivable.py --self-test`: **438/438 passed in 52.72s**; staged master comparison: **51.40s**. Both below 120s.
- All **133 mutations** have anchors binding exactly once. All **20 new/rebound entries** failed every named case, between green controls. The former failed-control survivor was killed **5/5 times**. The unchanged 113 were binding-checked, not executed.
- Real unscoped local sweep: **exit 2**, `REFUSED LOCALLY`, nothing measured, no tally. CI and `--allow-long-local` bypassed the budget in fixture runs; `CI=false` did not.
- Deterministic probes confirmed failed-control exclusion and failure-first reporting at `scripts/check-plan-code.py:2509` and `:2518`.
- Real CI `--only scripts/check-merge-ready.py`: **16 killed / 16 attributed**, explicitly labeled **DIAGNOSTIC**. Defects planted in unselected manifests still refused execution.
- Documentation matches the behavior. Backlog #208 explicitly supersedes its historical no-tally claim; dashboard counts describe the earlier recorded snapshot.

VERDICT: CONVERGED
