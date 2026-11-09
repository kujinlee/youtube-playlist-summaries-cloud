# Round 3 — `plan-586` (backlog #586 implementation plan) — coordinator — Claude NOT CONVERGED; THRASHING, Phase 6 ran, the owner approved redesign D1; next is `plan-586-redesign` round 1

REVIEW GAP: codex — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

REDESIGNED → plan-586-redesign. The owner approved design D1 on 2026-11-09 at 14:55 (selection card, answer A
"Committed ledger (recommend)"). The spec §2 diff and the rewrite of slices 6-8 are applied at the commit after
`4e22a93f`. A redesign restarts the count (`docs/review-method.md` §0 Q4c, *A REDESIGN RESTARTS THE COUNT*), so the
next round is `plan-586-redesign` round 1, BOTH halves, not a round 4 past the cap.

```yaml
round: 3
fixes_nontrivial: true
subject: plan-586
halves:
  claude: ran
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: F1, severity: High, aim: deliverable, fix_induced: false, component: readset-cache-provenance, disposition: fixed}
  - {id: F2, severity: High, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: F3, severity: Medium, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: F4, severity: Medium, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: F5, severity: Medium, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: F6, severity: Low, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: F7, severity: Medium, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: F8, severity: Medium, aim: deliverable, fix_induced: false, component: ledger-trust, disposition: fixed}
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
in review §5. Slices 6-8 were marked BLOCKED in the plan at `4e22a93f`. Slices 1-5 can be built now (review §7).
⟳ **2026-11-09 14:55: the owner approved D1** (*The owner's answer*, below); the BLOCKED markers are removed.

## Dispositions

**Under D1, the owner's answer (2026-11-09 14:55).** Each F2-F8 row's disposition is now `fixed`: the defect was
real, and on this branch either the design removed the text it lived in, or the fix it still needs is folded at the
place named. The D0 column is kept below for the record; it was not applied.

| Finding | Severity | Disposition under D1 | Where it is now |
|---|---|---|---|
| **F1** a PR-scope cache entry poisons its own read sets | High | **fixed** (at `4e22a93f`, unchanged by D1) | Task 5.3 `pick_cache` (review §4) |
| **F2** all ledgers expired → empty ledger → latch erased | High | **fixed: removed by the design** | No artifact ledger and no genesis rule exist. Genesis is the creating commit of `docs/shadow-ledger.json` (Task 7.3); expiry cannot empty a file. A stopped comparator or absorb fails CLOSED by `ledger stale` (Task 8.1, clause 7) |
| **F3** a re-run of an old run writes the newest ledger with old code | Medium | **fixed: removed, plus a guard clause** | Reports inherit nothing (Task 7.2). `check-shadow-ledger.py` refuses a report whose `code_sha` is not an ancestor-or-equal of BASE, or whose `reach_select.py` / `shadow-compare.py` blob differs from BASE's (Task 7.3). The gate's tightening read is a UNION over unabsorbed reports (Task 8.1, clause 9) |
| **F4** `q1_probe_delta` comes from a PR run | Medium | **fixed: still needed a fix, folded** | `selection-*` no longer carries it (Task 6.1); the report computes it in-job with default-branch code (Task 7.2); the absorb copies it, the guard checks it against a trusted report (Task 7.3); the gate reads it from the ledger at BASE (Task 8.1, clause 6) |
| **F5** epoch = any string inequality | Medium | **fixed: removed, plus a guard clause and a HOLD** | The epoch is a field of the committed ledger. The guard refuses a move that is not strictly later, alters `previous_epochs`, or lacks `reset_by_owner`; `check-merge-ready.py` HOLDs any epoch change (Task 7.3). `SHADOW_START` is gone |
| **F6** a global group lets a feature-branch dispatch cancel the writer | Low | **fixed: removed by the design** | Reports are independent, so `shadow-compare` has NO concurrency group (a case asserts its absence). The job's `if:` restricts it to the default branch on cost grounds, and it lives in its own `shadow-compare.yml` (Task 7.2) |
| **F7** per-candidate lookups let any PR fail the writer daily | Medium | **fixed: removed from the writer, pre-filter kept** | The report writer lists no reports. Only the gate's tightening read and the absorb guard list them, through `list_reports`, which pre-filters on `workflow_run.{head_branch, head_repository_id, repository_id}` before any lookup; either failing refuses (Tasks 7.3, 8.1). Case: 150 PR-branch candidates → zero lookups |
| **F8** evidence is not keyed to the selector | Medium | **fixed: still needed a fix, folded** | `selection-*` records `selector_blob` (Task 6.1); a push counts only when it equals the report's own (Task 7.2); the gate refuses `selector changed since epoch` against `BASE:scripts/reach_select.py` (Task 8.1, clause 3); the gate moved to `scripts/reach_gate.py` so editing it does not move the key. Task 8.0's revert restarts the count, the stated cost |

**r3's Q2 note, answered.** `shadow-compare` lives in a NEW workflow, `.github/workflows/shadow-compare.yml`, so
`ci.yml`'s `on:` gains no `workflow_dispatch` and a dispatched sweep cannot file `sweep-red` from a feature branch.
`trusted_report_run` checks `path == ".github/workflows/shadow-compare.yml"` (Task 7.2). This departs from review §3's
"`ci.yml`" in the predicate; it is the fold's choice, and round 1 of the redesign should check it.

**The spec divergence the r2 fold left** (the fixed `shadow-ledger` artifact name against the spec's
`shadow-ledger-<run_id>`) is resolved: the spec now names `shadow-report-<run_id>` reports and a committed ledger,
and the plan uses the same names.

<details><summary>The table as written before the owner's answer (both fold forms)</summary>

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

</details>

**Why these were `filed` before the answer.** No fix was applied at `4e22a93f`: the fix depended on the owner's
answer, and each row gave both forms, so the fold needed no guessing.

**Coordinator-found, recorded (no new finding):** the plan's fixed artifact name `shadow-ledger` (Task 7.2, from
the r2 fold) already departs from the spec's `shadow-ledger-<run_id>` (spec §2 line 356). The r2 coordinator
wrote that the spec was not changed. D1's diff resolves this. Under D0, the r2 rename must itself go to the owner
as a spec wording change, or revert to a prefix lookup.

**Q2 note from r3 (not a finding):** adding `workflow_dispatch` to `ci.yml`'s `on:` makes every job dispatchable,
including the sweep and its `sweep-red` alert. D1 needs `workflow_dispatch` only for `shadow-compare`, and the
job's `if:` limits it to the default branch. Under either design the fold must say whether a dispatched sweep on
a feature branch should file `sweep-red`. Today's alert condition (`event_name != 'pull_request'`) would let it.

## The owner's answer

**Asked:** approve the spec §2 diff in the architecture review §5 (D1), or keep the spec (D0)?
**Answered 2026-11-09 14:55, selection card: "A — Committed ledger (recommend)".** Applied: spec §2 *The comparator*
and *The ledger* (the §5 diff verbatim), spec §7's decisions table (a new row), and consistency edits in the spec's
status line, §2's "ADDS four things" and §8.6 (the epoch start, and a FAILS IF clause for the ledger and its guard).
Plan slices 6-8 are rewritten to review §6, and the BLOCKED markers are removed.

## Verdict

**Claude: NOT CONVERGED.** F1 was fixed at `4e22a93f`; F2-F8 are fixed by the D1 fold above. `fixes_nontrivial:
true`. The round stays NOT CONVERGED: a REDESIGN is new material, and no round has seen it.

**Next:** `plan-586-redesign` round 1, BOTH halves concurrently (`docs/review-method.md` §0 Q4c), scoped to the spec
§2 change (*The comparator*, *The ledger*, §7's new row, §8.6's ledger clause) and plan slices 6-8 (with the Global
Constraint *Trust and provenance*). Its BLOCKER line is review §8's: a path by which an input NOT in a file at BASE
opens the switch, or keeps it open after a trusted report holds a miss; or a committed ledger change that loses a
decided row or a miss and passes `check-shadow-ledger.py`. Review ids `plan-586-redesign-r1-claude` and
`plan-586-redesign-r1-codex`.
