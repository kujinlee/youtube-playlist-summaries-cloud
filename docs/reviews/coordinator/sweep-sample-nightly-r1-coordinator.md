# Round 1 — `sweep-sample-nightly` (backlog #651, PR #593) — coordinator — ⟳ NOT CONVERGED; all folded

```yaml
round: 1
fixes_nontrivial: true
subject: sweep-sample-nightly
halves:
  codex: ran
  claude: ran
findings:
  - {id: CM1, severity: Major, aim: deliverable, fix_induced: false, component: sweep-liveness, disposition: fixed}
  - {id: CM2, severity: Major, aim: deliverable, fix_induced: false, component: cost-table-builder, disposition: fixed}
  - {id: CM3, severity: Minor, aim: prose, fix_induced: false, component: harness-sample, disposition: fixed}
  - {id: CM4, severity: Minor, aim: prose, fix_induced: false, component: harness-sample, disposition: fixed}
  - {id: CM5, severity: Minor, aim: prose, fix_induced: false, component: sweep-liveness, disposition: fixed}
  - {id: X1, severity: Minor, aim: prose, fix_induced: false, component: harness-sample, disposition: fixed}
  - {id: X2, severity: Minor, aim: prose, fix_induced: false, component: harness-sample, disposition: fixed}
  - {id: X3, severity: Minor, aim: deliverable, fix_induced: false, component: harness-sample, disposition: fixed}
```

Both halves reviewed `2c65cf70` and were filed at `e26804d8`. Folded in `487a3cc1`. 8 findings, 8 fixed, 0 filed.

| Finding | Severity | Disposition | What changed |
|---|---|---|---|
| CM1 (Claude M1) nothing notices the only full sweep not running | MAJOR | fixed | `scripts/session-state.py` prints a `FULL SWEEP:` line at session start |
| CM2 (Claude M2) the cost table loses its only input | MAJOR | fixed | `scripts/sweep-costs.py` reads a scheduled run at one seed's cost |
| CM3 (Claude M3) two comments justify safety with the old behaviour | MINOR | fixed | `check-merge-ready.py` bound and the `ci.yml` concurrency comment reworded |
| CM4 (Claude M4) what a contributor learns later is understated | MINOR | fixed | ~38 h and the by-hand bisect in backlog #651's Bound, the dev-process row, the harness comment |
| CM5 (Claude M5) backlog #231 closed by retreating from its criterion | MINOR | fixed | criterion restated for scheduled runs: 3,000 s |
| X1 (Codex 1) different keys do not guarantee different samples | MINOR | fixed | `sample_manifests` docstring says CAN, with the one-target case |
| X2 (Codex 2) "ONLY full sweep" contradicts `batch/**` | MINOR | fixed | `ci.yml` says the only REGULAR full sweep |
| X3 (Codex 3) no case enforces smallest-hash selection | MINOR | fixed | a case ranks digests written out by hand; a descending-rank mutation |

- **CM1.** `fetch_schedule_runs` asks `gh run list --workflow ci.yml --event schedule --branch master` (10 s bound;
  the block's three calls sum to 55 s inside the hook's 60). The rule is the pure
  `full_sweep_status(runs, why, now)`, tested at fixed timestamps: 23 h is fresh, the same run at 37 h is STALE,
  exactly 36 h is fresh and a minute more is not, a cancelled run with zero jobs is no sweep (the age is the last
  run that completed with `success` or `failure`, and the cancelled one is named), no completed run among those
  listed is said, and a `gh` failure is `CANNOT VERIFY`, marked. The limit, 36 h, is 24 h of cron plus the 7-10 h
  start delay `ci.yml` records as measured. Live: `FULL SWEEP: last completed 23 h ago (run 43604088894, success)`.
  ⚠ Bound, written into the row: the line is read by a session; with no session for days nobody reads it.
- **CM2.** The brief asked for the seed count "from where the workflow defines it, never a hard-coded 2". The fold
  takes it from the RUN'S OWN verdict line instead (`… under PYTHONHASHSEED 0, 654415945`, which
  `check-plan-code.verdict_line` writes from the seeds it ran). Reason: `ci.yml`'s `SEEDS=` is what a FUTURE run
  will do; a log being read may predate a change to it, and the verdict is what that run did. A `schedule` verdict
  that lists none is refused, and so are two seed counts in one run. One case holds two distinct counts (2 and
  3) and a push that lists none. MEASURED on scheduled run 43604088894, shard 7: all 260 lines attribute, 2 seeds,
  938.1 s per seed against 1,876.1 s of wall time. ⚠ Bound, in the docstring: gap / N is the mean over the seeds,
  an estimate; the tree copy per extra seed precedes the first progress line and is in no gap.
- **CM5.** MEASURED with `gh api …/runs/<id>/jobs`, the three newest successful scheduled runs (38 shards each, all
  before PR #590's partition): slowest shard 2,876 s, 2,817 s, 2,540 s. Under 3,000 s by 4-15%, so the row stays
  closed, and the first two scheduled runs after PR #590 confirm or reopen it. Neither has completed.
- **X3.** The digests of sha256("k" NUL target) for a-e were computed with `shasum`, outside the script, and are
  literals in the case; the case ranks the literals itself. Lowest two: {a, c}. Highest two: {b, d}.

## Counts

| Script | Cases | Mutations | Swept locally |
|---|---|---|---|
| `scripts/sweep-costs.py` | 32 → 35 | 29 → 33 | yes: 33 killed, 33 attributed |
| `scripts/session-state.py` | 137 → 148 | 119 → 127 | NO (127 × ~10 s is over the local budget) |
| `scripts/check-plan-code.py` | 505 → 506 | 369 → 370 | NO (370 × ~29 s) |

Manifest total 5,190 → 5,203; all 5,203 anchors resolve, `pin_drift` empty. ⚠ The 9 new or re-bound mutations in
the two unswept manifests were each applied by hand to the delivered file and killed by exactly the case they
name; that is a diagnostic, not the gate. The two full manifests are CI's to sweep.

## `fix_induced`

Round 1: no earlier fold exists, so every finding is `fix_induced: false` — CM1, CM2, CM3, CM4, CM5, X1, X2, X3.

## Round 2

One half (alternation). The bet, stated before it: round 2 finds nothing caused by this fold in `sweep-liveness`
or `cost-table-builder`. Most exposed: `full_sweep_status`'s reading of a run that is `in_progress` past the
limit, and `seed_count` on a verdict line GitHub's log prefix or a trailing annotation has altered.
