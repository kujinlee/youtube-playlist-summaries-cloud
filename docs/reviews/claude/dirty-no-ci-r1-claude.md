Reviewed head: 664ff4f0eac86168930a52fbd085cc6d9f602f69

# dirty-no-ci (PR #539, backlog #545) — round 1, Claude half

Mandate: REFUTE. Priority 1 is a silent miss: a dirty PR with no CI that the line fails to name. Priority 2 is a
false alarm.

## What was run

- `python3 scripts/check-stalled-work.py --self-test` at the reviewed head: **203/203 passed** (21.7 s).
- Scratch copy from `git archive HEAD`. 16 fixture gh nodes went through the script's own seams
  (`own_prs` → `pr_fact` → `pr_item`, plus `render` → `hook_block`). Results are quoted per finding below.
- The real script, run once, read-only, without `--hook`: rc 0, 6 open PRs all `OK`, no `DIRTY-NO-CI` at that moment.
  So the live path is still exercised only by fixtures. That matches the PR body.
- **Hand-checked 2 new mutations**, each in its own scratch copy:
  - `545: mergeable UNKNOWN is read as a conflict` goes red on its named case: `[FAIL] 545: mergeable UNKNOWN
    (GitHub still computing) is not a conflict: got True want False`. That is 202 passed, 1 failed.
  - `545: items_from says every head has a run, so a conflict is never reported` is a mutation at a call site. It
    goes red on its named case, `collect over a DIRTY no-run PR ... reports ONLY the first: got (0, []) want (1,
    [...])`, and on 3 more (the hook block, the fresh dirty draft, and the end-to-end gh wrapper). That is 199
    passed, 4 failed.

## Probes that did NOT refute (recorded so the next round does not redo them)

| Input (CONFLICTING unless stated) | Result |
|---|---|
| future commit date (+1 d) | `DIRTY-NO-CI`, "last commit 0m ago", age_s −79200 (see R1-F4) |
| unparseable `committedDate` / key missing | `DIRTY-NO-CI`, "head commit date unknown" |
| `commits: null`, `nodes: []`, last commit oid ≠ head, bad `headRefOid` | `DIRTY-NO-CI`, "no CI run seen for its head" (fails closed) |
| `statusCheckRollup` key absent | `DIRTY-NO-CI`, worded "no CI run on its head" (see R1-F5) |
| rollup `{state: SUCCESS}` (a head whose only runs were skipped) / `{state: null}` | `OK`. The head shows a check, so this is not a "waiting on nothing" case |
| `isCrossRepository: true` | dropped, by design |
| stale draft, conflicting, head HAS a run | `STALLED-DRAFT`, so the draft rule still applies |
| missing `mergeable` | CANNOT RUN (self-test and fixture agree) |

**A head whose only runs are CANCELLED or SKIPPED**, or whose only run came from a `push` event, is not a miss in this
repo. `ci.yml` and `schema-gates.yml` run on `push` only for `master` and `batch/**`. A PR head that is the tip of
either of those cannot be CONFLICTING with master. A cancelled or skipped run on the head shows in the PR's checks, so
it does not read as "waiting".

**Truncation of `statusCheckRollup`:** none is possible. The query asks only for `statusCheckRollup{state}`, a single
scalar, and no connection is paged. Over 100 PRs is already CANNOT RUN.

**Exception paths:** `head_has_run` catches only `KeyError/IndexError/TypeError`, and returns `None`, which the item
reports as "no CI run seen". `pr_item`'s new branch has no other raising operation. I found no path that prints
nothing.

## Findings

### R1-F1 — Medium — a DIRTY-NO-CI line is the first one cut by the hook's 8-line cap, because it sorts last within tier 0

`scripts/check-stalled-work.py:135` puts `DIRTY-NO-CI` in the same tier as `STALLED`, `STALLED-DRAFT` and
`UNKNOWN-DRAFT`. `:567` sorts within a tier oldest-first. `:602` keeps that order through a stable sort, and the block
keeps only `shown[:HOOK_MAX_LINES]`.

A DIRTY-NO-CI head is young by nature: it is the thing just pushed. Its age is 0 when the date is unknown (`:457`),
and negative when the date is in the future. An unpushed `STALLED` tip, by contrast, is at least 30 minutes old by
definition. So whenever tier 0 already holds 8 or more lines, the DIRTY line is the one dropped.

**Input:** 8 `unpushed_item`s aged 1–8 h, plus `pr_item(#529, conflicting, headRun False, 10 m old)`, put through
`render` → `hook_block`.
**Result:** `DIRTY line in block: False`, and the block's last line reads `stalled-work: showing 8 of 9 (STALLED 8,
DIRTY-NO-CI 1)`.

Only the count survives. The PR number and the remedy are gone, and the remedy is the one action that unblocks a wait.
This is the exact silent miss the slice exists to close, re-created by the cap.

**Fix:** give `DIRTY-NO-CI` its own tier ahead of `STALLED`. It is the only state whose cost grows while someone
waits on it. Alternatively, sort tier 0 so that it comes first. Add a case where 8 older STALLED lines and 1 DIRTY line
leave the DIRTY line in the block.

### R1-F2 — Low — `mergeable: UNKNOWN` (or any value other than CONFLICTING) is silent, with no NOTE, and is invisible even in the CLI's OK line

`:435`: `conflicting = r["mergeable"] == "CONFLICTING"`. `:408` checks only that the value is a string. So `UNKNOWN`,
`""` and any value outside GitHub's enum read as "no conflict".

**Probe:** `UNKNOWN`, `"conflicting"` (lower case) and `""` all gave `OK | #1 b: last commit 2h00m ago`. The OK
line does not show mergeability, so in the full CLI listing a PR GitHub has not yet computed looks exactly like a clean
one.

**When this matters:** UNKNOWN is what GitHub returns right after a push to the PR, or after master moves. That is
exactly when a DIRTY state comes into being.

**Re-checked?** Yes, once per prompt. `:70` says NO CACHE, and the self-test asserts that no cache directory is
created. A transient UNKNOWN therefore heals on the next prompt, if GitHub has finished computing.

**Unmeasured:** whether a GraphQL *list* query triggers GitHub's background mergeability job. This is an inference from
the REST documentation, not observed. If it does not, a PR that nobody opens could read UNKNOWN for a long time, with
nothing said.

**Fix:** keep UNKNOWN out of DIRTY. When `mergeable` is UNKNOWN, the head has no run and the head is older than a few
minutes, emit a NOTE ("mergeability not computed yet"). Refuse a value outside {MERGEABLE, CONFLICTING, UNKNOWN} as
CANNOT RUN, as is already done for a non-string.

### R1-F3 — Low — the remedy and the premise assume the PR's base is master; a stacked PR gets the wrong remedy

`:461` always says "merge origin/master into the branch". The query (`GH_QUERY`, `:142`) does not read
`baseRefName`.

`mergeable` is computed against the PR's **base**. Both workflows run `pull_request` only for `branches: [master]`. So a
PR whose base is another branch never gets `pull_request` CI at all, conflicting or not. When it conflicts with its
base, the line says DIRTY and tells the reader to merge master, which neither resolves the conflict nor starts CI.

This is a false alarm: the remedy is wrong. Not measured against current PRs; none of the 6 open now was inspected for
its base.

**Fix:** query `baseRefName`. Report only PRs based on master, or name the base in the line.

### R1-F4 — Low — a future head commit date gives a negative `age_s` and prints "0m ago"

`:457` computes `int(now - commit_ts)` with no floor. `fmt_age` floors only the text.

**Input:** committedDate one day ahead.
**Result:** `age_s -79200`, "last commit 0m ago".

The line is still reported, so this is not a miss. But the negative age sorts the line below every other tier-0 line,
which feeds R1-F1. A committer's clock skew is enough to cause it.

**Fix:** use `max(0, …)`, or treat a future date as unknown.

### R1-F5 — Low — a reply with no `statusCheckRollup` key is worded as a measured absence

`:390`: `commit.get("statusCheckRollup") is not None`. A missing key is treated like an explicit `null`.

**Probe:** with the rollup key absent, the line reads "no CI run on its head". It should read "no CI run seen", the
wording the code already uses for an unknown head.

The verdict still fails closed: a conflicting PR is reported either way. Only the wording claims a measurement that was
not made. A schema change, or a query edit like the existing mutation that drops `statusCheckRollup{state}`, would
produce this shape.

**Fix:** `"statusCheckRollup" not in commit` → `None`.

## Summary

The core verdict is sound and fails closed on every malformed-reply shape I built. The self-test and the 2 hand-checked
mutations bite. One Medium remains: R1-F1, where the 8-line cap drops the DIRTY line in favour of older tier-0 lines,
which re-creates the silent miss this slice exists to close. Four Lows, each with a cheap fix.

VERDICT: NOT CONVERGED
