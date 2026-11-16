<!-- codex-review: model=gpt-6.1-sol -->

Reviewed `c7755050`, redesign `8721e5e8`, and `origin/master...HEAD`. No BLOCKER found. No files edited or GitHub accessed; `.claude/plans/` was not read.

**MINOR — `docs/dev-process.md:163`: liveness description retains the deleted contract.**

- **Breaking input:** last green sweep completed 40 hours ago; a red full sweep completed one hour ago.
- **Wrong output:** the documentation describes “no completed sweep in 36 h,” but `session-state.py:858–861` prints `STALE` despite that recent completion. The implementation correctly follows the redesigned **green** contract.
- **Fix:** replace “no completed sweep” with “no green scheduled master sweep.”
- **fix_induced: true** — the redesign changed the contract without updating this description.
- **Disposition:** file separately under the round-cap rule; no merge-blocking change requested.

The adversarial checks found:

- A recent green marker can remain fresh after a newer red, missing, or cancelled night. It explicitly reports the **last GREEN** sweep, not the latest scheduled attempt’s verdict. After 36 hours without another green marker, it reports `STALE`.
- The current marker writer requires schedule, master, first attempt, and successful preceding steps. PRs and manual events cannot reach it; sampled PR runs produce no marker. The reader excludes non-master and fork markers. This relies on the repository preserving the exclusive marker writer: artifact names themselves do not authenticate the producing workflow.
- Sampling deterministically ranks deduplicated targets by SHA-256 and unions the sample with directly named manifests. Non-PR selection remains full. I found no concrete harness regression that escapes both paths.
- A green rerun produces no marker by design. Missing markers before the first scheduled green, authentication failures, and short artifact pages also have explicitly documented outcomes.

Required self-test result lines:

- `check-plan-code.py`: `506/506 passed`
- `session-state.py`: `150/150 self-test cases passed`
- `sweep-costs.py`: `36/36 passed`
- `check-merge-ready.py`: `400/400 self-test cases passed`

The other touched Python file, `scripts/mutations/expected_mutations.py`, is a data module without a self-test entry point.

The scheduled-log acceptance below is an intentional loosening with per-seed normalization, not an additional defect.

## Loosening answers
LOOSENING-CHECK 78d24cf9fa8a: not a loosening
LOOSENING-CHECK dd15e5bdf30d: not a loosening
LOOSENING-CHECK 1e2478fd5813: not a loosening
LOOSENING-CHECK 8ab12d60e28b: not a loosening
LOOSENING-CHECK 0085414c8cfa: finding: completed scheduled full-sweep logs with a well-formed seed declaration are accepted; master refused every scheduled log
LOOSENING-CHECK 960f273307d8: finding: completed scheduled full-sweep logs with a well-formed seed declaration are accepted; master refused every scheduled log
LOOSENING-CHECK 07931f9e4c36: finding: completed scheduled full-sweep logs with a well-formed seed declaration are accepted; master refused every scheduled log
LOOSENING-CHECK 7f40bf3df38b: not a loosening
LOOSENING-CHECK 05b78844295d: not a loosening
LOOSENING-CHECK f3cf8887ebfc: not a loosening
VERDICT: CONVERGED
