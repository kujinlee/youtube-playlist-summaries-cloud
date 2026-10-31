<!-- codex-review: model=gpt-6.1-sol -->

**CONVERGED — no findings at any severity.**

- `compaction-state.py` differs only in docstrings; ASTs are identical after stripping docstrings.
- `STDIN_WAIT` is correctly grouped as killed by neither mode in the docstring and backlog #424. Scratch mutation `STDIN_WAIT = 20.0` survives: ordinary **125/125**, marker **123/123**, both exit 0.
- `ci_runs_real_time` now explicitly names workflow-level `defaults.run.shell`. Injecting `shell: 'true {0}'` remains accepted (`None`); executing that shell bypasses the script and exits 0, confirming the documented limitation.
- No remaining wording in the reviewed changes exceeds the measured claims.

No review file written; `.claude/plans/` was not accessed.
