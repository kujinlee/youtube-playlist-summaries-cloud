<!-- codex-review: model=gpt-6.1-sol -->

## Findings

**HIGH — `scripts/check-plan-code.py:849` — CI environment changes bypass the full-run precondition.**  
`fix_induced: true`

Reproducer: add `scripts/startup/sitecustomize.py` and set the mutation job’s `PYTHONPATH` to `${{ github.workspace }}/scripts/startup` in `ci.yml`. The startup module contains:

```python
import sys, time

def exit_zero(code=0):
    time.sleep(0.5)
    raise SystemExit(0)

sys.exit = exit_zero
```

Neither changed path forces unchanged guards into FULL mode. Using the existing first mutation of `check-function-revokes.py`, I measured:

- FULL: `caught=False`, mutation survives.
- EARLY: `caught=True`, `stop='sigint'`, no survivors.

The green control still exits zero. Thus the fold’s “same imported code” precondition does not cover interpreter startup or workflow environment changes.

**Realistic-or-theoretical:** demonstrated, deliberately constructed adversarial bypass. CI environment and interpreter changes are realistic maintenance; this exit-rewriting hook is contrived. Existing sibling imports commonly spell `fixture_git` or literal filenames passed to `spec_from_file_location`; ordinary aliases retain those spellings and are covered. Computed imports, transitive imports and package initializers remain theoretical escape routes here. I found no concrete JSON-fixture, other-manifest or shell-dependency exit-code bypass.

**Fix:** force FULL for execution-environment changes, including workflows and interpreter/dependency configuration. Either establish a conservative dependency closure or run FULL when changed executable code cannot be excluded as a dependency.

Other requested checks:

- **Diff:** CI uses `git diff --name-only -z "$BASE"...HEAD`, with `BASE=origin/<base_ref>` and default PR checkout of the merge commit. This compares the merge base to checked-out `HEAD`, rather than explicitly comparing the PR head SHA. Full history is fetched; a failed diff removes the partial list and forces FULL. Refs are checkout-time snapshots; no additional stale/partial-list defect was demonstrated.
- **Ratchet:** the allowance matches one exact stripped line in `ci.yml`, with count one. It adds no wildcard or substring exemption.
- **Mutations:** all 12 new entries have unique matching anchors and correctly named expected cases, including dynamically constructed names.
- **Self-tests:** `check-plan-code.py`: **326/326**; `check-merge-ready.py`: **256/256**.

VERDICT: NOT CONVERGED
