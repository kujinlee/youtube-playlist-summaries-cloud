Reviewed head: a8a2760d86c2651a4a6a65ed3610e987e4e8a74e

# Round 3 — `sweep-sample-nightly` (backlog #651, PR #593) — Claude half

Scope: the r2 fold (`git diff ad7eee2e..a8a2760d`) in `scripts/session-state.py` (component `sweep-liveness`) and
`scripts/sweep-costs.py` (component `cost-table-builder`), plus the whole branch diff against `origin/master`.
Mandate: refute that the fold is correct.

```yaml
round: 3
half: claude
findings:
  - {id: C3-1, severity: MAJOR, component: sweep-liveness, fix_induced: true}
  - {id: C3-2, severity: MINOR, component: sweep-liveness, fix_induced: false}
  - {id: C3-3, severity: MINOR, component: sweep-liveness, fix_induced: false}
  - {id: C3-4, severity: MINOR, component: sweep-liveness, fix_induced: false}
```

## Gates run (this worktree, head a8a2760d)

| Check | Result |
|---|---|
| `python3 scripts/session-state.py --self-test` | 161/161 passed |
| `python3 scripts/sweep-costs.py --self-test` | 36/36 passed |
| `time python3 scripts/session-state.py` (3 runs) | 4.82 s, 4.70 s, 5.53 s wall |
| the same for `origin/master`'s `session-state.py` (2 runs) | 1.86 s, 1.74 s |
| `full_sweep_line` alone (live) | 2.77 s; 2 gh calls (`gh run list` ~1.0 s, one `gh api --paginate …/jobs` ~1.8 s) |

## C3-1 — MAJOR — `fix_induced: true` — component `sweep-liveness`

**A run whose matrix was ABANDONED reads as a fresh green sweep, because the shard set is never checked for
completeness and the summary job is ignored.** `scripts/session-state.py:866` `shards_verdict` counts only the
`mutation-sweep (k)` jobs that are LISTED, and the r2 fold decided `mutation-sweep-complete` "is not a shard" and
reads nothing from it. `fetch_sweep_jobs` (`scripts/session-state.py:811`) checks the listed count against the API's
`total_count`, but `total_count` counts the jobs that EXIST, not the jobs the matrix declared — so jobs that never
materialised are invisible to both checks.

**Breaking input — a REAL run, not a constructed one.** Scheduled run `42666878865` (2026-11-09, `c3ef94d7`): its
matrix had 24 shards (`git show c3ef94d7:.github/workflows/ci.yml` line 1204), but the jobs API lists only 10 jobs,
`total_count` 10 — shards 1, 2, 7, 10, 12, 15, 18, 20, 21 (all `success`) and `mutation-sweep-complete` (`failure`).
That job's log: `SWEEP: abandoned` / `FAILED — the sharded mutation sweep reported 'abandoned', not 'success'`; it
commented on sweep-red issue #548. Replayed through the branch's own functions (live `fetch_sweep_jobs`, then
`full_sweep_status` with `now` = 2 h after its `updatedAt`):

```
('fresh', 'last completed 2 h ago (run 42666878865, all 9 shards green).')
```

15 of 24 shards measured nothing, CI itself said so, and the line this branch adds to catch exactly that says
FRESH and green. Running `shards_verdict` over the 10 real scheduled runs on master today: this is the only
false-fresh among them, but the class is general — any run where a subset of the matrix's jobs is never created
(abandoned matrix, and plausibly a `re-run failed jobs` attempt under the default `filter=latest`, unverified)
passes the `total_count` check and every-listed-shard-green check.

**Why fix-induced:** r1's rule (the run's conclusion) would have said `failure` here; the r2 fold replaced it with
the shard rule and deliberately excluded the summary job — the one job that carries the matrix's aggregate result
(`needs.mutation-sweep.result`), which is the only signal that knows how many shards there should have been.

**Fix (suggested):** make the summary job evidence, not noise. A run SWEPT green only when every listed shard is
green AND `mutation-sweep-complete` is listed, `completed`, `success`; all shards green but the summary job absent
or not `success` → `unswept` ("the summary job says <conclusion>: the matrix did not complete"). A RED verdict
needs at least one failed shard (as now). Cheap belt-and-braces: the shard numbers must be exactly `1..max(k)`
(catches holes like 3-6 missing here; not a missing tail, which only the summary job can see). Add the real
42666878865 job list as a case.

## C3-2 — MINOR — `fix_induced: false` — component `sweep-liveness`

**The hook's worst-case time now exceeds its 60 s limit; the "55 s" claim omits a call.**
`scripts/session-state.py:93` and the docstring at `:32` sum `TIMEOUT + ISSUE_TIMEOUT + SWEEP_RUN_TIMEOUT +
SWEEP_JOBS_BUDGET` = 30 + 15 + 5 + 5 = 55 s "under the hook's 60" (`.claude/settings.json:207`). `collect` first calls
`main_checkout` → `_common_dir` (`:689`), a `git rev-parse` with its own 10 s timeout (more git calls when
`REGEN_MAIN_CHECKOUT` is set). Worst case: 10 + 55 = 65 s, plus Python start-up and up to `DRAIN` (1 s) per call
whose pipe is held. `origin/master` was 10 + 30 + 15 = 55 s; this branch adds 10 s and crosses 60. Input: GitHub
slow enough that every gh call hits its timeout while git is also slow (e.g. a loaded disk) → the harness kills
the hook and the whole IN FLIGHT block is lost, not just the sweep line (the `|| echo … CANNOT RUN` in
`session-state.sh` never runs when the hook itself is killed). Unlikely, but it is the bound the comment asserts.
Not fix-induced: r1 was 65 s too (run list 10 s), r2 improved it; the arithmetic in the comment is what is wrong.
**Fix:** count the git call (cut `TIMEOUT` to 25, or make `SWEEP_RUN_TIMEOUT` + budget come out of a single
overall deadline), and make the docstring list every call.

## C3-3 — MINOR — `fix_induced: false` — component `sweep-liveness`

**The line roughly triples SessionStart's wall time, sequentially.** Measured above: 1.8 s → 4.7–5.5 s; the sweep
line is 2 extra gh calls today (~2.8 s), up to 4 (1 run list + 3 job reads, the latter capped at 5 s) when the newest
completed runs did not sweep. All gh calls in `collect` run one after another. Not wrong, but it is paid at every
session start, `/clear`, `/compact` and resume. **Fix (optional):** run the PR list, the sweep-red issues and the
sweep line concurrently (threads over `_run`), which would also shrink C3-2's worst case to the longest call.

## C3-4 — MINOR — `fix_induced: false` — component `sweep-liveness`

**A re-run of an old scheduled run resets the age.** `full_sweep_status` ages a sweep from the run's `updatedAt`
(`scripts/session-state.py:927`). Re-running a 5-day-old scheduled run (attempt 2) moves `updatedAt` to now while the
commit it sweeps is still 5 days old (seen in the data: run 43254333180 is attempt 2, `updatedAt` 3 h 45 m after
`createdAt`). If the newer nights did not sweep, the line says "last completed 1 h ago" for a sweep of old master.
**Fix:** age from `createdAt` (when the schedule fired against master's then-HEAD), or print the run's `headSha`.

## Items checked that held

- **Pagination:** `gh api --paginate --jq` emits one object per page; the `raw_decode` loop reads them all and a
  page short of `total_count` is refused (mutation "total_count unchecked" is killed). A truncated page raises
  `JSONDecodeError` (a `ValueError`) → CANNOT VERIFY.
- **Rate limit / gh failure:** non-zero exit on any page → `(None, why)` → CANNOT VERIFY, and the walk stops there.
- **Shard names drifting:** a renamed matrix reads as "no mutation-sweep shard ran" → `never`, loud. No `38` is
  hard-coded in the rule (only in the cases' default fixture).
- **Failed shards:** real run 42489447406 → `red`, "1 of 24 shards failed"; real cancelled attempt 43254333180
  (0 latest jobs) → `unswept`. Both safe.
- **CANNOT VERIFY never swallowed:** mutations replacing either `return "cannot"` in `full_sweep_status` with
  `continue` are each killed; so are "deadline skipped", "each call gets the full budget", "stop after an unswept
  run", "queued runs as candidates", "red treated as unswept" and "checked cap + 1" (10 of 11 killed on a temp copy).
  The one survivor, dropping `j.get("status") == "completed"` from `shards_verdict`, is equivalent in practice
  (GitHub gives no conclusion before completion) — not a finding.
- **Seed parser on REAL logs:** shard 3 of scheduled run 43604088894 (`… under PYTHONHASHSEED 0, 654415945`) → 2
  seeds; shard 3 of scheduled run 42489447406 (24 shards) → 2 seeds; shard 3 of master-push run 43721952922 (no
  seed tail) → 1. No regression. Malformed tails: a trailing space, two declarations, a damaged list, an empty list
  and a mid-line list are refused on both events. Still accepted, not worth a finding: a duplicated seed (`0, 0`),
  which `check-plan-code.parse_seeds` refuses at the source so the writer can never emit it; and a declaration with
  different spacing/case (`under  PYTHONHASHSEED`, `\t`, lower case), which on a push reads as 1 — the writer
  (`check-plan-code.py:2975`) emits exactly one form. Both seed mutations I applied ("two declarations allowed",
  "declaration ignored on a push") are killed.
- Rest of the branch diff (`check-merge-ready.py` accounted mentions, `check-plan-code.sample_manifests`, ci.yml
  `if:`/`max-parallel`/concurrency key): nothing new beyond rounds 1–2.

## Thrashing

C3-1 is in code the r2 fold wrote, in `sweep-liveness` — the same component as r2's X1, which was itself caused by
the r1 fold. That is two consecutive rounds of fix-induced findings in one component: the arming condition for
Phase 6 is met for `sweep-liveness`. `cost-table-builder` has no fix-induced finding this round.

VERDICT: NOT CONVERGED
