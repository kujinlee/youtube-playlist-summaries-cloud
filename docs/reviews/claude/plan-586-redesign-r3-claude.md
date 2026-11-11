Reviewed head: cf19b6846aeabf800c0f6788b487f582019fe8b5

# plan-586-redesign r3 — Claude half (adversarial, the r2 fold)

Subject: the r2 fold (`git diff 6d3e88ef 8a2fd165`) and anything it introduced in slices 6-8 of
`docs/superpowers/plans/2026-11-09-observed-reach-selection.md`, against spec §2/§7/§8.6 and
`docs/reviews/architecture-review-2026-11-09-plan-586-ledger-trust.md` §8-§9.

**No §8 BLOCKER found.** One MAJOR (the fold's own class-search rule undoes the owner's reset) and six MINORs.

## Findings

### F1 — MAJOR — the owner's epoch reset is undone by an old-epoch report written before the reset merged

**Where:** plan Task 7.3, epoch-change clause (line 1133, *"A report written for the OLD epoch and absorbed only
after the reset is absorbed into the NEW epoch for its misses and events only"*, added by the r2 fold's class
search); Task 8.2 *It also LATCHES* (line 1396) and its X3 case (line 1411); Task 8.1 clause 9's claim (line 1295)
*"an owner's reset is not undone by the reports it archived"*.

**Scenario (run against the extracted `absorb_epoch`/`absorb_errors`, script below):**
1. A red master sweep → day-10 report R10 records post-switch event E; an absorb PR latches E in epoch d0.
2. Task 8.2 step (1): every daily `--report` runs `post_switch` "over every red master full sweep since
   `epoch.start`" and records each hit. Nothing omits an event the ledger already holds (`report()` omits only
   DECIDED PRs). So the day-11 report R11, written before the reset merges, carries E again, `epoch_start` d0.
3. Day 12: the owner's reset (archive verbatim, empty epoch, later `start`) passes the guard. The epoch-change
   clause never lists reports, so R11 being unabsorbed does not stop it.
4. The next PR: gate clause 9 reads R11 (id `11.1` is in no epoch) → `unabsorbed miss`. The next absorb MUST take
   R11 (`absorb_errors` → `listed report not absorbed: 11.1` otherwise), and `absorb_epoch` writes E into the NEW
   epoch (`ABSORB MISSES ONLY: 11.1 report from another epoch`) → clause 4 `latched miss`.

Output: `new epoch events: [{'sweep_run_id': 77, 'pr': 600, ...}]`, and the guard accepts that absorb (`[]`).

The same thing happens with a shadow MISS. Every report written after the miss's first report and before the
absorb's checkout repeats it, because #600 is not yet decided at its checkout. Any such report published after
the absorb PR's `verify` is unabsorbed at reset time. For post-switch events this is near-certain, not a race:
one schedule between the absorb merge and the reset merge is enough. The owner's only recovery path (spec §7 Q5)
therefore needs a SECOND reset, and nothing says so. Task 8.2's X3 case tests the ledger in isolation, so it
passes while the live loop re-latches. Fails CLOSED, so it is not §8's BLOCKER, but it breaks the Q5 contract the
plan states.

**Fix (either):** (a) the epoch-change clause refuses while `list_reports(skip=BASE ids)` is non-empty
(`absorb first: <ids>`), so a reset archives every report written for the epoch it closes; or (b) when absorbing
an old-epoch report into a new epoch, skip a miss or event that an archived epoch already holds verbatim, so only
a miss the owner has NOT seen re-latches. (a) is simpler and keeps "every report is absorbed into the epoch it
was written for". Add the R11 case to Task 7.3 and Task 8.2.

Reproduction: `/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/b387c8e6-9003-42f5-a944-1d4eb1de0c9b/scratchpad/r3claude/reset.py`
(run with the scratchpad dir as argv[1]; `plan_code.py` there is the block extracted from the plan at this head).

### F2 — MINOR — a backdated reset `start` makes the re-latch permanent

**Where:** Task 7.3 line 1131, *"`start` strictly later"* (strictly later than BASE's `start`, nothing more).
**Scenario:** old epoch `start` 2027-01-01. A reset on 2027-03-01 with `start` 2027-01-02 passes the guard. Every
later report then re-scans PRs merged since 01-02, the missed #600 included, and re-runs `post_switch` over the
red sweeps since 01-02. That re-records the miss and the event in the NEW epoch every day, so no reset can clear
it while the inputs live. **Fix:** require the new `start` to be no earlier than the reset commit's date (or later
than every archived row's `merged_at` and every archived event's sweep). Add it to the guard's epoch clause.

### F3 — MINOR — comparing every attempt on its own breaks on "Re-run failed jobs"

**Where:** Task 7.2 `--report` (2), line 907; `compare_push` / `decide_pr`, line 942.
**Scenario:** a PR run's shard 3 flakes. Someone uses "Re-run failed jobs", and attempt 2 re-runs only shard 3.
`sweep-select` did not re-run, so `selection-<id>-2` does not exist and only `verdicts-<id>-2-3` does. Compared
on its own, attempt 2 has no `selector_blob` → `not a sample` (compare_push checks the blob first, None
included). Attempt 1 has an incomplete shard 3 → `inconclusive`. Whether an attempt-1 `clean` beside an attempt-2
`not a sample` is `clean` is not defined: `decide_pr` has rules for "all clean" and "every push not a sample",
not for that mix. This was possible before only for PRs that changed the selector. The fold makes it the outcome
of every partial rerun. It does not loosen, but it silently starves the 20-clean count, or an implementer picks a
rule. **Fix:** define the attempt view as "this attempt's artifact, else the latest earlier attempt's for a job
not re-run". Give `decide_pr` an explicit rule for a mix of `not a sample` with other results (ignore
`not a sample` pushes, as clause 5 ignores the rows). Add the partial-rerun case.

### F4 — MINOR — attempts that produced no report are re-queried forever, so the stated cost bound is wrong

**Where:** Task 7.2 step 3 (line 828) and the cost line (line 832, *"at most about 31 calls"*).
**Scenario:** an attempt that ended `failure` or `cancelled` "contributes its report if one exists", so it costs
an artifacts call. It never gets an identity in `skip` (nothing was absorbed), so EVERY listing re-queries it for
the whole 120-day window. An earlier attempt of a rerun run also costs +1 state call on every listing. A comparator
that fails for two weeks adds about 14 calls to every gate fetch for four months. Once the switch is open, the
gate fetches on every PR run (MEASURED in the plan: 710 runs in 7 days) against `GITHUB_TOKEN`'s 1,000 requests
per hour. The bound of "about 31" counts only unabsorbed SUCCESSFUL attempts. It fails closed
(`reports unreadable`), so this is liveness only. **Fix:** the upload step is `if: success()`, so a
non-`success` attempt cannot hold a report and needs no artifact call. Otherwise, restate the bound with the
non-success attempts in the window.

### F5 — MINOR — a report's identity is read from its BODY, while `skip` matches the run listing

**Where:** `report_id(rep)` (line 1043) uses `rep['run_id']`/`rep['run_attempt']` from the downloaded JSON;
`list_reports` filters `skip` by the run object's `<id>.<n>`.
**Scenario:** a report downloaded from run 5 attempt 1 whose body says `run_id: 6` (a comparator bug, e.g.
`GITHUB_RUN_NUMBER`) is absorbed as `6.1`. Run 6's real report, which may hold a miss, is then filtered out by
`skip` (`6.1`) on every later listing, by the guard and by gate clause 9. Its miss is never read. This needs a
trusted-code bug, so it is not §8's BLOCKER, but the two identities should not be able to disagree. **Fix:**
`report_schema_ok` (or `list_reports`) refuses a report whose body `run_id`/`run_attempt` differ from the
run/attempt it was downloaded from. Add the case.

### F6 — MINOR — `gh api --paginate` on the runs endpoint is not one JSON document

**Where:** Task 7.2 step 2 (line 808), and the F4 case's fake `gh`.
**Scenario:** for an object-shaped response, `gh api --paginate` writes one JSON object per page, concatenated.
The plan expects two pages. A `json.loads` of the whole output raises, which fails closed. A parser that reads
only the FIRST object (for example `raw_decode`) silently drops page 2, the oldest runs, so a late rerun report
there is invisible to the guard and the gate alike. **Fix:** specify `--paginate --jq '.workflow_runs[]'` (one
object per line) or `--slurp`. Make the F4 fake emit gh's real multi-page byte shape, so a first-object-only
parser goes red.

### F7 — MINOR — leftovers and an understated race cost

- Plan Global Constraints, line 68: *"by its IDENTITY (its run id, listed in the ledger)"*. Since C2 the identity
  is `<run_id>.<run_attempt>`. Spec §7's last row (line 572) still names `shadow-report-<run_id>`.
- Task 7.3 line 1113: *"at most one re-run per absorb PR that stays open across the schedule"*. The absorb "rides
  the coordinator's ordinary docs batch". Every later push to that PR re-runs `verify`, which re-lists and goes red
  again whenever a daily report has appeared since the last local `--absorb`. The cost is one re-absorb per push
  that crosses a schedule, not per PR. It fails closed. State it, or tell the absorber to run `--absorb`
  immediately before each push.

## Tried and could NOT break

- **A listing that differs between the local absorb and the guard** (pagination, the 120-day window, a report
  published in between, an attempt that finishes in between). The guard requires HEAD's ids to equal BASE ∪ the
  guard's OWN listing exactly, then rebuilds. Every divergence surfaces as `listed report not absorbed`,
  `absorbed id is no listed trusted report`, or a raise, and each refuses. I found no divergence that admits a
  ledger losing a miss. Two concurrent absorb PRs edit the same JSON region, so they conflict textually and force
  a re-push and re-verify. I did not find a non-conflicting merge of two add-only absorbs that drops a row.
- **Re-ran the r2 fold's extracted code** (identical to the plan block at this head, by `diff`): the Codex C1
  selective absorb, a contradiction kept by hand, the 14 weekly selective absorbs, the subset choosing the
  non-miss row, two attempts as two identities. Each is refused, with its adjacent pass.
- **The absorb-gap bound, read against its simulation** (`fold586r2/adv.py`). The model matches the plan's
  rule: listable = uploaded and less than 90 days old and run created within the window; an absorb takes all
  listed; the guard refuses at `day - through > 76`; `through` = max `generated_at`, which is ≤ the absorb day.
  The argument also holds when the merge lags `verify`: the next deadline is measured from `through` ≤ the
  verify time, and a report uploaded after verify lives 90 days. Limits of the model: it stops at the first
  refusal (the reset is not modelled), integer days hide the hour-long upload lag at the window edge (harmless:
  such a report is absorbed long before day 120), and it does not model the gate. The claim is stated only up to
  the last admitted absorb, so this is consistent.
- **Non-default BASE.** `ci.yml` runs `pull_request` only for `branches: [master]`, and all 200 recent PRs target
  master, so BASE is always the default branch. §9's "what the default branch says" holds.
- **The `status`-less listing and reruns.** An in-progress rerun leaves attempt 1's report listed and RAISES if
  that report is gone. A `pull_request` run never lists. A feature-branch dispatch is filtered out by
  `branch=<default>`, so its skipped `shadow-compare` job (run `success`, no report) never RAISES.
- **The guard with no API.** An unchanged ledger makes no call. A failed listing with a changed ledger is rc 2.
  `verify` gets the full `permissions` block plus `GH_TOKEN`. No current `ci.yml` `run:` body contains `gh ` and
  lacks a token (grep over non-comment lines: only a step NAME matches), so the new `GH_CALLERS` read does not
  red existing steps.

## Could not verify

- Live GitHub behaviour: whether a rerun keeps attempt 1's artifacts, whether a `status`-less runs listing
  includes in-progress runs, and artifact expiry measured from upload. The plan defers all three to its merge-gate
  reads and fails closed either way.
- `fresh_epoch`, the epoch-change clause, `list_reports` and `switch_gate` exist only as prose. F1 and F2 are
  checked against the extracted `absorb_epoch`/`absorb_errors` plus the prose rules as written (stated, not run
  against an implementation).
- No plan, spec or GitHub state was touched. This file is the only one written.

VERDICT: NOT CONVERGED
