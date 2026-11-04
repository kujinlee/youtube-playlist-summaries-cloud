<!-- codex-review: model=gpt-6.1-sol -->

One non-blocking selector defect reproduced at `2e69ba2f`. No BLOCKER established under the round-4 definition.

1. **Medium — NOT BLOCKER; FILED disposition: transitive imports loaded by filename are omitted.**  
   `scripts/check-plan-code.py:451–465`

   **Concrete input:** a PR changing only `scripts/check-dashboard-entry.py`. The selector chooses **21/88 manifests**, including `gen-dashboard`, but omits `compaction-state`.

   The real dependency chain is:
   - `gen-dashboard.py:329` loads `check-dashboard-entry.py` by filename and adopts its parser.
   - `compaction-state.py:482` loads `"gen-dashboard.py"` and uses that parser in `pending_asks()`.

   `_import_spellings()` recognizes quoted `"gen-dashboard"` but not `"gen-dashboard.py"`, so the closure drops this second edge.

   **Observed versus expected:** on a temporary copy, changing the dashboard grammar’s `FLAG` alternative from `needs-you` to `needs-owner` changes `compaction-state.pending_asks()` on its existing fixture from `(1, [ask], None)` to `(0, [], None)`. Its behavior depends on the changed file, yet its manifest remains unselected. Expected: include that consumer through the import closure.

   This establishes an affected-manifest omission, **not a demonstrated surviving mutant or merge escape**. The master full sweep still includes `compaction-state`, so it does not meet the supplied BLOCKER definition.

The round-3 removal holds: no production path closes an issue. Repeated reds comment with their own SHA marker; greens leave issues open; `gh` failures make the step fail. The alert’s six mutations were all killed and attributed. Session-state’s `SWEEP-RED` block remains connected.

The required aggregate’s actual shell returned **0 only for `success`**, and **1 for `failure`, `cancelled`, `skipped`, and empty result**. An empty PR selection explicitly reported zero work and passed after whole-manifest checks. Pins, anchor checks, and home-escape scans precede selection; selected targets retain before/after controls.

Push and schedule select FULL. `issues: write` remains confined to the aggregate job. Manual cancellation remains the previously filed alert exception; pending-run replacement remains #482’s accepted disposition. Docs-only master pushes now receive the full backstop, and schedule also running `verify` adds execution without weakening a gate.

Validation passed:
- `check-plan-code.py --self-test`: **308/308**
- `check-merge-ready.py --self-test`: **256/256**
- Alert self-tests: **15/15**
- Session-state self-tests: **110/110**
- Alert mutation sweep: **6/6 killed and attributed**

No repository files changed. Nothing under `.claude/plans/` was read.

VERDICT: CONVERGED
