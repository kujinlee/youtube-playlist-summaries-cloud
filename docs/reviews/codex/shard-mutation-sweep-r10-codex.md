<!-- codex-review: model=gpt-5.5 -->

**Verification**

Worktree: current branch `shard-mutation-sweep` at `1fb8ef92`; dirty files are only generated `docs/explainers/*` plus untracked `docs/reviews/claude/shard-mutation-sweep-r10-claude.md`, matching the ignore note.

`python3 scripts/check-plan-code.py --self-test`:

```text
178/178 passed
```

Independent manifest check:

```text
entries 1211
anchors 1219
missing 0
ambiguous 0
duplicate_anchor_tuples 0
```

Required contexts from GitHub branch protection:

```text
["verify","schema-gates"]
```

`python3 scripts/check-merge-ready.py --pr 366`, verbatim:

```text
pull request           : #366
base                   : origin/master
pull-request-only steps: 2 derived from ci.yml — dashboard entry ratchet, check-review-recorded (PR only)

  ok  dashboard entry    rc=0  ok — an entry block was added
  ok  review recorded    rc=0  ok — review recorded in this range: docs/reviews/claude/shard-mutation-sweep-r1-claude.m
  NO  review rounds      rc=1  ⚠ verdict corpus: 224 read — 32 meaningfully checked below, 192 PRE-CUTOVER (schema < 3:
  NO  mergeability       rc=1  mergeStateStatus is BLOCKED
  ??  CI                 rc=2  still running

CANNOT RUN — CI could not reach what they measure. Treat this as NOT RUN.
  ⚠ A local gate sweep cannot answer the pull-request-only checks above. That is why this script exists and why 'all my gates are green' is a different claim.
```

`gh pr checks 366 --watch=false` currently shows `verify`, `schema-gates`, and `mutation-sweep (1..8)` all pending on `1fb8ef92`; `prod-drift` is skipping. So I cannot confirm current-head CI green. Marked **NOT MEASURED** until those complete.

**Findings**

Low · INSTRUMENT · caused by previous fold: `docs/dashboard-entries.md` still says “#235 the home-escape scan is the one global check riding only on the non-required matrix.” That is now false after the `1fb8ef92` backlog amendment: #235 correctly names **two** checks, home-escape scan and anchor resolution. This is a merge-artifact stale sentence, not a deliverable defect.

Low · INSTRUMENT · caused by previous fold: backlog #235’s title/body now names both checks, but its candidate fix still only says to give `home_escapes()` a `--self-test` caller. The row’s `FAILS IF` includes unresolved/ambiguous anchors, so the falsifier is right; the action sentence is incomplete and could let someone close the row after fixing only half. Not merge-blocking, but worth filing or amending later.

| Severity | Deliverable Or Instrument | Caused By Previous Fold? |
|---|---|---|
| Low | Instrument, dashboard merge artifact | Yes |
| Low | Instrument, backlog row action text | Yes |

**What I Tried To Refute And Could Not**

I enumerated what `verify` used to catch via the old unsharded sweep. The matrix still catches mutation survivors, unattributed kills, suite timeouts, red before/after controls, count drift, missing target manifests, invalid/empty JSON, duplicate names, duplicate anchor-tuples, file/name disagreement, home-escape routes in targets/replacements, and unresolved/ambiguous anchors. Of those, `verify --self-test` still has a second home for manifest load/count/duplicate/file-name checks. The items without a second required-context home are the two Claude named, plus the intentional execution verdicts themselves; I did not find a third cheap global manifest preflight beyond home-escape scan and anchor resolution.

I tried to construct a green PR over unmeasured work: cancelled shard, skipped shard, timeout, failed shard, aggregator rerun alone, one-job rerun, missing `mutation-sweep-complete`, and missing `ffmpeg` in the matrix. Each either fails loud through `needs.mutation-sweep.result != success`, remains pending/red, or is already #230’s observational-scope row. No new reachable green-over-unmeasured state found.

I checked backlog rows #233, #234, #235, #230, #232. #235 is now mostly corrected, but its candidate fix is still incomplete as above. I found no other row wrong about its own subject.

I checked merge artifacts changed since round 9: PR body now says nine rounds and carries the #235 correction; backlog #235 is amended; dashboard tail still has the stale one-check phrasing. The commits after round 9 remain docs-only: `docs/backlog.md`, `docs/dashboard-entries.md`, and `docs/reviews/claude/shard-mutation-sweep-r9-claude.md`.

**Verdict**

**CONVERGED** on the deliverable. This is the second consecutive clean round for the merge criterion: no Blocking, no High, no deliverable finding, and no non-trivial fix required.

Should this merge? **Yes, after current-head CI finishes green and this Codex half is filed so `check-merge-ready.py --pr 366` returns rc=0; no code or tracked-file change is required first.**
