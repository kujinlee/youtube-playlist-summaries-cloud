Reviewed head: 36ab1546f7ed2a5f15110d18a98da6bcaa8bcd8a

# Round 3 — `dirty-no-ci` (PR #539, backlog #545) — Claude half (adversarial)

Scope: the r2 fold (`git show 36ab1546`) and then `git diff origin/master...HEAD`, with the weight on
`scripts/check-stalled-work.py` (`own_prs`, `head_has_run`, `pr_item`, the hook tiers), its cases and its mutations.
Mandate: refute the decision-log prediction for `dirty-no-ci`, which says r3 brings no admissible finding in which a
field gh returns, missing, truncated, malformed or mid-computation, yields a confident diagnosis or silence.

**The prediction is refuted** by R3-F1 (a missing field gives the confident diagnosis) and R3-F2 (a skewed date gives
silence). **R3-F2, R3-F3 and R3-F4 were caused by r2's fold**, in the same component (`stalled-work-dirty-pr`) as r2's
three fix-induced findings. That makes two consecutive fix-induced rounds: THRASHING, and the architecture review
fires. R3-F1 was not caused by r2: the code dates from r1's fold, and r2's class audit missed it.

## What was run

- `python3 scripts/check-stalled-work.py --self-test` at HEAD: **225/225**.
- Probe scripts that import the module and call the pure functions with constructed inputs. They are
  `probe.py` and `probe2.py` in the session scratchpad (`.../scratchpad/r3/`).
- One read-only `gh api graphql` over the last 40 PRs (`commits(last:10)`, each commit's `committedDate` and its
  check suites' `createdAt`), saved as `heads.json`: 187 heads with suites.
- The real script, read-only, against GitHub: rc 0, 6 open PRs, all `OK` (no DIRTY / MERGE state live right now).
- **Mutations.** I ran the 23 manifest entries that r2 added or re-bound, one at a time, in a copy of `scripts/`
  plus `.claude/hooks/` outside the repo. The control gave rc 0 and 225/225. The harness's rule is rc 1, with every
  `expect` among `parse_fail_names` (the function copied from `scripts/check-plan-code.py`). **All 23 pass it.**
  Every one of the 133 anchors binds exactly once in HEAD's source. This was not a full `--mutate` sweep.

## Findings

### R3-F1 — Low — a suite node MISSING `workflowRun` (or its `event`) is read as a measured "no PR CI", and the no-CI diagnosis with its forced merge follows

- **Where:** `scripts/check-stalled-work.py:434`, `(n.get("workflowRun") or {}).get("event") == "pull_request"`, and
  then `:436`, `return False if total == len(nodes) else None`.
- **Input:** a CONFLICTING, master-based row whose head suites are `{"totalCount": 1, "nodes": [{}]}`. The same
  happens for `[{"workflowRun": {}}]`, `[{"workflowRun": {"event": null}}]` and `[{"workflowRun": {"evnt": "pull_request"}}]`.
- **Result** (`probe2.py`, through `own_prs` then `pr_item`): `headRun False`, giving `DIRTY-NO-CI` with the
  action "CI will not run until master is merged in — merge origin/master into the branch and push", for all four.
- **Why it matters:** the query asks for `workflowRun{event}`, so a well-formed reply always has the key, `null` when
  there is no run. A node without it is a malformed reply. r2's class audit fixed two cases of exactly this
  shape: nodes that are not a list, and a boolean `totalCount`. Its table says "every field the parser reads" was
  audited, but its rows stop at `checkSuites.nodes` and `totalCount` and never reach the per-node `workflowRun` /
  `event`. A missing key is read as null, null is read as "no run", and with a complete page that is a
  **measured none**. That is the confident diagnosis the prediction rules out.
- **Fix:** each node must be a dict holding a `workflowRun` key whose value is `None` or a dict with a string
  `event`. Anything else makes `head_has_run` return `None`, so the PR is DIRTY-UNSEEN. Add a case and a mutation.
- **Reachability:** none from today's gh, since GraphQL returns the fields it is asked for. The two audit
  items r2 did fix are no more reachable than this one.
- **fix_induced: no** (not caused by r2's fold). The read came in with r1's fold (R1-F1's rewrite to check
  suites), and r2's audit missed it.

### R3-F2 — Low — a head dated in the FUTURE gets the merge grace for the whole skew, so an UNKNOWN head stays silent

- **Where:** `:510` floors the age at 0, `age = 0 if commit_ts is None else max(0, int(now - commit_ts))`. That
  floored age then feeds the grace test at `:528`, `if commit_ts is not None and age <= MERGE_GRACE_S:`. The claim
  it breaks is at `:151`: "the grace can only end EARLY ..., never late".
- **Input:** an UNKNOWN, master-based head with no PR CI and `committedDate` 6 h or 1 day after `now`.
- **Result** (`probe.py`): `MERGE-PENDING` for both. That status is not a stalled state and not a hook tier, so the
  check exits 0 and the hook prints nothing. It stays that way until the clock passes the commit date plus 300 s.
  The cases cover the past side of the grace (60 s, grace + 1 s, undated) and never a future date.
- **Why it matters:** R1-F4's floor was written for a DIRTY line's *displayed* age, where 0 is harmless. r2 reused the
  floored value as "young enough to be left to GitHub". A committer date is whatever the committing machine's clock
  (or `GIT_COMMITTER_DATE`) said, so it is not "never after the push". A skewed field becomes silence, which is the
  prediction's class.
- **Reachability:** measured low. Of 187 real heads, none has a committed date after its first suite.
- **Fix:** give no grace when `commit_ts > now` beyond a small tolerance. A future date is an unmeasured age, the
  same rule as an undated head. Add a case and a mutation.
- **fix_induced: yes** (the grace is r2's).

### R3-F3 — Low — the grace counts from the COMMIT date, but its 300 s was measured from the PUSH, so 28% of real pushes get no grace and R2-F2's noise remains

- **Where:** `:147-152`. The comment derives the 300 s from "the first `pull_request` workflow run was created 2 s
  to 111 s ... after the head's **first check suite**". That is a push-relative interval. The code at `:528` counts it
  from `committedDate`.
- **Input:** the measured `committedDate`-to-first-check-suite interval (a proxy for "pushed after committed") on 187
  real heads from the last 40 PRs: min 5 s, **median 45 s, max 3270 s; 53 of 187 (28%) over 300 s**, 6 over 30 min.
  Constructed case: a commit made 20 min before its push, read 30 s after the push, gives `UNKNOWN-MERGE`
  (`probe2.py`). That is the hook item R2-F2 said fires "the instant it is pushed".
- **Why it matters:** the docstring (`:97-98`) admits "a commit pushed long after it was made gets none". But here,
  committing, then reviewing or testing, then pushing is the normal flow: about one push in four. The derivation
  "5 min is that maximum with room" measures a different interval from the one the code times, so the
  measurement does not support the constant as it is applied. This is noise, not silence, so it is outside the
  prediction's class.
- **Fix:** anchor the grace on what was measured. Add `createdAt` to the `checkSuites` query and count from the
  earliest suite. A head with no suites, or none dated, gets no grace, so it is never read as young. Or keep the
  commit-date basis and re-measure the constant on it. Either way the comment must state the interval it times.
- **fix_induced: yes** (the grace and its derivation are r2's).

### R3-F4 — Low — DIRTY-UNSEEN sits in the STALLED tier, so the 8-line cap cuts it first: R1-F1's defect, rebuilt for the new state

- **Where:** `:163`, where `HOOK_TIERS` puts `DIRTY-UNSEEN` in tier 1 with `STALLED`, sorted oldest first.
- **Input:** 8 unpushed `STALLED` tips aged 1 to 8 h, plus a CONFLICTING head whose suites were truncated (21 total,
  20 returned, none `pull_request`), committed 10 min ago.
- **Result** (`probe.py`): the capped block's item lines do not hold the DIRTY-UNSEEN line. Only the summary
  counts it, as "showing 8 of 9 (STALLED 8, DIRTY-UNSEEN 1)".
- **Why it matters:** r1 (Claude R1-F1) moved DIRTY-NO-CI into a tier of its own for one reason: a dirty head is
  young by nature, and it is the state whose cost grows while someone waits. That reason holds just as well for a
  conflict whose CI could not be seen. The conflict is MEASURED, and a CONFLICTING PR needs master merged in before it
  can merge, whatever CI did. The case `545 r2: DIRTY-UNSEEN is a stalled state in the hook's SECOND tier` pins the
  placement that gets cut. A truncated measurement leaves only a count in the hook, which is near-silence.
- **Reachability:** DIRTY-UNSEEN is rare: at most 4 suites on 132 heads, per the r2 measurement.
- **Fix:** put `DIRTY-UNSEEN` in tier 0 with `DIRTY-NO-CI`, and extend the R1-F1 cap case to it.
- **fix_induced: yes** (r2 added the state and chose its tier).

## Checked and not a finding

- **`BASE_REF_RE`.** `batch/**` is refused, which is correct: `*` is forbidden by `git check-ref-format` and GitHub
  cannot create such a branch, since it is a ruleset pattern, not a ref. Non-ASCII names (`fé/ünï`, `feature/über`)
  are accepted. `x..y`, `-x`, `foo.lock` and `@{u}` are accepted too, which is harmless because accepted means
  "not master". One edge case: a legal ref over 255 characters made of short components would be CANNOT RUN for
  the WHOLE check, since `own_prs` validates every node first. That fails loudly, not silently, and I did not show
  that GitHub allows such a name.
- **A PR that HAS run CI.** A head with a `pull_request` suite among the 20 returned is `True` even when truncated,
  and is never flagged. One whose `pull_request` suite is past the page is DIRTY-UNSEEN, with a conditional action.
  That is by design and worded as unmeasured. The real script against GitHub flags no open PR, including the
  owner-held ones (#376, #392).
- **A conflicting PR with no CI that is missed.** None found outside the documented non-master base. The
  `pull_request_target`, `merge_group` and upper-case event values read as no PR CI (`False`), which is right for
  this repo's workflows.
- **`head_has_run` against malformed pages.** `nodes` of `[None]` or `["x"]`, a `totalCount` of -1 or 1.0, and an
  empty commit list all give `None`. Only R3-F1's per-node keys slip through.
- **MERGE-PENDING through `collect`.** The status is 13 characters and fits the column. `hook_block` takes the first
  token, and MERGE-PENDING is not in `HOOK_TIER`, so it is never shown. The `collect` case confirms rc 0 and no
  block.
- **Mutations.** The 23 new or re-bound entries each go red with rc 1 on every named case. Two of them, "the grace
  is widened" and "DIRTY-UNSEEN leaves the hook's tiers", are killed by cases that pin constants, not by behaviour
  through `hook_block`. Each is also killed by a behavioural case (the r1 `collect` UNKNOWN case) or is plain data,
  so neither is a finding.

VERDICT: NOT CONVERGED
