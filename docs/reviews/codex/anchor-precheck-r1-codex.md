<!-- codex-review: model=gpt-6.1-sol -->

No actionable findings; no severity assigned. Read PR #405, backlog #252, and `git diff origin/master...HEAD`.

Executed evidence:

- `python3 scripts/check-plan-code.py --self-test`: **244/244 passed**.
- `scripts/check-plan-code.py:2393`: differential probes against actual `run_mutations` agreed for sequential edits creating, destroying, or duplicating later anchors; independent entries; overlapping matches; empty edits; empty anchors; and CRLF input. No false refusal found.
- `scripts/check-plan-code.py:2503`: an injected unreadable target produced `NotMeasured` before staging. A staging tripwire confirmed that **both shards**, plus `--only` naming another target, refused the orphan. This whole-manifest behavior matches the stated design.
- `scripts/check-plan-code.py:4054`: traced the monkeypatched shortfall fixture into actual late application: both anchors were rejected, zero mutation verdicts were recorded, and the global was restored afterward. The arithmetic assertion passes through its intended path.
- `scripts/check-plan-code.py:3782,3803`: both adjusted control fixtures still detect their intended regressions. The existing diagnostic and evidence-tail mutants each failed the corresponding named case.
- All **three new manifest mutations**, applied in memory, failed their named self-test cases.
- Whole-manifest pre-check: **2,108 entries / 2,121 anchors**, zero problems.

No full `--mutate .` sweep was run.

VERDICT: CONVERGED
