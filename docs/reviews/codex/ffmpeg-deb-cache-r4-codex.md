<!-- codex-review: model=gpt-6.1-sol -->

Reviewed `903d93a5` against `origin/master`. Repository unchanged; the probe used a temporary copy. Findings below are **FILED under DEFER**, with no fixes folded.

1. **P2 — The claimed whole-job budget still substitutes measured runtime for step caps.** `.github/workflows/ci.yml:143–148`

   `verify` contains **83 steps**: six have explicit timeouts—the five cache steps and install—and **77 have none**. Those include checkout, runtime setup, `npm ci`, typechecking, tests, and guards. Four are PR-only, leaving 73 uncapped steps on push.

   Let **R** be the total runtime of every remaining step. The actual path arithmetic is:

   | Path | Explicit caps, minutes | Whole path |
   |---|---:|---:|
   | Update not reused; no key | key 3 + install 20 | **23 + R** |
   | Update reused; no key | key 3 + install 13 | **16 + R** |
   | Exact cache hit | key 3 + restore 2 + seed 1 + install 13 | **19 + R** |
   | Miss/restore failure; staging and save succeed | key 3 + restore 2 + install 13 + stage 1 + save 2 | **21 + R** |

   Failed staging or skipped saving only reduces these subtotals. Seed and stage/save are mutually exclusive.

   Substituting the claimed **measured** `R ≈ 5.3` gives **28.3 / 21.3 / 24.3 / 26.3 minutes**. The advertised 27.3 also adds mutually exclusive cache branches.

   More importantly, **R has no independently enforced cap**. For example, key and install can consume nearly 23 minutes, leaving seven minutes for everything else; `npm ci` alone has no smaller configured limit. The job timeout can therefore cancel later checks. It limits actual execution to 30 minutes; it does not establish that the steps’ budgets fit within 30. [GitHub timeout semantics](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idtimeout-minutes).

   This refutes the budget half of the bet.

Confirmation results:

- **No cache work remains inside install.** Lines 240–307 contain the required apt operations, diagnostics, and executable checks. Manifest verification, copying, staging, and saving are separate steps. Reading `FFKEY_UPDATED` reuses prerequisite work.
- **The timeout expression is valid.** GitHub permits `steps` in a step’s `timeout-minutes`; the expression returns numeric **13** when `updated == 'yes'`, otherwise **20**. Missing outputs evaluate to an empty string. Thus a skipped key step selects 20; a failed key step selects 20 unless its `updated=yes` output was retained, in which case it selects 13. Failure status itself is not tested. [Allowed contexts](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability), [expression semantics](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions).
- **Thirteen minutes covers the configured apt bounds, including an empty cache.** Reusing the index still leaves three downloads, two retry pauses, and one local dpkg operation: `3 × (150+10) + 2 × 15 + (180+10) = 700 seconds`. That leaves 80 seconds for shell work, log printing, and `ffmpeg`/`ffprobe` checks. Those activities lack separate bounds, so 13 minutes is not an unconditional completion guarantee, but I found no additional demonstrated regression from this cap.
- **Same-size forgery probe rerun:** executed the extracted seed block under `bash -e -o pipefail`, with temporary paths and a read-only forged archive matching the genuine payload’s size. Exit **0**; output reported **0 restored, 1 rejected**; the destination remained empty. This tested the copy gate, not actual dpkg installation.

**PR body and dashboard:** the separation and verification descriptions match the tree. Their “sum of STEP CAPS” budget remains false. **FILED, Low:** `docs/dashboard-entries.md:17705` also still says “all three,” although there are five optional cache steps.

VERDICT: NOT CONVERGED
