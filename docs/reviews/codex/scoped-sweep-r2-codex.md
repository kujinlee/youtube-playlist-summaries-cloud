<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head `0845887c` against `origin/master`. Two findings remain.

1. **P2 — An older green rerun clears a newer red alert.** `.github/workflows/ci.yml:1312–1320`

   **Concrete input:** master commit A passes; descendant B fails its full sweep and opens `sweep-red` issue #501; rerun A successfully. GitHub reruns retain the original commit SHA. [GitHub documentation](https://github.com/github/docs/blob/main/content/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs.md)

   **Observed:** executing the workflow’s extracted shell with a `gh` state shim closed #501, rc 0, with a comment claiming the full sweep was green. The step checks neither the issue’s failing SHA nor ancestry. Concurrency serializes execution but does not establish commit freshness.

   **Expected:** A’s evidence must not resolve B’s failure. Keep the alert open unless the green sweep covers the failing commit. Otherwise SessionStart subsequently reports no open alert while current master remains defective.

   This is introduced by the FOLD’s automatic close behavior.

2. **P2 — Excluding `scripts/` walkers demonstrably drops an affected manifest.** `scripts/check-plan-code.py:453–457`

   **Concrete input:** append this valid Python comment to `scripts/check-usage-pace.py`:

   ```python
   # REMEMBER_HANDOFF
   ```

   **Observed selector result:** **5/87** manifests selected: `check-agent-large-read`, `check-agent-long-call`, `check-fixture-variation`, `check-selftest-counts`, and `check-usage-pace`. **`check-canonical-source` is omitted.**

   In an isolated copy preserving repository symlinks, its unchanged suite changed from **28/28, rc 0** to **27/28, rc 1**, reporting:

   ```text
   scripts/check-usage-pace.py restates handoff-path
   (carries 'REMEMBER_HANDOFF') without citing
   .agents/skills/shared/handoff-path.md
   ```

   That guard walks `scripts/` at `scripts/check-canonical-source.py:268–273`, and its suite audits the actual tree at line 539.

   **Expected:** select that manifest or FULL. This is a demonstrated runtime dependency omission, separate from accepted orphaned anchors. **Limitation:** this reproduces a red control, not a newly surviving mutation; the ordinary guard can also catch it. I did not construct a new control-green survivor.

Round-1 verification:

- **X1/C1:** all listed sibling changes now select their omitted consumers. The original `gen-work-lines.py` reproducer still turns the goal-tree mutant from **200/205, rc 1** into **205/205, rc 0**, but goal-tree is now selected.
- **C2:** `docs/memory/MEMORY.md` selects **51/87**, including both named docs walkers. The `scripts/` exception remains defective as above.
- **C3:** both dependency manifests select FULL.
- **C5:** `m4_base_db.py` selects both previously omitted transitive consumers.
- **C4:** SessionStart surfaces open issues; failure and malformed-output cases produce **CANNOT READ**. Its suite passes **110/110**. The new close behavior introduces finding 1.

Other checks held:

- Undetermined diffs, harness changes, push and schedule select FULL.
- Empty selection returns `Measured(declared=0)`; the required aggregate still reports. Its shell rejects failed, skipped and cancelled shard results.
- With an empty selection, injected pin drift, target home escapes and replacement home escapes each refused measurement.
- Alert shell probes covered first red, second red, two open issues on green, and label creation before the first red. These used a `gh` shim, not live Actions.
- `issues: write` remains confined to the aggregate job. Manual cancellation remains filed C6; pending-run replacement remains the accepted #482 disposition.
- Docs-only master sweeps and scheduled `verify` add execution; neither weakens a gate.

Required suites passed: **check-plan-code 305/305; check-merge-ready 256/256**. No repository `.claude/plans/` content was read.

VERDICT: NOT CONVERGED
