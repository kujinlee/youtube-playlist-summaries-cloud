# Round 3 — `plan-586` (backlog #586 implementation plan) — coordinator — Claude NOT CONVERGED; THRASHING, Phase 6 ran, redesign needs a spec change (owner)

REVIEW GAP: codex — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 3
fixes_nontrivial: true
subject: plan-586
halves:
  claude: ran
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: F1, severity: High, aim: deliverable, fix_induced: false, component: readset-cache-provenance, disposition: fixed}
  - {id: F2, severity: High, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: filed}
  - {id: F3, severity: Medium, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: filed}
  - {id: F4, severity: Medium, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: filed}
  - {id: F5, severity: Medium, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: filed}
  - {id: F6, severity: Low, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: filed}
  - {id: F7, severity: Medium, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: filed}
  - {id: F8, severity: Medium, aim: deliverable, fix_induced: false, component: ledger-trust, disposition: filed}
```

Subject: `docs/superpowers/plans/2026-11-09-observed-reach-selection.md` at `221533a7` (the round-2 fold), reviewed by
the Claude half at `docs/reviews/claude/plan-586-r3-claude.md`. This disposition is written at `052c3579` + this commit.

## Phase 6 was armed, and this is its answer

**Phase 6 was armed.** Round 2's six findings were all caused by the round-1 fold in `ledger-trust`. Round 3 has
six (F2-F7) caused by the round-2 fold in the same component. That is two consecutive rounds
(`docs/review-method.md` → *The arming condition — full account*). Each attribution was checked against
`git show 221533a7`:
- F2: the widened "no candidate passes" genesis rule;
- F3: the run-metadata predicate;
- F4: the merged-PR delta source;
- F5: the epoch string rule;
- F6: the global group;
- F7: the per-candidate lookup.

All six are text the fold added. F1 and F8 are not fold-caused, and are not counted toward arming.

**The review:** `docs/reviews/architecture-review-2026-11-09-plan-586-ledger-trust.md`. **Root cause:** the gate
can open on state that is carried forward through Actions artifacts. Those artifacts expire, any run can write
them, and whatever code runs rewrites them. So every fold has to infer which writer to trust, and every inference
has an edge.

**Recommended design D1 (review §3):**
- Every input that can open the switch is read at BASE, from a committed `docs/shadow-ledger.json`.
- That file changes only through absorb PRs, under a monotonic guard.
- The comparator writes stateless reports, and those reports can only close the switch.

**D1 changes one sentence of spec §2**, so it is the owner's decision. The quoted sentence and the exact diff are
in review §5. Slices 6-8 are marked BLOCKED in the plan. Slices 1-5 can be built now (review §7).

## Dispositions

| Finding | Severity | Disposition | If the owner approves D1 (the spec diff) | If the owner declines (D0: keep the spec, fold the fix) |
|---|---|---|---|---|
| **F1** a PR-scope cache entry poisons its own read sets | High | **FIXED in Task 5.3.** It is not the ledger class, and its fix needs no spec change (review §4). `pick_cache` keeps only `ref == refs/heads/<default>` entries; the cache list carries `ref`, MEASURED 2026-11-09. It refuses `key shadowed in <ref>` when the chosen key is also listed under another ref. Cases include a nearer PR-ref ancestor, which is skipped. The residual race needs a workflow the PR adds, which is the plan's existing review bound | (same) | (same) |
| **F2** all ledgers expired → empty ledger → latch erased | High | filed: held for the owner's decision | **Removed.** Genesis is the ledger file's creating commit. Expiry cannot empty a file. A stopped comparator or absorb makes `ledger stale` (14 days), which refuses: fail CLOSED | An empty ledger only on a `workflow_dispatch` with input `genesis: true` and no trusted ledger, expired or not, ever listed; otherwise nonzero, nothing uploaded. Plus an alert line on `shadow-compare` failure through `sweep-red-alert.py`. Cases: all candidates expired → nonzero; `genesis: true` → empty (adjacent) |
| **F3** a re-run of an old run writes the newest ledger with old code | Medium | filed: held | **Removed.** Reports inherit nothing. The absorb guard accepts a report only when its `code_sha` is an ancestor-or-equal of BASE and its `reach_select.py` and `shadow-compare.py` blobs equal BASE's. The gate's tightening read is a UNION over reports, so a report that omits a miss cannot hide it | The ledger records `code_sha`. `--run` refuses when its own sha is not a descendant-or-equal of the predecessor's `code_sha`, and `trusted_ledger` requires `run_attempt == 1` or the same check. Case: a predecessor written by a newer sha → the older code refuses |
| **F4** `q1_probe_delta` comes from a PR run | Medium | filed: held | **Removed.** The report computes it with default-branch code, it is absorbed into the ledger, and the gate reads it at BASE | The comparator computes it itself. Case: a merged PR's `selection-*` says 2 while master's computation gives 6 → the ledger holds 6. (The same edit to Task 6.1 is needed under D1; review §6) |
| **F5** epoch = any string inequality | Medium | filed: held | **Removed.** The epoch is a field of the committed ledger. The guard refuses a move that is not strictly later, that alters `previous_epochs`, or that has no `reset_by_owner`. `check-merge-ready.py` HOLDs any epoch change, which makes spec §7 Q5 a machine | A new epoch only when `SHADOW_START` parses STRICTLY LATER and a committed `EPOCH_RESET_FROM` equals the predecessor's start; else nonzero. Cases: backward → refused; reformat → refused; forward and matching → new epoch |
| **F6** a global group lets a feature-branch dispatch cancel the writer | Low | filed: held | **Removed.** No concurrency group is needed, because reports are independent. `if:` restricts the job to the default branch on cost grounds | `if: github.ref == format('refs/heads/{0}', github.event.repository.default_branch)` on `shadow-compare`, plus a `ci.yml` read case |
| **F7** per-candidate lookups let any PR fail the writer daily | Medium | filed: held | **Removed from the writer.** Only the gate's tightening read and the absorb guard list artifacts. Either one failing refuses (fail closed). Both pre-filter on the list's `workflow_run` fields before any lookup | Pre-filter on `workflow_run.{head_branch, head_repository_id, repository_id}` before any run lookup. Case: 150 PR-run candidates → zero lookups for them |
| **F8** evidence is not keyed to the selector | Medium | filed: held | **Removed.** Rows count only under the epoch's `selector_blob`, which must equal `BASE:scripts/reach_select.py`. The gate moves to `scripts/reach_gate.py`, so editing the gate does not reset the evidence. An option-A revert (Task 8.0) restarts the count, which is the stated cost | `selection-*` records `selector_blob`. `clean_consecutive_from_start` counts only samples whose blob equals BASE's. Case: 20 clean under blob A with BASE at blob B → `0 of 20` |

**Why `filed` for F2-F8.** No fix is applied on this branch: the plan's slices 6-8 stay as they were and are
marked BLOCKED. The fix depends on the owner's answer, and each row above gives both forms, so the fold needs no
guessing. This keeps the round honestly NOT CONVERGED.

**Coordinator-found, recorded (no new finding):** the plan's fixed artifact name `shadow-ledger` (Task 7.2, from
the r2 fold) already departs from the spec's `shadow-ledger-<run_id>` (spec §2 line 356). The r2 coordinator
wrote that the spec was not changed. D1's diff resolves this. Under D0, the r2 rename must itself go to the owner
as a spec wording change, or revert to a prefix lookup.

**Q2 note from r3 (not a finding):** adding `workflow_dispatch` to `ci.yml`'s `on:` makes every job dispatchable,
including the sweep and its `sweep-red` alert. D1 needs `workflow_dispatch` only for `shadow-compare`, and the
job's `if:` limits it to the default branch. Under either design the fold must say whether a dispatched sweep on
a feature branch should file `sweep-red`. Today's alert condition (`event_name != 'pull_request'`) would let it.

## NEEDS THE OWNER

**Decide:** approve the spec §2 diff in the architecture review §5 (D1), or keep the spec (D0)?
- **A (recommended).** Approve the diff. The ledger becomes a committed file read at BASE, and the comparator
  becomes a stateless report writer. Slices 6-8 are rewritten to review §6.
- **B.** Keep the spec. Fold r3's seven fixes onto the artifact ledger (the right-hand column above). The class
  stays, with its bounds stated.

Slices 1-5 do not wait on this.

## Verdict

**Claude: NOT CONVERGED.** F1 is fixed (Task 5.3). F2-F8 are held for the owner's decision on the redesign.
`fixes_nontrivial: true`: the F1 fix adds a refusal with cases. **Next:** after the owner answers, fold slices 6-8
(D1 per review §6, or D0 per the table). Then run ONE scoped round 4, past the cap: findings FILED unless they are
a BLOCKER as review §8 defines it.
