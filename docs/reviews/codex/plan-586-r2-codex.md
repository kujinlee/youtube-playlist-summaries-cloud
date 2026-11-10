<!-- codex-review: model=gpt-6.1-sol -->

**F1 — HIGH — A parseable list can bypass the fallback despite being unusable.**

**Evidence:** Task 8.1 accepts any non-empty parsed list when the event is `pull_request` and the selector succeeded. Construct: change `scripts/check-docs.py`; selector result `success`; output `["scripts/nonexistent.py"]`. Today’s `select_manifests` necessarily selects `check-docs.py` through its own-source rule. The planned `shard_targets` accepts the supplied list without requiring known targets or mandatory selections, allowing fewer targets—or no matching mutants—to run.

**Proposed fix:** validate element types, target membership, and all mandatory own-source/own-manifest selections; independently preserve FULL conditions. Any violation falls back. Add this exact successful-selector case.

**Round-1 fold caused it:** Yes; the new acceptance contract is insufficiently strict.

**F2 — HIGH — A PR can decide its own Q1 gate.**

**Evidence:** Task 8.1 reads backlog status at BASE but takes `Q1_DECISION` from the executing selector. Task 5.1 explicitly excludes `reach_select.py` from the harness. With #590 closed, 20 clean PRs, and `q1_probe_delta: 6`, a PR changing `Q1_DECISION` from `"B"` to `"A"` passes the Q1 clause immediately. Its own-source selection protects the selector’s mutants, but does not force today’s selection for other targets. Task 8.0’s separate reviewed commit does not mechanically prevent that commit from enabling its own skips.

**Proposed fix:** read the Q1 decision at BASE, validate its allowed values, and retain today’s selection on the decision-changing PR.

**Round-1 fold caused it:** Yes.

**F3 — HIGH — Artifact names are treated as trusted gate evidence.**

**Evidence:** Tasks 7.2 and 8.1 choose the newest `shadow-ledger-*` by name/time, without checking its producing workflow, event, branch, repository, or commit. A PR workflow can upload an artifact with that prefix and fabricated clean counts; that PR’s harness edit may force its own FULL sweep, but the artifact remains eligible for subsequent selectors. The comparator can then preserve the fabricated rows. GitHub exposes producer metadata suitable for validation. [GitHub artifact API](https://docs.github.com/en/rest/actions/artifacts)

**Proposed fix:** accept ledgers only from the designated successful comparator running trusted default-branch code; validate producer metadata and schema in both consumers. Reject PR-produced and arbitrary branch-dispatch artifacts.

**Round-1 fold caused it:** Yes; persistence now directly authorizes skipping without a provenance contract.

**F4 — HIGH — Concurrent ledger writers can erase a latched miss.**

**Evidence:** Task 7.2 permits schedule and manual dispatch, but specifies no writer serialization. Runs A and B download ledger L0. B scans while evidence is pending; A subsequently observes and uploads a miss as L1. B finishes later and uploads its older pending state as L2. “Newest `created_at`” selects L2, whose previous ledger was L0, so the miss disappears and a previously sufficient clean count can reopen the gate.

**Proposed fix:** serialize all ledger writers with one concurrency group and no cancellation of the active writer. Read the predecessor only after acquiring that serialization. Test overlapping runs and persistence of misses/post-switch events.

**Round-1 fold caused it:** Yes.

**F5 — MEDIUM — The prescribed artifact lookup does not implement prefix matching.**

**Evidence:** Task 7.2 specifies `gh api …/actions/artifacts?name=` “by prefix” for dynamically named `shadow-ledger-*` artifacts. GitHub’s `name` parameter filters artifacts by name; it does not provide the stipulated prefix search. A literal prefix lookup can return an empty list despite existing ledgers, triggering the plan’s “first run” behavior. [GitHub artifact API](https://docs.github.com/en/rest/actions/artifacts)

**Proposed fix:** paginate the repository artifact listing and filter prefixes locally, then validate provenance and expiration. Test an existing suffixed ledger and multiple pages.

**Round-1 fold caused it:** Yes.

**F6 — MEDIUM — The documented restart cannot clear the persisted ledger.**

**Evidence:** Task 8.2 says moving `SHADOW_START` forward restarts the 20-PR count and allows an owner-approved restart. Task 7.2 nevertheless downloads the newest ledger and preserves decided rows; no rule rejects a predecessor whose `shadow_start` differs or excludes its old misses/post-switch events. Following both instructions retains the latch indefinitely.

**Proposed fix:** define an explicit ledger epoch keyed by the trusted shadow-start configuration. Specify how a reviewed epoch change initializes counts and excludes previous-epoch decisions while preserving their historical artifacts.

**Round-1 fold caused it:** Yes.

I could not refute `!cancelled()` itself for ordinary failed/skipped dependencies: GitHub documents that an explicit status condition overrides the normal dependency skip behavior. Whole-run cancellation remains excluded by that expression and already exists in today’s PR concurrency policy. [GitHub workflow semantics](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax), [status expressions](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions)

I could not execute the proposed implementation or verify live Actions behavior because it is not built. I found no additional concrete counterexample in the folded seed merging, copy-relative comparison, probe provenance, single-seed replay, or reason split. No repository files or GitHub state were written; `.claude/plans/` was not read.

NOT CONVERGED
