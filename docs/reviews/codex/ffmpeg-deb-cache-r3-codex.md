<!-- codex-review: model=gpt-6.1-sol -->

Reviewed `140706d0` against `origin/master`, prior reviews, coordinator decision, and PR #407’s current body. Repository unchanged; experiments used temporary scripts and a disposable Ubuntu 26.04 container.

1. **P2 — Cache verification/copy can still prevent installation through the required step’s timeout.** `.github/workflows/ci.yml:251–266`

   `sha256sum` and `sudo cp` have no independent timeout. The subshell suppresses failure exits, but a stalled command never reaches its warning handler. Its only backstop is the **required install step’s 20-minute timeout**.

   **Executed fault injection:** ran the extracted block under `bash -e -o pipefail`, substituted a sleeping copy, and applied a shortened external watchdog. The install marker was never reached. This demonstrates the missing timeout boundary; I did not reproduce a spontaneous filesystem stall or wait 20 minutes.

   GitHub’s step timeout kills the step process; the optional steps’ `continue-on-error` cannot protect this required step. [GitHub workflow reference](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idstepstimeout-minutes).

   This directly refutes the availability half of the bet. Bound the entire verification/copy operation independently, or move it into a separate bounded, optional step.

Confirmation results:

- **Read-only, same-size forgery:** rejected; install marker reached. Subsequent staging replaced it with verified bytes.
- **Partial restore with extras:** staging retained exactly the manifest entry; the extra disappeared.
- **Invalid staging hash:** staging failed without emitting `complete=yes`, withholding save authorization.
- **Copy/hash failure exits:** both reached the install marker under `-e -o pipefail`. No remaining ordinary cache-command exit demonstrated an `errexit` abort.
- **Hung `--print-uris`:** executed with the real 30-second timeout in Ubuntu 26.04. Returned 124, emitted no key, preserved `updated=yes`, and returned successfully.
- **Restore error:** protection confirmed by configuration and documented `continue-on-error` semantics; no live GitHub restore-error run was executed.
- **Integrity:** no unlisted or hash-rejected restored file crossed the copy gate in these probes. Actual dpkg installation was not rerun.

The subshell also masks individual copy errors: a forced `cp` failure printed `restored 0 …; 0 rejected` without the advertised copy-failure warning. Apt can download the missing archive, so this does not establish a failure the install must propagate. **FILED, low severity:** misleading failure reporting.

**Budget:** the arithmetic is correct: `28.3` and `28.0` minutes. The latter is not a worst-case bound: it substitutes the 700-second apt bounds for the whole install step, omitting verification/copy time. Using the actual 20-minute step cap gives `36.3` minutes across those components, exceeding the job cap.

**PR body and dashboard:** the staging and integrity descriptions now match the tested behavior. The unconditional availability guarantee and “worst case” budget remain unsupported. “All three” optional cache steps is also stale: there are now four.

VERDICT: NOT CONVERGED
