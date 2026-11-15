# Round 2 — `sweep-sample-nightly` (backlog #651, PR #593) — coordinator — ⟳ NOT CONVERGED; all folded

```yaml
round: 2
fixes_nontrivial: true
subject: sweep-sample-nightly
halves:
  codex: ran
  claude: skipped
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: true, component: sweep-liveness, disposition: fixed}
  - {id: X2, severity: Major, aim: deliverable, fix_induced: true, component: cost-table-builder, disposition: fixed}
```

REVIEW GAP: claude — alternation

Codex reviewed `ad7eee2e` and was filed at `c7600b18`. 2 findings, 2 fixed, 0 filed. Both are `fix_induced: true`:
each sits in code the r1 fold wrote, so the r1 bet ("r2 finds nothing caused by this fold in `sweep-liveness` or
`cost-table-builder`") LOST on both components.

| Finding | Severity | Disposition | What changed |
|---|---|---|---|
| X1 (Codex 1) a run's own conclusion is no evidence that it swept | MAJOR | fixed | `scripts/session-state.py` judges a scheduled run by its `mutation-sweep (k)` SHARD jobs |
| X2 (Codex 2) a malformed seed list reads as "no seeds" | MAJOR | fixed | `scripts/sweep-costs.py` refuses a DECLARED but malformed seed list on every event |

- **X1 — component `sweep-liveness` (`scripts/session-state.py`, the FULL SWEEP line).** The r1 rule counted a run
  whose conclusion was `success` or `failure`; a `success` whose shards were all skipped, or a run with some shards
  cancelled, read as a fresh sweep. Now `fetch_sweep_jobs` reads `gh api --paginate …/actions/runs/<id>/jobs`
  (a page short of `total_count`, a job missing a field, a `gh` failure or a run id that is no id is `(None, why)`,
  never a partial list), and the pure `shards_verdict(jobs)` says: no shard job → unswept; any shard not
  completed with `success`/`failure` → unswept, counted by conclusion; a failed shard → a sweep the line calls RED
  (it RAN: fresh, and red); else green. The summary job `mutation-sweep-complete` is not a shard.
  `fetch_sweep_evidence` walks the newest completed runs (at most `SWEEP_JOBS_CHECKED` = 3), stops at the first
  that swept or could not be read, and shares one `SWEEP_JOBS_BUDGET` = 5 s deadline across its calls;
  `SWEEP_RUN_TIMEOUT` went 10 → 5 s so the hook's four `gh` calls sum to 30 + 15 + 5 + 5 = 55 s, inside its 60.
  Jobs not read or unreadable are `CANNOT VERIFY`, never fresh and never "no sweep". The fixed job lists the lead
  asked for are each a case: all shards green, all skipped, 9 of 38 cancelled, 2 of 38 failed (FRESH, the line says
  RED), no jobs. Live, this worktree: `FULL SWEEP: last completed 23 h ago (run 43604088894, all 38 shards green);
  the newest scheduled run is queued.` (run 43604088894 has 40 jobs: `verify`, 38 shards, the summary job).
  ⚠ Bound: three runs and 5 s; a fourth unswept run in a row reads as no sweep among those checked, said as such.
- **X2 — component `cost-table-builder` (`scripts/sweep-costs.py`, the seed parse).** The r1 `seed_count` matched
  only a well-formed tail, so a declared-but-malformed list (`0, bad`; a mid-line list with a suffix; an empty
  list; two declarations) fell to "no seeds" and a two-seed push was divided by 1. Now an occurrence of
  ` under PYTHONHASHSEED ` that is not exactly one well-formed list at the line's end is `Refused` on a push and a
  schedule alike. The per-mutation `(killed under PYTHONHASHSEED=3)` form is not a declaration (its `=` is the
  difference), pinned by a case and a mutation. The r1 case that ACCEPTED a mid-line list is inverted.

## Codex's LOOSENING-CHECK lines

`0085414c8cfa`, `960f273307d8` and `07931f9e4c36` answer "finding: scheduled logs with a parseable seed-list tail
now pass where master refused every scheduled log". That is the INTENDED r1 CM2 change, not a defect: the
nightly scheduled run is the cost table's only input once a master push no longer sweeps (r1 coordinator, CM2),
so refusing every scheduled log would leave the table with nothing. The loosening is bounded by X2's fold: a
scheduled log passes only with one well-formed seed list, and its times are divided by that count.

## Counts

| Script | Cases | Mutations | Swept locally |
|---|---|---|---|
| `scripts/sweep-costs.py` | 35 → 36 | 33 → 36 | yes: `--mutate . --only scripts/sweep-costs.py` 36 killed, 36 attributed, 0 survivors |
| `scripts/session-state.py` | 148 → 161 | 127 → 145 | NO (the slice is over the local budget) |

⚠ The session-state manifest's 3 re-bound and 18 new mutations (21) were each applied BY HAND to a temp copy of
`scripts/` (control green first) and each was killed by exactly the case it names: 21 of 21. Two drafts that
repeated an earlier entry's anchor were made distinct before that run. That is a diagnostic, not the gate; the full
manifest is CI's to sweep. The 3 re-bound: a cancelled run as a sweep (now `if not shards:`), collect() not reading
the runs, the age from the wall clock (both now through `full_sweep_line(root, run, clock(), tick)`).

## `fix_induced`

Round 2: X1 and X2 are both `fix_induced: true` — each is in code the r1 fold (`487a3cc1`) wrote. One fix-induced
round does not arm Phase 6; two consecutive rounds of findings caused by the previous fold, in one component, do.

## Round 3

One half (alternation): Claude. The bet, stated before it: round 3 finds nothing caused by this fold in
`sweep-liveness` or `cost-table-builder`. If it does, in one of them, that is THRASHING and Phase 6 arms. Most
exposed: `shards_verdict` on a run whose shard names change (a matrix renamed away from `mutation-sweep (k)` reads
as no sweep, loudly), and the shared deadline on a slow first call.
