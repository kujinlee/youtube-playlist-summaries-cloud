Reviewed head: 221533a7521706a728773822d030ccf9c83d40d5

# plan-586 (observed-reach selection): round 3 (the cap round), Claude half

Subject: `docs/superpowers/plans/2026-11-09-observed-reach-selection.md` at `221533a7` (the round-2 fold),
against the approved spec `docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md`. Mandate: REFUTE
the round-2 fold in `ledger-trust` (the selector's list re-validated in `shard_targets`, `Q1_DECISION` at BASE, the
`SELECTOR_FILES` refusal, `trusted_ledger` provenance, the fixed `shadow-ledger` name with pagination, the
`shadow-ledger` concurrency group, the `shadow_start` epoch). Codex alternates out this round.

For every finding: **caused by the round-2 fold?** and **component**, for the thrashing question.

## What I checked by reading the repo (not the plan's claims)

- `git show 221533a7 -- <plan>`: the whole fold diff, line by line, against the text at `a808ef1e`.
- `.github/workflows/ci.yml` today: workflow-level `concurrency: group: ci-${{ github.workflow }}-${{ github.ref }}`,
  `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`; `on:` is `pull_request`, `push` (master,
  `batch/**`), `schedule`. **There is no `workflow_dispatch` today**; Task 7.2 adds it to the WORKFLOW (it is an
  `on:` key, not a job key), so every job of `ci.yml` becomes dispatchable on any branch.
- Task 4.2's `record-reads` never runs on `pull_request` (its `if:`), Task 5.3's `pick_cache` filters keys by
  prefix and sha-ancestry only (no `ref`), Task 6.2 restores "by the exact key it printed".
- The r1 wording of the empty-ledger rule (`a808ef1e`): "`no shadow-ledger-* has ever existed` (the API answers
  with an empty list) starts an empty ledger". The r2 wording: "`no trusted shadow-ledger has ever existed` (no
  candidate passes) starts an empty ledger", where candidates are first filtered to `expired == false`.

## What holds (tried and could not break)

- **X-F1's fix.** I could not build a list that passes `shard_targets` while omitting a rule-1 or rule-2 pick: the
  shard re-derives `full, reasons` in the harness on the same `GITHUB_SHA` merge commit `sweep-select` checked out,
  so the two can only disagree toward refusal (today's rule). Codex's `["scripts/nonexistent.py"]` construct is
  closed. What the shard CANNOT check is rule 3 itself, which is why F1 below matters.
- **X-F2's fix.** `q1_at_base` + the `SELECTOR_FILES` refusal close the self-enabling PR; the ast import case
  covers new selector modules (`strace_reads` is harness through `check-plan-code.py`'s import).
- **X-F4's ordering argument** (a pending job has read nothing) is correct; see F6 for what the group's KEY gets
  wrong.
- **X-F5.** A fixed name with the exact `name` filter is right.

## Findings

### F1 — HIGH — a PR can poison its OWN read sets through the PR-scoped Actions cache, and rule 3 then skips named targets

**Construct.** Push 1 of a PR adds `.github/workflows/x.yml` (not a harness file: `harness_files` is
`{check-plan-code.py, ci.yml} | imports`), triggered on `pull_request`, that runs `actions/cache/save` with key
`readsets-<python>-<hash>-<a real master sha>` and a payload whose every record is `trace: complete`, rc 0, equal
counts, `reads: []`, `probed: []`. That cache lands in the PR's scope (`refs/pull/N/merge`). Push 2 (or a re-run):
`sweep-select`'s `pick_cache` sees the key (the cache-list API lists every ref's caches, and the plan filters by
prefix and ancestry only), and `actions/cache/restore` with that exact key restores the PR-scope entry FIRST
(GitHub searches the run's own ref before the base branch; from the documentation, not exercised). `restore_check`
passes: the sha is an ancestor of BASE, every target appears once, and the key elements are copyable. Rule 3 now
drops every target picked only by naming. `shard_targets` cannot see this: it validates rules 1 and 2 only. With
the switch open, a PR touching e.g. `docs/backlog.md` skips every guard that merely names it.

**Why it matters to this round.** The fold's new Global Constraint says "Nothing a pull request produces or edits
may open the switch for that PR or any other", and proves it for the list, `Q1_DECISION` and the ledger, but the
read sets are the input rule 3 actually skips on, and the PR can write them.

**Fix.** `pick_cache` keeps only entries whose `ref == refs/heads/<default branch>` (the cache-list API returns
`ref`), and the restore is done by `gh api`/`actions/cache` only after asserting that ref; or carry the payload as
a `record-reads` ARTIFACT checked by the same `trusted_ledger`-style run provenance (event `push`/`schedule`,
default branch, same repository). Case: a PR-ref entry with a nearer ancestor sha is skipped.

**Caused by the round-2 fold: NO** (Tasks 5.3/6.2 are unchanged since r1). **Component: readset-cache provenance**
(not `ledger-trust`).

### F2 — HIGH — when every ledger has expired, the comparator starts an EMPTY ledger and a latched miss is erased without the owner

**Construct.** Candidates are filtered to `expired == false` before the trust check, and "no candidate passes"
starts an empty ledger, rc 0. Any 90 days without a successful upload empties the candidate set. The fold itself
supplies a way to get there: "the newest TRUSTED one must pass the schema or the run fails closed (nonzero, nothing
uploaded)". So a trusted ledger the current code cannot parse (a `schema: 2` writer reverted, a truncated upload,
a field renamed) makes `shadow-compare` fail every day; it is not a required check and the plan files no alert on
its failure; on day 91 that ledger expires, the next run finds no candidate, rebuilds from `SHADOW_START`, and
every decided row whose inputs also expired (the r1 Codex F5 case: a `miss` kept only by the ledger) comes back
`inconclusive`, i.e. not a miss. `ledger.counts.miss` is 0, and 20 new clean PRs open the switch. The fail-closed
branch times out into fail-open. The same happens after a scheduled-workflow suspension (GitHub disables
schedules on an inactive public repository) longer than retention.

It also contradicts the fold's own sentence in *The epoch*: "Moving `SHADOW_START` is the ONLY way to clear a
latch (Task 8.2)".

**Fix.** Genesis is explicit, never inferred from absence: an empty ledger starts only when the run is a
`workflow_dispatch` with an input `genesis: true` (or a committed `LEDGER_GENESIS = "<shadow_start>"` equal to
`SHADOW_START` and no trusted artifact, expired or not, ever listed); otherwise no usable trusted ledger → nonzero,
nothing uploaded, and `switch_gate` stays refused (`no shadow ledger`), which it already does. Add an alert on
`shadow-compare` failure (it can append to `sweep-red-alert.py`'s report like Task 8.2), so the job cannot fail
silently for 90 days. Cases: all candidates `expired: true` → nonzero (adjacent: `genesis: true` → empty ledger);
a trusted `schema: 2` ledger → nonzero AND the alert line.

**Caused by the round-2 fold: YES.** The r1 text started empty only on "an empty list"; the fold widened it to
"no candidate passes", which includes the all-expired list, and added the schema hard-failure that leads there.
(The 90-day persistence bound itself is r1's choice of artifacts; the fold made the erase explicit and reachable.)
**Component: ledger-trust.**

### F3 — MEDIUM — `trusted_ledger` trusts a RE-RUN of an old scheduled run, which writes the newest ledger with old code

**Construct.** A re-run keeps the run's `event` (`schedule`), `head_branch` (`master`), repository and `path`,
and executes the workflow at its ORIGINAL `head_sha` (re-runs are allowed for 30 days). Schedule run S at sha X
fails on a flake; PR Y merges a fix to `compare_push` (say, one that counted an `unreproduced difference` as clean)
or an `EPOCH RESET`; the owner then clicks "Re-run all jobs" on S. S's `shadow-compare` acquires the group, reads
the newest trusted ledger (Y's), and writes a new `shadow-ledger` with X's code: X's buggy decisions become
"decided" rows that every later run KEEPS (`ledger` never re-decides a decided PR), and an X-era `SHADOW_START`
differs from Y's, so X starts a "new epoch", undoing the reset and dropping expired decided rows (F2's loss). The
new artifact's `created_at` is newest, so it wins. Whether `upload-artifact@v4` accepts the same name in a later
attempt of one run is UNVERIFIED; if it refuses, the job fails and no harm follows, so the plan must not rely on it.

**Fix.** The ledger records `code_sha` (`GITHUB_SHA`); `shadow-compare --run` refuses (nonzero, nothing uploaded)
when its own sha is not a descendant-or-equal of the predecessor's `code_sha` (`git merge-base --is-ancestor`),
and `trusted_ledger` additionally requires `run.run_attempt == 1` OR the same check. Case: a predecessor written
by a NEWER sha → the older code refuses.

**Caused by the round-2 fold: YES** (the provenance predicate is the fold's; it checks WHO ran, not WHICH CODE).
**Component: ledger-trust.**

### F4 — MEDIUM — `q1_probe_delta` is still produced by a pull-request run, so it is PR-controlled evidence

**Construct.** The fold moved the source to "the newest `selection-*` of a PR this ledger lists as MERGED". That
artifact is still written by the PR's own `pull_request` run: PR HEAD's `reach_select.py` and the PR-scope cache
(F1). Two paths: (a) the PR's earlier push ran a different `reach_select.py` than the one that merged, and a
re-run of that superseded run produces a `selection-*` with a later `created_at`, so "newest" takes the
superseded code's delta; (b) F1's poisoned read sets make any merged PR's delta whatever the payload says. A delta
≤ 5 under `"B"` opens the Q1 clause of `switch_gate`. This contradicts the fold's Global Constraint (*Nothing a
pull request produces ... may open the switch*).

**Fix.** Compute `q1_probe_delta` in `shadow-compare` itself (default-branch code, default-branch cache, PR #543's
pinned commits), so it is a property of master's selector, not of any PR's run. Case: a merged PR's `selection-*`
with delta 2 while master's computation gives 6 → the ledger holds 6.

**Caused by the round-2 fold: YES** (the fold rewrote this source and its new rule is still PR-produced).
**Component: ledger-trust.**

### F5 — MEDIUM — the epoch is any string inequality, so a revert, a reformat or a typo of `SHADOW_START` silently resets the latch

**Construct.** "The predecessor is merged only when its `shadow_start` equals the running code's `SHADOW_START`;
otherwise ... a NEW epoch". `git revert` of an `EPOCH RESET` commit, `"2026-11-12"` → `"2026-11-12T00:00:00Z"`, or
moving the date BACKWARD is each a new epoch with no `EPOCH RESET` in any PR body; the only guard is the stated
convention, and these edits do not look like resets to their author. Every decided row whose inputs expired is
lost (F2's mechanism).

**Fix.** Make the reset explicit in code: a new epoch only when `SHADOW_START` parses as a date STRICTLY LATER than
the predecessor's AND a committed `EPOCH_RESET_FROM` equals the predecessor's `shadow_start`; any other inequality
→ nonzero, nothing uploaded. Cases: backward date → refused; reformat → refused; forward with the matching
`EPOCH_RESET_FROM` → new epoch (adjacent).

**Caused by the round-2 fold: YES** (the epoch rule is the fold's). **Component: ledger-trust.**

### F6 — LOW — the `shadow-ledger` concurrency group is global, so a feature-branch dispatch can cancel or block the trusted writer

**Construct.** Task 7.2 adds `workflow_dispatch` to `ci.yml`'s `on:`; a dispatch may name any branch. Its
`shadow-compare` job joins the SAME job-level group `shadow-ledger`: while it runs, master's schedule job waits;
if another job queues behind it, the pending master job is CANCELLED (a group holds one pending job). Its own upload
is then ignored by `trusted_ledger`, so it is all cost: the day's trusted run is lost, and repeated, it feeds F2.

**Fix.** Give `shadow-compare` `if: github.ref == format('refs/heads/{0}', github.event.repository.default_branch)`
so only the default branch runs it (the trust predicate already ignores the rest), and case it in the `ci.yml`
read.

**Caused by the round-2 fold: YES** (the group and its key are the fold's). **Component: ledger-trust.**

### F7 — MEDIUM — per-candidate run lookups let any PR make the trusted writer fail closed, every day

**Construct.** `newest_trusted` walks candidates newest first and does one `gh api .../actions/runs/<id>` per
candidate until a trusted one, and "a FAILED ... run lookup ... exits nonzero". Any pull-request run can upload an
artifact named `shadow-ledger`; a PR whose workflow uploads one per run (or many PRs' worth) puts N untrusted
candidates ahead of the trusted one, costing N lookups per run against the token's rate limit, and one failed
lookup fails the job. The writer then fails daily, which is F2's precondition.

**Fix.** Pre-filter locally from the artifact list itself, which carries `workflow_run.{head_branch,
head_repository_id, repository_id}` (from the API documentation, not exercised): drop every candidate whose
`head_branch` is not the default branch or whose repository ids differ BEFORE any lookup; only the survivors get
the run lookup for `event` and `path`. Case: 150 PR-run candidates ahead of the trusted one → zero lookups for them.

**Caused by the round-2 fold: YES** (the lookup-per-candidate with fail-closed is the fold's).
**Component: ledger-trust.**

### F8 — MEDIUM — the ledger is not keyed to the SELECTOR, so a merged selector change goes live on evidence gathered under the old one

**Construct.** The `SELECTOR_FILES` refusal protects only the PR that edits `reach_select.py`. Once it merges,
the next PR runs the NEW rule 3 against a ledger whose 20 clean PRs measured the OLD rule's would-skip sets; the
epoch is keyed to `shadow_start` only. A change that loosens rule 3 (more would-skips) is live with zero shadow
evidence for the targets it newly drops. (Task 8.0's revert to option A only ADDS picks, so it is the safe
instance; a later rule-3 edit is not.) The fold's "or any other" PR in the Global Constraint overstates what the
refusal does.

**Fix.** Each `selection-*` records the blob sha of `reach_select.py` it ran; `clean_consecutive_from_start`
counts only samples whose selector blob equals the BASE blob `switch_gate` reads (`git show BASE:` already
there), or a change to that blob on master starts a new epoch automatically. Case: 20 clean under blob A, BASE at
blob B → `0 of 20`.

**Caused by the round-2 fold: NO** (the ledger was never keyed to the selector at `a808ef1e`; the fold only added
the overstated sentence). **Component: ledger-trust.**

## Q2 — did a fold contradict another task or the spec, or make a task unexecutable?

- **Contradiction inside the fold:** "Moving `SHADOW_START` is the ONLY way to clear a latch" (Task 7.2, *The
  epoch*) vs. the all-expired → empty-ledger rule (F2), and the old-code re-run (F3).
- **Contradiction with the fold's own Global Constraint** ("Nothing a pull request produces or edits may open the
  switch"): the read sets (F1) and `q1_probe_delta` (F4) are both pull-request products.
- **Spec §7 Q5** makes revisiting after a latched miss the owner's; F2 and F5 clear a latch with no owner act.
- **No task is made unexecutable.** Slice 7 now edits `reach_select.py` (before any refusal exists, fine); slice
  8's own PR is refused by both `q1_at_base` (no `Q1_DECISION` at BASE) and `selector changed`, which its live
  check already expects. Note, not a finding: adding `workflow_dispatch` to `ci.yml`'s `on:` makes EVERY job
  dispatchable (the sweep runs FULL, and Task 8.2's alert condition is `event_name != 'pull_request'`, so a red
  dispatched sweep on a feature branch would file a `sweep-red` issue); the plan should say whether that is wanted.

## Q3 — thrashing

Round 2's six findings were all caused by the round-1 fold, in `ledger-trust`. This round has SIX findings
caused by the round-2 fold in the same component (F2-F7: one HIGH, four MEDIUM, one LOW), each in text
the fold added (the empty-ledger widening, the provenance predicate, the merged-PR delta source, the epoch rule,
the global group, the per-candidate lookup). By `docs/review-method.md` → *The arming condition*, two
consecutive rounds of fix-caused findings in one component: **Phase 6 is ARMED for `ledger-trust`.** F1 (readset
cache) and F8 (selector key) are NOT fold-caused and are reported for completeness, not counted toward arming.

The common cause, for the architecture review: the ledger is an ARTIFACT with 90-day retention, rebuilt by
whatever code runs, and its trust is inferred from metadata about the run that wrote it. Each fold adds a refusal
around one way that inference goes wrong. A design that removes the class: compute every gate input (the ledger,
`q1_probe_delta`) on the default branch from inputs whose provenance is master's (master-scope cache, master-run
artifacts), persist it where it does not expire and every write is a reviewed, monotonic commit (for example a
bot-free committed `docs/shadow-ledger.json` updated by the owner's merge of a generated PR, or append-only
evidence the gate re-derives), and let `switch_gate` read it at BASE like `docs/backlog.md`.

## Could NOT check

- Live GitHub behaviour: PR-scope cache priority on an exact-key restore, the cache-list API's `ref` field, the
  artifact list's `workflow_run` fields, `upload-artifact@v4` on a re-run attempt, and job-level concurrency's
  pending-job cancellation. Each is from GitHub's documentation as I know it, not exercised.
- I did not execute any of the plan's code; nothing of slices 6-8 exists.

VERDICT: NOT CONVERGED
