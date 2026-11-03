<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head: b39640824d51138fdee957c4eacdf922227a8176

- **Medium — `scripts/check-selftest-counts.py:421`: timeout leaves descendants running.** `subprocess.run(timeout=600)` kills the suite process, without creating or killing a process group. A hung suite that launches another process leaves that descendant alive after CANNOT RUN, potentially retaining ports or writing files while other suites run. Reproduced with a shortened timeout: the descendant survived. This defect predates the PR but remains unresolved.

- **Medium — `scripts/check-selftest-counts.py:496`: signal crashes receive the wrong verdict.** A suite killed by SIGKILL returns `-9`, enters the generic nonzero branch, and produces rc 1 (“its own cases are red”) instead of CANNOT RUN/rc 2. Reproduced with a real subprocess that printed a passing count before killing itself. Handle negative return codes separately.

Other checks: worker exceptions and nonzero exits cannot become passes; CANNOT RUN correctly takes precedence over red suites. No concrete new suite collision found; `fixture_git.isolated()` changes each subprocess’s environment independently. The re-bound mutation anchor preserves the original behavior under test.

Validation: **51/51 self-tests passed; 29/29 mutations killed and attributed to their named cases.** The sweep required temporarily linking the main checkout’s TypeScript dependency; that link was removed afterward.

VERDICT: NOT CONVERGED
