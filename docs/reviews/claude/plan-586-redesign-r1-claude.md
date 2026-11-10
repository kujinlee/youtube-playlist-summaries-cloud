Reviewed head: 18d72977c4bd733b11c8679bfb25316dde186b02

# plan-586-redesign (observed-reach selection, design D1): round 1, Claude half

Subject: commit `18d72977`, which applies design D1 (owner, 2026-11-09 14:55). It changes the spec's §2 *The
comparator* and *The ledger* and the consistency edits in §7 and §8.6. It also rewrites slices 6, 7 and 8 of
`docs/superpowers/plans/2026-11-09-observed-reach-selection.md`. The BLOCKER definition is
`docs/reviews/architecture-review-2026-11-09-plan-586-ledger-trust.md` §8, and the trust rule is §9: "the switch
opens only on what the default branch says; Actions storage can only close it". Mandate: REFUTE.

## What I checked by reading the repo (not the plan's claims)

- `git show 18d72977`: the spec diff and the rewritten slices 6-8, read in full. I also read the Global
  Constraints, the W1-W8 / WM section and the self-review notes.
- `.github/workflows/ci.yml`:
  - `on:` is `pull_request` (branches `[master]`), `push` (`master`, `batch/**`) and `schedule`.
  - There is no top-level `permissions:`. **`verify` has no `permissions:` block**; only `mutation-sweep-complete`
    has one (`contents: read`, `issues: write`).
  - `verify` checks out with `fetch-depth: 0`.
- `scripts/check-merge-ready.py:1714`: `hold_reasons(files, diff, head, app_tests_at, no_review, fs, *, pins,
  answered)`. It is pure, and the pins are read outside it.
- `scripts/batch-ci.py`:
  - It merges READY PR heads into `batch/**` and resolves conflicts only in `UNION_FILES`.
  - `land` squash-merges each member in order.
  - The batch push runs `verify` on the `push` event, where a `pull_request`-only step does not run.
- Repo volume, MEASURED with `gh api …/actions/runs?created=>2026-11-03`: 710 workflow runs in 7 days, 578 of them
  `pull_request`. The repo is public and its default branch is `master`.

## Findings

### F1 — BLOCKER (§8, bullet 1): a trusted report's miss is lost once `absorbed_through` passes it unabsorbed

**Where:** Task 7.3 `--absorb` ("a report the guard below would refuse is skipped and logged"; "`absorbed_through`
becomes the newest absorbed report's `generated_at`"), the guard's clause list, and Task 8.1 `switch_gate`
clause 9 ("any trusted report with `generated_at` later than `absorbed_through`").

The gate's tightening read only sees reports newer than `absorbed_through`. Nothing makes sure that every trusted
report at or before that point had its misses absorbed. Three concrete paths lead there.

**(a) A comparator or selector change makes a pending miss unabsorbable.**
1. Report R1 (day 5) comes from a trusted `schedule` run on master and holds `#600: miss`.
2. On day 5.5 a PR edits `scripts/shadow-compare.py`. Fixing the comparator is routine, and Task 8.2 itself does
   it. The PR merges.
3. Report R2 (day 6) re-decides #600, because #600 is not in the ledger. The replay is the flaky path the spec
   designs for: "reproduces under only ONE of the two replay seeds → miss" on day 5, "neither → unreproduced"
   on day 6. So R2 says `inconclusive`.
4. The absorb at BASE (after day 5.5) skips R1 as `ABSORB SKIPPED` (its `comparator_blob` ≠ BASE's). It absorbs
   R2 and sets `absorbed_through = R2.generated_at`.
5. Clause 9 no longer looks at R1, because R1 is older than `absorbed_through`. Clause 4 has no miss row.

The result: a trusted report holds a miss and the switch stays open.

**(b) Hand-resolving an `ABSORB CONFLICT`.** R1 says `#600: miss` and R2 says `#600: inconclusive` (or `clean`, if
the failing push's artifacts went missing and the PR is now judged on its final push). `--absorb` refuses. A
hand-edited ledger then takes R2's row and sets `absorbed_through` to R2's time. Every clause of
`check-shadow-ledger.py` passes:
- the added row is "held with identical content" by a trusted report (R2);
- nothing was removed;
- `absorbed_through` moved forward.

No clause compares an added row against OTHER trusted reports that decide the same PR. Clause 9 then drops R1 as
in (a).

**(c) Order of upload versus `generated_at`, with no concurrency group.** Task 7.2 removes the group, so a
dispatch can overlap the daily run. Run A starts at 00:00, run B at 01:00:
1. B uploads at 02:00.
2. An absorb at 02:30 sees only B and sets `absorbed_through` to B's `generated_at`.
3. A uploads at 03:00.

If `generated_at` is the run's START (the plan does not say which), A's `generated_at` is earlier than
`absorbed_through`. A's misses are then never absorbed and never read by clause 9.

**Why it is the §9 rule broken, not an edge.** A miss only TIGHTENS. By §9 it may come from anywhere, yet the
absorb applies the blob and ancestry refusals (which exist to stop LOOSENING content) to misses as well. Clause 9
also keys "absorbed" by a timestamp, not by identity.

**Fix (any one closes all three; the first is the smallest):**
- `switch_gate` clause 9 reads EVERY trusted, unexpired report. It refuses when any miss or post-switch event in
  any of them is absent from `ledger_at_base`, whatever `absorbed_through` says. Drop the "newer than" filter.
  14-day staleness plus 90-day retention means every unabsorbed miss stays visible for at least 76 days.
- Optionally, also have:
  - the guard refuse an added row when another trusted report decides that PR differently;
  - the absorb copy misses and post-switch events from a blob-mismatched trusted report instead of skipping it,
    applying the blob refusal to `clean` rows and `q1_probe_delta` only.

Cases to add:
- (a): a skipped older report holding a miss → `unabsorbed miss`;
- (b): a ledger that takes the non-miss side of a conflict → refused, or the gate refuses;
- (c): a report whose `generated_at` is earlier than `absorbed_through` but whose run id was never absorbed →
  `unabsorbed miss`.

### F2 — MAJOR: a latched miss can never be cleared; epoch reset (spec §7 Q5) and the rows model disagree

**Where:** Task 8.1 clause 4 ("any `miss` row or any `post_switch_events` entry in the ledger → `latched miss`"),
Task 7.3's guard ("a removed or altered decided row"; "a drop in … `post_switch_events`"; the epoch is
"append the old epoch VERBATIM to `previous_epochs`"), the Task 8.1 case "20 clean rows recorded under an earlier
epoch (in `previous_epochs`)", and Task 8.2 ("Turning it back on is the owner's … a NEW EPOCH … restarts the 20-PR
count").

**What the schema says.** `rows` and `post_switch_events` are top level, `epoch` is `{start, selector_blob,
reset_by_owner}`, and the guard forbids removing rows or events. So an owner's epoch reset leaves the old `miss`
row and the event exactly where clause 4 reads them. The switch then stays closed forever after the first miss,
whatever the owner decides. That contradicts Task 8.2 and spec §7 Q5 ("revisit").

**The other reading fails too.** The 8.1 case implies rows move INTO `previous_epochs`. If they do, the guard
refuses that move as "a removed decided row".

**It is also unclear which epoch a row belongs to.** Rows carry no epoch, and clause 5 alone filters by
`merged_at ≥ epoch.start`, while clause 4 does not.

**Fix:** make clause 4 read only rows with `merged_at ≥ epoch.start`, and post-switch events after `epoch.start`.
Say in the schema that rows stay in `rows`, and correct the 8.1 case text. Then add:
- a case: a miss row before the current `epoch.start` → clause 4 passes;
- an adjacent case: a miss row after it → `latched miss`.

### F3 — MAJOR: the `if:` on `shadow-compare.yml` very likely skips every scheduled run

**Where:** Task 7.2 *The workflow*: `if: github.ref == format('refs/heads/{0}',
github.event.repository.default_branch)`. A self-test case pins this exact expression.

**The problem.** The `schedule` event has no webhook payload: GitHub's event docs list it as "not applicable", and
`github.event` on a cron run carries only `schedule` (and `workflow`). So `github.event.repository.default_branch`
is empty there. The expression becomes `github.ref == 'refs/heads/'`, which is false, and the daily job is skipped
every day. Only `workflow_dispatch`, whose payload has `repository`, would run.

**Impact.** It fails closed: clause 7 goes `ledger stale` after 14 days. But the comparator the whole shadow
period depends on never runs on its schedule, and the self-test LOCKS the broken expression in. INFERRED from
GitHub's documented payloads; not run. No workflow in this repo uses `default_branch` today
(`grep -rn default_branch .github/`: none).

**Fix:**
- Either use `if: github.ref == 'refs/heads/master'`, with the self-test case asserting it equals the
  `gh api repos/{owner}/{repo} --jq .default_branch` value written into a constant;
- or drop the job `if:`, check the branch in the first step, and exit 0 with a log line.

Trust already rests on `trusted_report_run`, so either is safe. Verify by dispatching once AND reading the first
scheduled run in the merge gate (today's merge gate only dispatches, so it cannot see this).

### F4 — MAJOR: listing every repository artifact on every PR will hit the API rate limit

**Where:** Task 7.3 `list_reports`: `gh api --paginate "repos/{owner}/{repo}/actions/artifacts?per_page=100"`, then
filter locally. Task 8.1 runs it in `sweep-select` on EVERY pull-request run, and the guard runs it on every
ledger change.

**The arithmetic.**
- MEASURED: 710 runs per 7 days, 578 of them `pull_request`.
- After slice 6, every CI run uploads one `verdicts-*` per shard (8 shards) and every PR run one `selection-*`.
  That is about 9 artifacts per CI run.
- INFERRED: about 450 artifacts per day, retained 90 days, so about 40,000 artifacts, or about 400 pages per
  listing.
- The `GITHUB_TOKEN` limit is 1,000 requests per hour per repository. Three PR pushes in an hour exhaust it.

**What breaks.** At that point the gate refuses `reports unreadable`, which is closed and safe. But the same token
budget also serves `sweep-select`'s cache list and, from slice 8, the post-switch step and `sweep-red-alert.py`.
So the switch never stays open in practice, and the backlog #330 alert can fail with it. The r3 F7 pre-filter only
removes run lookups; it does not remove pages.

**Fix:** list the runs of the workflow, not the repository's artifacts:
`gh api "repos/{owner}/{repo}/actions/workflows/shadow-compare.yml/runs?branch=<default>&created=>=<absorbed_through
- 1 day>"` (paginated). That returns the run metadata `trusted_report_run` needs, with no per-run lookup. Then call
`…/runs/<id>/artifacts` for each trusted run. The cost is about 15 runs per gate call. After F1's fix (all
unexpired reports) the cost is at most about 90 runs, still one or two pages. Add a case asserting the call count
for 150 runs.

### F5 — MAJOR: ledger rows do not carry the selector they were decided under, so an early epoch start counts old-selector rows

**Where:** Task 7.2 row schema (`{decision, merged_at, decided_at, pushes: [{head, base, result, differing,
drift}]}`, with no `selector_blob`); Task 7.3's epoch rule ("start strictly later"); Task 8.1 clause 5
(`merged_at` order from `epoch.start`).

**The scenario.**
1. Rows were decided under selector blob X (on day 30 X was the absorb-time BASE blob). The current
   `epoch.start` is day 1.
2. Task 8.0 merges selector Y on day 40.
3. The owner's reset PR sets `epoch = {start: day 10, selector_blob: Y}`. That is strictly later than day 1, so it
   passes the guard.
4. Clause 3 passes. Clause 5 counts the X-decided rows merged between day 10 and day 40 toward Y's 20.

**Why it matters.** This undoes r3 F8's point, that evidence is keyed to the selector by CONTENT. The ledger
keys it only by a date the reset PR types. The HOLD shows the PR to the owner, but nothing machine-checks the date,
and a wrong date is a mistake, not dishonesty (§8's exclusion covers dishonesty only). It is not a §8 BLOCKER,
since the input is in a file at BASE.

**Fix:**
- Copy the report's `selector_blob` into each row at absorb time. The guard checks it via "identical content".
- Clause 5 counts only rows whose `selector_blob == epoch.selector_blob`.
- Case: 20 clean rows under blob X with an epoch keyed to Y → `0 of 20`.

### F6 — MINOR: the ledger's `q1_probe_delta` may be any trusted report's value, not the newest

**Where:** Task 7.3 guard ("an added … `q1_probe_delta` … that no TRUSTED report holds with identical content").

**The problem.** The absorb takes the newest absorbed report's value, but the guard accepts any trusted report's.
Say a hand absorb picks an older report's `4` while the newest says `7`. Clause 6 then passes (≤ 5) and Q1, an
OPENING input, opens.

**Fix:** require the ledger's `q1_probe_delta` to equal the value of the trusted report with the greatest
`generated_at` at or before HEAD's `absorbed_through`, with a case.

### F7 — MINOR: "the job gains `actions: read`" on `verify`, which has no `permissions:` block today

**Where:** Task 7.3 Files, and the Global Constraints' read-only tokens rule.

**The problem.** `verify` runs on the default token. A job-level `permissions: {actions: read}` sets every
unlisted scope to `none`, `contents` included. The plan's words read as adding exactly that one line.

**Fix:** state the block in full as `contents: read`, `actions: read`. Add a `ci.yml` read case asserting it, like
Task 8.2's case for `mutation-sweep-complete`.

### F8 — MINOR: a leftover from the old design names the wrong module

**Where:** Global Constraints, the "No skip takes effect before slice 8" bullet: "a pure
`reach_select.switch_gate`".

**The problem.** Task 8.1 now puts `switch_gate` in `reach_gate.py`, deliberately (so editing the gate does not
move the evidence key). An implementer reading the constraints first would put it in the keyed file. The same
bullet's list of refusals also omits `no ledger at BASE`, `selector changed since epoch` and `reports
unreadable`.

**Fix:** write `reach_gate.switch_gate`, and point to Task 8.1 for the list instead of restating it.

### F9 — MINOR: "decided" is never defined

**Where:** Task 7.2 `report()` ("omitting every PR the committed ledger already holds decided"); Task 7.3 ("a
decided row is never overwritten"; the guard's "removed or altered decided row").

**The problem.** The five decisions are `clean`, `miss`, `inconclusive`, `pending` and `not a sample`. The plan
never says which of them count as "decided".

**What a wrong guess does:**
- If `pending` is absorbed and counts as decided, a pending PR is frozen as pending, and clause 5 skips it.
- If `inconclusive` does not count as decided, a later report may turn it into `clean`.
- In either case the guard's "altered decided row" judges differently from the absorb's.

**Fix:** decided = {`clean`, `miss`, `inconclusive`, `not a sample`}, and `pending` is never written to the
ledger. Add one case for each side.

## What holds (tried and could not break)

- **Opening by a PR's own diff.** Clauses 1-7 read `git show BASE:…` and `git rev-parse BASE:…`. The cases include
  a HEAD ledger with 20 clean rows and a HEAD backlog with ✅, both refused. Clause 6 takes `q1_at_base`, never
  the running constant.
- **A forged or untrusted report opening the switch.** Reports reach the gate only through clauses 8-9, which only
  refuse. The case "a report claiming 25 clean rows does not open a gate refused at `N of 20`" pins this.
- **Deleting, renaming or emptying the ledger.** "BASE has the file and HEAD deletes it" is refused, and so is a
  HEAD that fails the schema. Clause 2 closes the switch when BASE has no ledger. Genesis by the creating commit
  removes the r2 "no trusted ledger → empty" path.
- **Pull-request runs writing reports.** `trusted_report_run` requires `schedule`/`workflow_dispatch`, the
  workflow path, the default branch and the same repository id. A fork's `master` is covered by the id clause.
- **Concurrency-group removal (r3 F6).** Two reports cannot erase each other, because neither reads the other.
  Its one residue is F1(c), which is about absorb ordering, not about reports racing.
- **Batched landing (`batch-ci.py`).** Two absorb PRs both change `absorbed_through`. `docs/shadow-ledger.json` is
  not in `UNION_FILES`, so that conflict EJECTS the second PR rather than producing an unguarded merged ledger.
  An absorb plus an epoch-only PR can merge textually. I found no way that combination loses a row, because git's
  3-way merge does not delete lines neither side deleted.
- **Spec §2 against slices 6-8.** The four guard refusals in the spec's text match Task 7.3's list. "Reads no
  earlier report" is cased in 7.2. The predecessor search, genesis rule, concurrency group and string epoch are
  gone and are not load-bearing anywhere I read.

## Could NOT check

- **F3** depends on GitHub's `schedule` payload, which I did not observe live. A one-line probe workflow would
  settle it.
- **F4**:
  - the artifact count is INFERRED from the run count, the shard count of 8 and the plan's upload list;
  - the 1,000/hour `GITHUB_TOKEN` limit is from GitHub's documentation, not measured here.
- None of slices 6-8 exists, so none of the plan's code was executed. The plan's snippets in these slices are
  interfaces and YAML fragments, not runnable blocks.
- Whether branch protection stops a direct push of `docs/shadow-ledger.json` to master: the guard runs only on
  `pull_request`. The agent push hook blocks it, but a human push is not covered by the plan. Not in §8's
  out-of-scope list either, so I note it rather than raise it.

VERDICT: NOT CONVERGED
