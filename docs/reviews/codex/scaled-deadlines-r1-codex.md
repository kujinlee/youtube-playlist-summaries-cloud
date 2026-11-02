<!-- codex-review: model=gpt-6.1-sol -->

1. **P1 — The harness’s own mutation control fails.** `scripts/check-plan-code.py:5147` — **fix-induced: yes**.

   Concrete input: `run_suite_parts(repo, "scripts/check-plan-code.py")`. Measured result: **rc=1, 247/248 passed**. `mutation_env` sets the marker; `child_env` copies `os.environ`, so the new assertion receives `('1', '1')` while expecting `(None, None)`. The harness therefore rejects its unmutated control before measuring its mutants. The borrowed environment also retains the marker for `check-selftest-counts`.

   Fix: distinguish “does not introduce the marker” from “removes an inherited marker,” and explicitly define the count auditor’s environment.

2. **P1 — Skipping held-open stdin loses previously demonstrated mutation coverage.** `scripts/compaction-state.py:1415` — **fix-induced: yes**.

   Constructed production mutant at line 877:

   ```python
   payload, err = read_payload(stdin_text, wait=60.0)
   ```

   Concrete input: an empty pipe whose writer remains open, passed to the PreCompact hook.

   Measured on isolated copies:
   
   - `origin/master` with this mutant: **rc=1**, `TimeoutExpired` in the held-open-stdin case after 60 seconds.
   - This branch with the same mutant and `PLAN_CODE_MUTATION_RUN=1`: **rc=0, 100/100 passed**.

   The direct pipe test supplies `wait=0.2`; it cannot detect broken wiring of the hook’s wait argument. The event-ordered capture test cannot detect it either. This refutes the coverage-preservation claim.

   Fix: retain a fast integration case that exercises the hook’s actual stdin-deadline wiring.

3. **P2 — The new CI guard accepts a disabled real-time step.** `scripts/compaction-state.py:921` — **fix-induced: yes**.

   Concrete input:

   ```yaml
   - name: compaction-state self-test
     if: false
     run: python3 scripts/compaction-state.py --self-test
   ```

   Measured: `ci_runs_real_time(...)` returns `None`, meaning success. It checks command text without checking whether the step executes.

   Fix: validate the enclosing step and job conditions. The guard reads the repository workflow normally and its staged copy during mutation runs; it is not merely checking the synthetic `step` string.

Required foreground checks passed: compaction-state **102/102** normally, **100/100** marked; check-plan-code **248/248**; fixture_git **43/43**.

The doubling loops have finite attempt lists and fail when no event is observed. I found no production marker read or demonstrated nested-suite marker loss. Implicit subprocesses inherit the marker inside `fixture_git.isolated()`; explicit `fixture_git.env()` environments omit it.

**NOT CONVERGED**
