Reviewed head: 052c3579

> **For the r3 disposition of `plan-586` (the backlog #586 implementation plan).** THRASHING triggered this review in
> one component, `ledger-trust`. That component is the switch gate and the trust of what it reads: the selector's
> list, `Q1_DECISION`, the persisted `shadow-ledger`, the ledger's writers and its epoch. All six r2 findings were
> caused by the r1 fold. Six of r3's eight findings were caused by the r2 fold (`docs/dev-process.md` → *Phases*).
>
> **Verdict: REDESIGN. SPEC CHANGE NEEDED (the owner's decision).** The gate keeps writing state forward into
> storage that expires, that any workflow run can write to, and that is rewritten by whatever code happens to run.
> It then infers which writer to trust from metadata about the run. Each fold has patched one way that inference
> goes wrong. **The recommended design (D1):**
> - Every input that can OPEN the switch lives in a committed file read at BASE, as `docs/backlog.md` already is.
> - That file is changed only by reviewed pull requests, under a guard that refuses any non-monotonic change.
> - The comparator becomes a stateless REPORT writer.
> - A report can only CLOSE the switch, never open it.
>
> This contradicts one sentence of the approved spec, §2 (quoted in §5, with the exact diff). So **slices 6-8 are
> marked BLOCKED in the plan**. **Slices 1-5 can be built now.** They do not touch the ledger. r3 F1's fix,
> which is in slice 5, is folded. **BLOCKERs: none.**

# Phase 6 architecture review (narrow, triggered by thrashing): the trust of the switch gate's inputs

**Scope.** These sections of `docs/superpowers/plans/2026-11-09-observed-reach-selection.md` at `052c3579`:
- the Global Constraint *Trust and provenance*;
- Task 5.3 `pick_cache`;
- Task 6.1 `q1_probe_delta`;
- Task 7.2: the ledger's lookup, writers, epoch and schema;
- Task 8.1: `switch_gate`, `q1_at_base`, `shard_targets`;
- Task 8.2: the latch.

The review checks these against the approved spec `docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md`.

**Read first:**
- `docs/reviews/codex/plan-586-r2-codex.md` and `docs/reviews/claude/plan-586-r3-claude.md`;
- the r1 and r2 coordinator docs;
- the two `plan-586` rows of `docs/reviews/decision-scheme/decision-log.jsonl`;
- `docs/review-method.md`: *The stop condition* and *Can a redesign remove it?*;
- `CONTEXT.md` and `docs/adr/`.

No ADR covers how CI evidence is persisted or trusted, so none is re-litigated. ADR-0014 (a guard's main is
drivable) shapes the new guard in §6. The owner's decisions in spec §7 (Q1-Q6) are inputs here, not questions.
Nothing under `.claude/plans/` was read.

## 1. Thrashing or prose floor?

**Thrashing.** Every finding is a construct against plan text, and none is wording, so none is a prose floor. The
table classifies each finding by the gate INPUT it concerns, and by where that input is STORED and who can WRITE it.

| Round | Finding | Gate input | Stored in | Writable by | fix_induced |
|---|---|---|---|---|---|
| r2 | X-F1 a parseable list bypasses the fallback | the selector's list | a job output | the PR's own run | yes (r1) |
| r2 | X-F2 a PR decides its own Q1 | `Q1_DECISION` | the PR's HEAD | the PR | yes (r1) |
| r2 | X-F3 an artifact NAME is trusted | the ledger | Actions artifacts | any run, a PR's included | yes (r1) |
| r2 | X-F4 two writers erase a latch | the ledger | Actions artifacts | two overlapping runs | yes (r1) |
| r2 | X-F5 the `name` filter is exact | the ledger | Actions artifacts | (lookup) | yes (r1) |
| r2 | X-F6 the restart cannot clear | the ledger | Actions artifacts | (epoch) | yes (r1) |
| r3 | F2 all-expired → empty ledger → latch erased | the ledger | Actions artifacts, 90 days | expiry | yes (r2) |
| r3 | F3 a re-run writes the newest ledger with old code | the ledger | Actions artifacts | a re-run of an old run | yes (r2) |
| r3 | F4 `q1_probe_delta` from a PR run | the Q1 delta | `selection-*` artifacts | the PR's own run | yes (r2) |
| r3 | F5 epoch = any string inequality | the ledger's epoch | the script constant + the artifact | any commit, silently | yes (r2) |
| r3 | F6 a global concurrency group | the ledger's writer | Actions job queue | a feature-branch dispatch | yes (r2) |
| r3 | F7 lookups per candidate fail the writer | the ledger | Actions artifacts | any run, many uploads | yes (r2) |
| r3 | F1 PR-scope cache poisons read sets | the read sets | Actions cache | the PR's own scope | no |
| r3 | F8 evidence not keyed to the selector | the ledger | Actions artifacts | (any merged selector change) | no |

r2 alone does not show the pattern. r2 and r3 together do. **Twelve of the fourteen findings concern an input
that lives in GitHub Actions storage (a job output, an artifact or a cache), not in git. The other two are
X-F2 (the PR's HEAD) and F5 (the script constant).** Ten concern the LEDGER, the one input that carries state forward from run to run. The
r1 fold put that state in artifacts. Each fold since then has added a refusal around one way of reading those
artifacts. Each refusal then had an edge of its own:
- the trust predicate checks who ran, not which code ran (F3);
- the fail-closed schema rule turns into fail-open after 90 days (F2);
- the epoch is a free string (F5);
- the concurrency group is global (F6);
- the lookup loop can be flooded (F7).

**Can a redesign remove it?** Yes, for all of F2-F8. Every one is about carrying state forward through storage
that is mutable, expiring or multi-writer. None is in code the design merely governs. F1 is a different case
(§4).

## 2. Root cause

**The gate uses carried-forward state that it can open on, and that state is in expiring, multi-writer CI
storage.** The gate must then INFER which writer was legitimate from run metadata, and every inference has an
edge. The brief proposed the phrase "the gate trusts mutable, PR-reachable, expiring CI state". That is right,
with two refinements, both checked against the findings.

1. **The inputs that matter are those that can LOOSEN.** A PR-produced artifact that says "miss" can only close
   the switch, and a forged one costs a day of today's selection. One that says "clean", or the absence of a
   miss, can open it. All six r3 fold-caused findings are about a loosening path. Each is a way to lose a miss,
   gain a clean, or substitute evidence:
   - F2 erases a miss;
   - F3 writes old decisions;
   - F4 supplies the delta;
   - F5 erases a miss;
   - F6 cancels the writer, which feeds F2;
   - F7 fails the writer, which feeds F2.

   No finding is about a forged miss. Each was checked against the r3 constructs in
   `docs/reviews/claude/plan-586-r3-claude.md`.
2. **CARRY-FORWARD is the multiplier, not PR-reachability alone.** The read sets (F1) are also PR-reachable CI
   state, but each recording stands alone at its sha. A bad restore costs one PR's selection, and expiry costs
   nothing but a fallback to today's rule. The ledger is an accumulator. One bad write is inherited by every
   later run, because "a PR already decided in the newest ledger keeps that decision" (spec §2, line 356). So
   every way of mis-choosing the predecessor becomes a permanent loss. That is why the ledger thrashes and the
   cache does not.

So the class is: **loosening state carried forward through storage that the repository's review process does not
own.** In this repository the only store that review owns is the default branch. Its required checks
(`verify`, `schema-gates`, `mutation-sweep-complete`) were MEASURED with
`gh api repos/{owner}/{repo}/branches/master/protection` on 2026-11-09. Merges go through the dual-review process.
The plan already relies on that store for two inputs: `switch_gate` reads `docs/backlog.md` and `Q1_DECISION` at
BASE, and neither has drawn a finding since the r2 fold put them there (r3 "What holds": X-F1 and X-F2 hold).

## 3. The designs considered

### D0 — keep the artifact ledger and fold r3's seven fixes (accrete)

The fixes, each from r3:
- explicit genesis (`genesis: true` dispatch, or a committed `LEDGER_GENESIS`) and an alert on `shadow-compare`
  failure (F2);
- `code_sha` with ancestry, plus `run_attempt == 1` (F3);
- `q1_probe_delta` computed by the comparator (F4);
- `EPOCH_RESET_FROM`, with a strictly later date (F5);
- `if:` on the default branch only (F6);
- a pre-filter on the artifact list's `workflow_run` fields (F7);
- a selector-blob key (F8).

- **Spec change:** none. Each fix is a refusal inside spec §2's wording.
- **Cost:** seven more mechanisms on Task 7.2, with about 14 more cases.
- **Why it is not the recommendation:** the store still expires, and the predecessor is still chosen by
  inference. The next round can attack:
  - the genesis input (who may dispatch `genesis: true`);
  - the alert's own failure;
  - `run_attempt` semantics (UNVERIFIED in r3: does `upload-artifact@v4` accept a repeated name in a later attempt?);
  - the interaction of `EPOCH_RESET_FROM` with a revert.

  This is the pattern of §1. The r2 coordinator logged this exact bet as `redesign`, and r3 refuted it. The ladder
  (`scripts/check-decision-scheme.py`) does not allow it again on this unit.
- **Kept as the owner's fallback** if the spec change in §5 is declined. Per-finding fixes are in the coordinator
  doc.

### D1 — the ledger is a committed file read at BASE; the comparator writes stateless reports (RECOMMENDED)

The r3 reviewer's proposal, made concrete. One principle: **an input that can open the switch is read at BASE,
from a file changed only by a reviewed, guarded pull request. Anything read from Actions storage may only close
the switch.**

- **The comparator is a pure report writer.**
  - `shadow-compare` (daily, on the default branch only, read-only token) re-scans every PR merged since the
    epoch start, as spec §2 already says ("STATELESS over its inputs").
  - It uploads `shadow-report-<run_id>` (90 days). It reads no earlier report and no earlier ledger artifact.
  - Two overlapping runs therefore write two independent reports. Neither can erase the other, and nothing needs
    serialising.
  - Each report carries `code_sha` (`GITHUB_SHA`), `run_attempt`, and the blob ids of `reach_select.py` and
    `shadow-compare.py` at `code_sha`.
  - It computes `q1_probe_delta` itself, with its own (default-branch) code (F4).
  - A sample counts only when its PR run's `selection-*` records a `selector_blob` equal to the report's own
    (F8). The PR run executes the merge commit's `reach_select.py`, so equal blobs mean the evidence was produced
    by the code being keyed. This is provenance by CONTENT, not by run metadata.
- **The ledger is `docs/shadow-ledger.json`.** It is created by slice 7's PR with `epoch.start` (today's
  `SHADOW_START`, moved out of the script) and no rows.
  - It is changed by an ABSORB pull request: `shadow-compare.py --absorb` is run locally with a read-only `gh`.
    It merges every trusted report newer than the ledger's `absorbed_through`.
  - The absorb commit rides the coordinator's ordinary docs batch, so it costs no extra PR.
  - A guard, `scripts/check-shadow-ledger.py`, runs in the required `verify` job and compares BASE's ledger with
    HEAD's. It refuses:
    - a removed or altered decided row;
    - a drop in `miss` or `post_switch_events`;
    - an added row that no TRUSTED report holds with identical content;
    - a report whose `code_sha` is not an ancestor-or-equal of BASE (F3);
    - a report whose `reach_select.py` or `shadow-compare.py` blob differs from BASE's (F3: old code cannot
      write);
    - an epoch change that does not append the old epoch verbatim to `previous_epochs`, does not start strictly
      later, or does not carry a non-empty `reset_by_owner` (F5).
  - "Trusted report" uses the same run predicate the plan has today: `schedule`/`workflow_dispatch`, `ci.yml`,
    the default branch, the same repository. Candidates are pre-filtered on the artifact list's `workflow_run`
    fields before any lookup (F7). Any failure refuses the absorb, and a refused absorb leaves the switch where
    BASE has it.
  - `check-merge-ready.py` gains one HOLD reason: a change to the ledger's `epoch`. Spec §7 Q5 makes a revisit
    the owner's, and a HOLD makes it a machine, not the PR-body convention the plan has now (F5's residue).
- **The gate reads two things.**
  - **The loosening inputs, at BASE.** `switch_gate` reads `git show BASE:docs/shadow-ledger.json`, beside the
    backlog and `Q1_DECISION`. It opens only when the committed ledger shows:
    - at least 20 consecutive complete clean rows under the epoch's `selector_blob`, which must equal
      `git rev-parse BASE:scripts/reach_select.py` (F8);
    - 0 misses and 0 post-switch events;
    - a decided Q1 delta;
    - an `absorbed_through` no older than 14 days. A stale ledger refuses, so a comparator or absorb that stops
      running fails CLOSED. This is the inverse of F2.
  - **The tightening input, from Actions.** Every trusted report newer than `absorbed_through` is read
    (`actions: read`, already held). Any miss or post-switch event in ANY of them, or a listing failure,
    refuses. The read is a UNION over reports, so the newest report omitting a miss cannot hide it (F3, F5 in
    the window). A forged or untrusted report could at most close the switch.
- **What it removes from slices 7-8:**
  - `newest_trusted` as a predecessor search;
  - the "no trusted ledger → empty ledger" genesis rule (F2's root: genesis is now the file's creating commit);
  - the schema hard-failure of the writer;
  - the `shadow-ledger` concurrency group and its case (F6's subject: reports do not race);
  - the epoch-by-string-equality rule (F5's subject);
  - the per-candidate lookup on the WRITER path (F7's subject: only the gate's tightening read and the absorb
    guard list artifacts, and either failing refuses);
  - `q1_probe_delta` in `selection-*` (F4).

  `trusted_ledger` survives, renamed `trusted_report_run`. Every remaining use of it is fail-closed and inherits
  nothing.
- **What it adds:**
  - one guard script (W1-W8; ADR-0014: a pure `ledger_change_errors(base_doc, head_doc, reports)` with the fetch
    injected);
  - one committed JSON file;
  - one HOLD reason in `check-merge-ready.py`;
  - `actions: read` on `verify`, or on a small `ledger-guard` job if `verify`'s token is to stay untouched;
  - a recurring absorb step for the coordinator, at least every 14 days while the switch is open, or the gate
    closes itself.

  It adds no write permission anywhere, and every job keeps a read-only token.
- **Spec change: YES.** §5 quotes the sentence it contradicts and gives the diff.

### D2 — no persisted ledger: the owner flips a reviewed constant after reading a shadow report

`shadow-compare` writes stateless reports. `switch_gate` reads `SWITCH = "off"` at BASE. The owner reads a report
showing 20 clean, 0 misses and the Q1 delta, then approves a PR that flips the constant, with the report committed
as evidence.
- **Spec change: YES, and a larger one.** It contradicts the same §2 sentence, and it adds an OWNER act to every
  switch-on. Spec §7 Q4 sets a measured condition, not an owner's reading. The plan's Global Constraint (r1
  Claude F2) chose a machine precisely because a prose precondition is worthless under merge-when-READY.
- **Weakness:** after the switch, spec §8.1 wants one event to "stop the switch, or revert it". Without a
  committed latch, the stop must come from Actions storage or issues, and those are expiring or deletable, which
  is the class again. A reviewed revert is the only durable stop, and it waits for a human.
- **Rejected:** it costs the owner's attention, which is the scarce resource, and it buys nothing over D1.

### D3 — a master-only job writes the ledger and opens a bot pull request

- **Spec change: YES.** Spec §2 gives the comparator a "read-only token" (line 354). Opening a PR needs
  `contents: write` and `pull-requests: write`, which also breaks the plan's "No new job gets a write
  permission".
- **Mechanism gap:** GitHub does not start workflow runs for events created with `GITHUB_TOKEN` (documented, not
  exercised here). A bot PR would therefore never get its required checks (`verify`, `schema-gates`,
  `mutation-sweep-complete`) and could not merge under merge-when-READY without a PAT or an App, which means a new
  secret.
- **Rejected:** more permissions and a secret, to automate a step D1 rides on an existing docs batch.

## 4. F1 (PR-scope read-set cache): is it the same class?

**Partly.** It is PR-reachable CI state that LOOSENS: rule 3 drops picks. But it is not carried forward. Each
read set stands alone at its sha, and expiry or eviction costs only a fallback to today's rule. It cannot move to
git: there is one payload per master sha, saved on every push. So D1 does not cover it, and it needs its own
refusal. That refusal is cheap and needs no spec change.

- **MEASURED** (`gh api "repos/{owner}/{repo}/actions/caches?per_page=3"`, 2026-11-09): every cache entry the API
  lists carries `ref` (both entries today: `refs/heads/master`). So `pick_cache` can filter on scope.
- **The fix, folded into Task 5.3 (slice 5):**
  - `pick_cache` keeps only entries whose `ref == refs/heads/<default branch>`.
  - It REFUSES (`key shadowed in <ref>`) when any entry with the chosen key exists under another ref. That covers
    the exact-key restore preferring the run's own scope, the r3 construct.
  - Spec §2 Resolve lists the cache entries, keeps ancestors, takes the nearest and validates. A scope filter and
    a shadow refusal are further fail-closed conditions inside that text. No spec change.
- **Residual, stated:** an entry created in the PR's own scope after the list and before the restore. That needs
  a workflow the PR itself adds and runs concurrently. It sits in the plan's existing bound (a PR that edits
  workflows "could stop calling `shard_targets` at all ... that is review's to catch"). Per GitHub's documentation
  (not exercised), a `refs/pull/N/merge` cache is visible only to that PR's runs, so the poisoning can reach only
  the PR that does it.

## 5. The spec change D1 needs, exactly

**The sentence it contradicts** (spec §2, *Shadow mode's data and its comparator*, lines 353-358):

> A new script, `scripts/shadow-compare.py`, run by a new scheduled job, `shadow-compare` (daily, read-only
> token). It is STATELESS over its inputs: each run re-scans every PR merged since the shadow start date (a
> constant in the script), so a comparison PENDING at one run is retried at the next and cannot fall out of a time
> window. **It uploads its result as `shadow-ledger-<run_id>` (90 days); a PR already decided in the newest ledger
> keeps that decision, so an input artifact's expiry cannot undo it.** An expired input with no decided row is
> INCONCLUSIVE, never clean.

The bold sentence makes the carry-forward an ARTIFACT chain ("the newest ledger"). D1 moves it into git, and that
is a change of mechanism, not an implementation detail the wording permits. "(a constant in the script)" also
moves: the start date goes into the ledger. **Note:** the plan ALREADY departs from this sentence. The r2 fold
renamed the artifact to the fixed `shadow-ledger` (plan line 776), while the spec says `shadow-ledger-<run_id>`.
The r2 coordinator wrote "The approved spec ... is NOT changed by this fold". D1's diff resolves that divergence
too.

**Proposed diff** (for the owner; NOT applied):

```diff
 - **The comparator.** A new script, `scripts/shadow-compare.py`, run by a new scheduled job, `shadow-compare`
-  (daily, read-only token). It is STATELESS over its inputs: each run re-scans every PR merged since the shadow
-  start date (a constant in the script), so a comparison PENDING at one run is retried at the next and cannot
-  fall out of a time window. It uploads its result as `shadow-ledger-<run_id>` (90 days); a PR already decided in
-  the newest ledger keeps that decision, so an input artifact's expiry cannot undo it. An expired input with no
-  decided row is INCONCLUSIVE, never clean.
+  (daily, on the default branch only, read-only token). It is STATELESS over its inputs: each run re-scans every
+  PR merged since the ledger's epoch start, so a comparison PENDING at one run is retried at the next and cannot
+  fall out of a time window. It uploads its result as a REPORT, `shadow-report-<run_id>` (90 days), and reads no
+  earlier report.
+- **The ledger.** A committed file, `docs/shadow-ledger.json`, changed only by a pull request that absorbs
+  reports. A guard on every pull request refuses a change that removes or alters a decided row, lowers a count
+  of misses, adds a row no trusted report holds, or moves the epoch without recording the owner's decision. A PR
+  decided in the ledger keeps that decision, so neither an input's nor a report's expiry can undo it. An expired
+  input with no decided row is INCONCLUSIVE, never clean. The switch reads the ledger at BASE, as it reads
+  `docs/backlog.md`; a report can only CLOSE the switch, never open it.
```

Nothing else in the spec changes:
- §7 Q4 ("The comparator's ledger reports the count") and §8.6 ("listed in the ledger") still read true.
- The 20-PR condition, the latch, Q1's fallback and Q5's revisit are unchanged in meaning.
- D1 is STRICTER than the spec in two places, and both are allowed by the wording: the selector-blob key, and
  the 14-day staleness refusal.

## 6. The rewrite of slices 6-8 that implements D1 (proposed; applied only after the owner approves §5)

**Slice 6** changes only by fields, and both D0 and D1 need them:
- `selection-*` gains `selector_blob` (`git rev-parse HEAD:scripts/reach_select.py` in the PR run);
- it loses `q1_probe_delta` (F4: the comparator computes it).

Everything else in slice 6 stands.

**Slice 7:**
- Task 7.1 (`--mutant` replay) is unchanged.
- **Task 7.2, `shadow-compare.py --report`:**
  - The job has `if: github.ref == format('refs/heads/{0}', github.event.repository.default_branch)`,
    `contents: read`, `actions: read`, and no concurrency group.
  - It reads the committed ledger at its own checkout only for `epoch.start` and to skip rows already decided.
  - It writes `shadow-report-<run_id>`:
    `{schema: 1, run_id, run_attempt, code_sha, selector_blob, comparator_blob, epoch_start, generated_at,
    q1_probe_delta, prs: {...}, post_switch_events: [...]}`.
  - Keep from today's text: `pushes`, `compare_push`, `replay`, `decide_pr`, drift and every §8.6 case.
  - Delete: `newest_trusted`, the predecessor merge, *Why the job-level group*, *Fail closed on the ledger
    itself*, *The epoch* and the ledger-artifact schema.
  - New cases:
    - a sample whose `selector_blob` differs from the report's → `not a sample`;
    - `q1_probe_delta` computed in-job.
- **Task 7.3 (new), the ledger, the absorb and the guard:**
  - Create `docs/shadow-ledger.json`:
    `{schema: 1, epoch: {start, selector_blob}, previous_epochs: [], absorbed_through: null, rows: {},
    q1_probe_delta: null, post_switch_events: []}`.
  - `shadow-compare.py --absorb LEDGER` merges the trusted reports newer than `absorbed_through`. A decided row is
    never overwritten, a miss is never dropped, and a report that the guard below would refuse is skipped and
    logged.
  - Create `scripts/check-shadow-ledger.py --base REF` (W1-W8). Its rule, `ledger_change_errors(base_doc,
    head_doc, reports, blobs_at_base, is_ancestor)`, is pure, and the fetch is injected (ADR-0014). Its
    refusals are the ones listed in §3 D1.
  - Caller: a `verify` step (the job gains `actions: read`).
  - Its cases, each with an adjacent pass:
    - a removed row;
    - a `miss` → `clean` change;
    - a lowered `miss` count;
    - a row in no report;
    - a row that differs from its report;
    - a report from a `pull_request` run;
    - a report whose `code_sha` is a non-ancestor;
    - a report with an old `reach_select.py` blob;
    - an epoch moved backward;
    - an epoch moved forward without `reset_by_owner`;
    - an epoch moved with `previous_epochs` altered;
    - a PR that does not touch the ledger → rc 0, "ledger unchanged".
  - `scripts/check-merge-ready.py`: a HOLD reason `shadow-ledger epoch changed` (WM pins), with its case and an
    adjacent case where rows are added and the epoch is unchanged → no HOLD.

**Slice 8:**
- Task 8.0 is unchanged. Note: reverting 3(c) to option A changes `reach_select.py`'s blob, so the 20-PR count
  restarts under the new rule. That is correct, because the rule changed. Its cost is stated, not avoided.
- **Task 8.1:**
  - `switch_gate` and `q1_at_base` move to a new module, `scripts/reach_gate.py`, which goes in `SELECTOR_FILES`.
    This keeps the evidence key, `reach_select.py`'s blob, from moving when the GATE is edited.
  - `switch_gate(backlog_at_base, ledger_at_base, q1_decision, selector_blob_at_base, reports, today)` refuses,
    in this order:
    - `backlog #590 open` (unchanged);
    - `no ledger at BASE` (absent or schema);
    - `selector changed since epoch`;
    - `latched miss`;
    - `N of 20 clean PRs`;
    - the two Q1 clauses (unchanged, with the delta read from the ledger at BASE);
    - `ledger stale` (`absorbed_through` more than 14 days before `today`);
    - `unabsorbed miss` (any trusted report newer than `absorbed_through` with a miss or a post-switch event);
    - `reports unreadable` (a listing or download failed).
  - `shard_targets` and the workflow-level cases are unchanged.
- **Task 8.2:** `post_switch` is unchanged. The daily report records hits, the gate's tightening read closes the
  switch on the next PR, and the absorb makes the hit permanent.

**Global Constraint *Trust and provenance***, rewritten as one rule: an input that can open the switch is read at
BASE. Actions storage can only close it, or, at absorb time, be checked against BASE's code by the guard.
Clauses (a) and (b) stand. Clause (c) becomes the absorb guard.

## 7. Slices 1-5: are they affected?

**No, except F1's fold in Task 5.3.** Each slice was checked against the plan text at `052c3579`.
- **Slices 1-3** (measurement, parser, classifier) read no ledger, artifact or cache.
- **Slice 4** saves `readsets.json` with `actions/cache/save` on master only (`record-reads`, Task 4.2 `if:`).
  Neither D0 nor D1 changes the save.
- **Slice 5**'s pure selector has one function that touches Actions storage: `pick_cache`, which is F1. Its fix
  is a scope filter and a shadow refusal (§4). It is folded into Task 5.3 at this commit.

So slices 1-5 can be built in order now (slice 1 first). The owner's answer on §5 is needed before slice 6
starts, and slice 6 starts only after Task 4.3's post-merge observations, so that answer is not on the critical
path for days.

## 8. Stop condition

The next review of `ledger-trust` is r4, past the cap (`docs/review-method.md` §0 Q4c). Its findings are FILED
unless they are BLOCKERs.

**A BLOCKER is either:**
- a path by which an input that is NOT in a file at BASE opens the switch, or keeps it open after a trusted report
  holds a miss;
- a path by which a committed ledger change that loses a decided row or a miss passes `check-shadow-ledger.py`.

**Out of scope (stated, not defended):**
- a PR that edits `ci.yml` or adds a workflow to stop calling the guard or the gate. This is the plan's existing
  bound, and review's to catch;
- a dishonest `reset_by_owner` text. The HOLD puts it in front of the owner, and the text cannot prove it was
  the owner;
- GitHub returning false run metadata.

**Pre-committed retreat.** If the owner declines §5, the fold is D0 with the seven per-finding fixes in the
coordinator doc. It is logged as the next rung on a NEW unit, because the ladder refuses a retry. If a round
after D1's fold finds a defect caused by THAT fold, the arming count starts again: the design question then has
an answer, and §6 is what a fold is checked against.

## 9. Not written down until now

**Trust is asymmetric. Inputs that can LOOSEN a gate must come from where review lives; inputs that only TIGHTEN
can come from anywhere.** r1 framed the ledger as a store to protect. Every reviewer then attacked how its writer
was chosen, and every fold accepted that framing. The missing sentence is *"the switch opens only on what the
default branch says; Actions storage can only close it."* Once that is said:
- the predecessor search, the genesis rule, the concurrency group and the epoch string all stop being
  load-bearing;
- they fail closed or disappear;
- the one remaining inference, the absorb guard's report trust, is checked at a single point and inherits
  nothing.

This sentence goes into the plan's Global Constraints when §6 is applied.

## 10. Could not verify

Each item below is from GitHub's documentation, not exercised:
- the artifact list's `workflow_run` fields (the repository has 0 artifacts today, MEASURED:
  `gh api "repos/{owner}/{repo}/actions/artifacts?per_page=2"` → `total_count` 0);
- that a `refs/pull/N/merge` cache is visible only to that PR;
- that an exact-key restore prefers the run's own scope;
- that `GITHUB_TOKEN` events start no workflow runs;
- `upload-artifact@v4` on a re-run attempt.

D1 relies on NONE of these to open the switch. The first two bound F1's residual. No code of slices 6-8 exists,
and none was run.
