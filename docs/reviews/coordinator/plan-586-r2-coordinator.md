# Round 2 — `plan-586` (backlog #586 implementation plan) — coordinator — Codex NOT CONVERGED; folded

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 2
fixes_nontrivial: true
subject: plan-586
halves:
  codex: ran
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: X-F1, severity: High, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: X-F2, severity: High, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: X-F3, severity: High, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: X-F4, severity: High, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: X-F5, severity: Medium, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: X-F6, severity: Medium, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
```

Subject: `docs/superpowers/plans/2026-11-09-observed-reach-selection.md` at `a808ef1e` (the round-1 fold). The
approved spec `docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md` is NOT changed by this fold.

- Codex half: `docs/reviews/codex/plan-586-r2-codex.md` (F1-F6, recorded here as X-F1..X-F6): 4 High, 2 Medium.
  NOT CONVERGED. Codex itself marked all six "Round-1 fold caused it: Yes"; each was checked against the r1
  fold's diff and the attribution holds (every finding is against text `a808ef1e` added: `shard_targets`'
  acceptance, `Q1_DECISION`, the `shadow-ledger-*` lookup and persistence, the `SHADOW_START` restart).
- Claude half: not run this round (alternation; see the gap line above).

**Component.** All six cluster in ONE component, named here `ledger-trust`: the switch gate and the trust and
provenance of what it reads (the selector's list, the Q1 decision, the persisted ledger and its writers). None is
in the recorder, the parser, the classifier or the selector's rule 3.

**Method.** Every fact a disposition rests on was checked by hand at this head, never taken from the reviewer:
- `scripts/check-plan-code.py`: `SWEEP_WORKFLOW = ".github/workflows/ci.yml"` and `harness_files` returns
  `{SWEEP_HARNESS, SWEEP_WORKFLOW} | <sibling imports>`, so a change to `check-plan-code.py` or `ci.yml` makes
  `select_manifests` run FULL. That is what makes a check placed in `shard_targets` trustworthy against the PR it
  runs on (X-F1, X-F2).
- Plan Task 5.1: "`reach_select.py` is NOT in `harness_files`" and is picked only by its own manifest, so a PR that
  edits it runs its own mutants but nothing forces today's selection elsewhere (X-F2 holds as stated).
- `.github/workflows/ci.yml` top-level `concurrency: group: ci-${{ github.workflow }}-${{ github.ref }}`,
  `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`. The schedule and a dispatch on master share
  `refs/heads/master` and are therefore ALREADY serialized at workflow level today; X-F4 is still a real gap,
  because the plan neither stated nor guarded that dependency (see its row).
- GitHub's artifact list endpoint documents `name` as filtering to artifacts "with this name" (exact), and each
  artifact carries `workflow_run.id`; event, workflow path, head branch and head repository come from
  `GET /repos/{owner}/{repo}/actions/runs/{id}` (X-F3, X-F5). Artifact names must be unique only within one run
  (upload-artifact v4), so a fixed name per run is allowed. ⚠ INFERRED from the documentation, not exercised
  live; slice 7's fake-`gh` cases pin the shapes, and its live merge gate will show them.

## Dispositions

| Finding | Severity | Disposition | Plan section changed |
|---|---|---|---|
| **X-F1** a parseable list bypasses the fallback | High | FIXED. `shard_targets` no longer trusts the list: the shard re-derives `full, reasons` with `select_reasons` on its own diff (the harness, which a PR cannot change without forcing FULL) and refuses (→ today's rule) on `full`, a non-list or non-distinct-string output, an unknown target, or a missing `own-source`/`own-manifest` pick. Codex's exact construct (`check-docs.py` changed, `["scripts/nonexistent.py"]`) is a case, with each clause's adjacent pass | Task 8.1 (`shard_targets`, cases); Global Constraints *Trust and provenance* |
| **X-F2** a PR decides its own Q1 gate | High | FIXED, two refusals. (a) `q1_at_base` reads `Q1_DECISION` from `git show BASE:scripts/reach_select.py` by `ast`; anything but `"A"`/`"B"` → refused. (b) `shard_targets` refuses any list on a PR whose diff touches `SELECTOR_FILES` (`reach_select.py`), so the decision-changing PR, and any PR that edits `switch_gate` itself (the wider class X-F2 is one instance of), runs today's rule; a case asserts every `scripts/` module `reach_select.py` imports is in `SELECTOR_FILES` or the harness | Tasks 8.0, 8.1 |
| **X-F3** artifact names treated as trusted evidence | High | FIXED. `trusted_ledger(run, default_branch)` accepts only `event ∈ {schedule, workflow_dispatch}`, `path == .github/workflows/ci.yml`, `head_branch == ` the API's default branch, and `head_repository.id == repository.id` (a fork branch may be NAMED `master`). Untrusted candidates are skipped; the newest TRUSTED one must pass the schema or the run fails closed (never "use the next one", which could drop a newer latch). Shared by `shadow-compare` and `sweep-select`, so they cannot disagree. **Coordinator-found, same class, folded here:** `q1_probe_delta` was taken "from the newest selection-* on any PR", i.e. an unmerged PR's own selector output; it now comes only from a PR the ledger lists as merged | Task 7.2 (lookup, schema, `trusted_ledger`, cases); Task 8.1 (`sweep-select`, `ledger` None) |
| **X-F4** concurrent writers erase a latched miss | High | FIXED. `shadow-compare` gets `concurrency: {group: shadow-ledger, cancel-in-progress: false}` at job level, with a `ci.yml` read case. The predecessor is downloaded inside the job, after the group is acquired; GitHub cancels only a PENDING job, which has read nothing. Verified: today's workflow-level group already serializes master's schedule and dispatch, so the race was not live as built, but the plan relied on that silently; the job-level group states it and survives a change to the workflow group. Runs on other branches are excluded by X-F3, not by the group | Task 7.2 (Files, *Why the job-level group*, cases) |
| **X-F5** the artifact lookup does not implement prefix matching | Medium | FIXED by a simpler route than the proposed prefix filter: the artifact name is FIXED (`shadow-ledger`), so the API's exact `name` filter is correct; `gh api --paginate`, `per_page=100`; the name and `expired` are re-checked locally. Cases: the trusted ledger on page 2 is found; a `shadow-ledger-old` artifact is not a candidate; an expired one is skipped | Task 7.2 |
| **X-F6** the documented restart cannot clear the ledger | Medium | FIXED. A ledger carries one epoch (`shadow_start`); a predecessor from another epoch is NOT merged, `prs`/`counts` restart from `SHADOW_START`, and `previous_epoch: {shadow_start, counts}` keeps the history; the artifacts themselves stay until 90-day retention. Cases: E1 `miss: 1` → E2 `miss: 0` with `previous_epoch.counts.miss == 1`; same epoch keeps it. **Stated bound:** moving `SHADOW_START` is a semantic loosening `check-merge-ready.py` cannot HOLD (its `hold_reasons` are syntactic); spec §7 Q5 makes it the owner's, so the plan requires `EPOCH RESET` in the PR body and asking the owner first. That is a convention, not a machine, and is said so in the plan | Task 7.2 (*The epoch*, schema, `ledger`); Task 8.2 |

**Codex's closing note** (not a numbered finding): it could not refute `if: ${{ !cancelled() }}` on
`mutation-sweep` and found no further counterexample in seed merging, copy-relative comparison, probe provenance,
single-seed replay or the reason split. No change.

## Rejected

None. Each finding was reproduced against the plan text at `a808ef1e`; X-F4's race is not live under today's
workflow-level group, but the finding (an unstated, unguarded dependency) stands and is folded.

## The thrashing question (`docs/review-method.md` → *The arming condition — full account*)

**Not yet armed, and armed by the next round if it repeats.** The arming condition is "two consecutive rounds
carry findings caused by the previous round's own fix, in one component". Round 1 had none fix-induced (it was
the first round). Round 2 has six, ALL caused by the round-1 fold and ALL in one component, `ledger-trust`. That
is ONE such round. **If round 3 carries a finding caused by THIS fold in `ledger-trust`, Phase 6 arms** and the
round document must convene the architecture review on that component, not fold a third time.

Per-finding evidence that this is one component and one cause: every r2 finding is a place where the r1 fold
let the gate trust something a pull request, a non-default-branch run or an unserialized run can produce (the
list, `Q1_DECISION`, an artifact's name, a stale predecessor, a non-matching filter, an old epoch). *Can a
redesign remove it?* This fold is that attempt: it moves trust to the consumer (the harness and the default-
branch comparator) and closes each hole with a refusal that falls back to today's rule, adding no new mechanism
beyond one provenance predicate, one concurrency group and one epoch key. Logged as the `redesign` bet in
`docs/reviews/decision-scheme/decision-log.jsonl` (the `accrete` bet of the r1 fold is logged beside it,
`continued`, refuted by this round).

**Round 3 is the last round before the cap** (§0 Q4c: from r4, findings are FILED unless a BLOCKER).

## NEEDS THE OWNER

None now. Every fix is inside the approved spec: §2 "backlog #590 must close before any skip takes effect",
§7 Q4 (20 complete clean PRs, 0 latched misses) and §7 Q5 (revisit on a §8.1 event) are what the refusals enforce.
The one owner-shaped item is the stated bound under X-F6 (an epoch reset is the owner's call by spec §7 Q5, held
by convention); it arises only after slice 8 has latched a miss.

## Verdict

**Codex: NOT CONVERGED.** Six findings, all fix-induced, all folded; the fixes are non-trivial (a re-validating
`shard_targets`, a BASE read of `Q1_DECISION`, a provenance predicate, a concurrency group, an epoch), so a
further round is owed.

**Next: round 3, ONE half, Claude** (alternation), on this fold commit, with `REVIEW GAP: codex — alternation` in
the round-3 coordinator. Its brief should ask it to REFUTE the fold in `ledger-trust`: any path by which a pull
request (including a fork, a branch named `master`, or one editing `reach_select.py`, `shadow-compare.py` or
`ci.yml`), a non-default-branch dispatch, or two overlapping runs open the switch, shrink a list below today's
mandatory picks, or erase a latch; and whether `shard_targets`' re-derivation can disagree with the selector's
on the same diff.
