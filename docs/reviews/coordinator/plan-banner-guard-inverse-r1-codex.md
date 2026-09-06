<!-- codex-review: model=gpt-5.5 -->

**Blocking** — Intermediate task commits leave CI red because the declared self-test count is not updated until Task 7.  
Evidence: Task 1 adds five cases (`docs/superpowers/plans/2026-09-04-banner-guard-inverse.md:62-92`) and commits at `:196-197`, but the declared count remains `# 25 cases` in `scripts/check-banner-armed.py:47` and is pinned by `scripts/check-selftest-counts.py:83-89`. Tasks 2-6 add more cases before Task 7 finally updates the count (`plan:697-702`).  
Smallest fix: update the declared count in every task that adds self-tests before committing, or make this a single final commit after Task 7.

**Blocking** — F6 can never pass after the proposed hook move because it compares against the first `exit 2`, which is in a comment.  
Evidence: the test is `hook.index("check-banner-armed.py") < hook.index("exit 2")` (`plan:629-631`). The real hook already contains `exit 2` in the header comment at `.claude/hooks/block-idle-stop.sh:15`, before any possible moved banner invocation. The executable blocking exit is at `.claude/hooks/block-idle-stop.sh:39-40`.  
Smallest fix: parse executable lines only, or assert banner invocation precedes the `check-plan-progress.py` invocation / its following indented `exit 2`.

**Blocking** — Task 5’s logging block references `steps`, but Task 4’s own `run_decide` snippet never binds `steps` in scope.  
Evidence: Task 4 calls `decide(..., steps=_plan_steps() if armed else _UNSET, ...)` inline (`plan:505-509`). Task 5 later uses `steps` in the logging block (`plan:575-581`) and only adds a prose warning to hoist it (`plan:592`). As pasted, a banner-less WARN path raises `NameError`, and the Task 5 self-tests only check `log_line`, not `run_decide`.  
Smallest fix: Task 4 must introduce `steps = _plan_steps() if armed else _UNSET` before `decide`, and Task 5 needs a `run_decide`/log side-effect test for the unbannered case.

**High** — Spec §7/F4 asks for an actual log line for the new warning class, but the plan tests only string formatting.  
Evidence: spec F4 is “a line appears in the log” (`spec:226-230`) and §7 says drop the `if banner:` gate (`spec:269-281`). The plan’s F4 test only calls `log_line(...).split(...)` (`plan:540-546`), so it would not catch the Task 5 `NameError` above or any failure to append in `run_decide`.  
Smallest fix: add an integration-style self-test around `run_decide` with fixture transcript/sentinel/plan and a temporary `WARN_LOG`, or factor a pure “log record for warning” helper and test the gate path that selects it.

**High** — Spec §8 says both “Nothing is blocked” messages are corrected, but the plan edits only `check-banner-armed.py`.  
Evidence: spec §8 item 4 says “Both ‘Nothing is blocked’ messages are corrected” (`spec:287-294`). `scripts/check-ci-watched.py` still has the message at `:107` and a self-test requiring it at `:222-223`. Negative claim checked with `rg`: the plan’s file list excludes `scripts/check-ci-watched.py` (`plan:26-33`) and Task 7 only mentions the old banner message (`plan:684-690`).  
Smallest fix: add `scripts/check-ci-watched.py` to Task 7, reword the message, and rewrite its self-test.

**Medium** — `_edit_inside_repo()` accepts the repo root itself as “a file inside root.”  
Evidence: the helper claims “True iff any path is a file inside `root`” (`plan:446-447`) and spec §4.7 says the predicate is path inside `ROOT` with `.git/` excluded (`spec:204-208`). The pasted code returns `True` for `Path("/repo")`: it is absolute, `resolve().is_relative_to(root)` is true, `relative_to(root).parts[:1]` is empty, then it returns true (`plan:458-468`).  
Smallest fix: require `resolved != root` and preferably `resolved.is_file()` where existence is expected; add a self-test for `"/repo"`.

**Medium** — Task 3’s “failing tests first” are not behavioral; they all fail at the new keyword boundary.  
Evidence: all Task 3 tests call `decide(..., steps=...)` (`plan:285-294`), and the expected failure is `unexpected keyword argument 'steps'` (`plan:299-300`). That proves only that the function signature is old, not that CANNOT_RUN is hoisted above banner detection.  
Smallest fix: split the change: first add the signature with `_UNSET` preserving old behavior, then add behavioral tests that fail because the hoist is missing.

**Coverage map:** §2 is incomplete because `check-ci-watched.py` still says “Nothing is blocked”; §4.1 is attempted but F6 is broken; §4.2, §4.3, §4.4, §4.5, §4.6, §4.7 are mostly covered by Tasks 1-4 with the root-path hole above; §5 F4 and F6 have defective tests; R1-R6 are present; §7 is not actually verified end-to-end; §8 is incomplete; §9 is assigned to Task 7 docstring work.

VERDICT: NOT CONVERGED
