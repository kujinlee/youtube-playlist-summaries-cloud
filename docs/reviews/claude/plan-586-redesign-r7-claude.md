Reviewed head: 02f7e18d4c842a628aa2097d474de990124f73a5

# plan-586-redesign, round 7, the Claude half (adversarial, BLOCKER-only past the cap)

Subject: `git diff bdcd6c56 02f7e18d`, the r6 fold (plan Task 7.2 / 7.3, spec §2 / §8.6, backlog #595, the `## Fold`
section of `docs/reviews/coordinator/plan-586-redesign-r6-coordinator.md`). Mandate: refute that the fold is safe.

## Method

The Task 7.2 block (plan lines 1070-1179) and the Task 7.3 block (lines 1360-1477) were extracted verbatim into
`$TMPDIR/r7-586/t72.py` and `t73.py`, and a construction script `poc.py` imports them and runs under `python3 -I`:

```
D=$TMPDIR/r7-586; mkdir -p $D
sed -n '1070,1179p' docs/superpowers/plans/2026-11-09-observed-reach-selection.md > $D/t72.py
sed -n '1360,1477p' docs/superpowers/plans/2026-11-09-observed-reach-selection.md > $D/t73.py
python3 -I $D/poc.py $D
```

Output (verbatim):

```
== A: runner 2 days FAST (> SKEW_DAYS), run 55 past the capped listing's reach ==
settled before any record: False -> #620 re-decided; its own runs join runs_now
report final_runs: {'55': {'attempts': 1, 'observed_at': '2027-02-01T10:00:01Z'}}
ledger final_runs: {'55': {'attempts': 1, 'observed_at': '2027-02-01T10:00:01Z'}}
CONTROL (uncapped listing shows 55 at attempt 2): settled = False
REAL (capped listing, 55 absent): settled = True -> #620 OMITTED; attempt 2's miss never compared; decide_pr would have said miss
  later report (+2d), run 55 still absent: settled = True
  ...
  later report (+37d), run 55 still absent: settled = True
== B: at real scale the unfreeze clause is unreachable for every recorded run ==
capped listing reach ~= 9.9 days; a record needs age > 31 days
so for a run with any final_runs record, runs_now.get(run) is None unless its PR is re-decided,
and settled() returns True on `now is None` -> the unfreeze compares against nothing
== C: replacement from a report that may NOT loosen ==
final_runs: {'55': {'attempts': 1, 'observed_at': '2027-02-01T10:00:01Z'}} log: ['ABSORB MISSES ONLY: 9002.1 report from another epoch']
== D: guard rebuild reproduces a replacement; HEAD keeping the first is refused ==
rebuilt: {'55': {'attempts': 2, 'observed_at': '2027-02-05T07:00:00Z'}}
HEAD keeping first: ['final_runs differs from the rebuilt absorb']
HEAD = rebuilt: []
```

## Findings

### F1 — BLOCKER (conditional on a runner clock more than `SKEW_DAYS` fast): the unfreeze rule cannot see the run it is meant to unfreeze, so a premature final observation still silently drops a re-run's miss

The fold's safety claim (plan line ~1004): "a frozen push is UNFROZEN whenever `runs_now` lists its run at an attempt
count other than the recorded one, so a premature observation, **from any cause**, is overruled by the next listing
that contradicts it". In `settled` (Task 7.2):

```python
now = runs_now.get(p["run_id"])
if (fin is not None and as_utc(fin["observed_at"]) > as_utc(p["run_created_at"]) + FINAL_AFTER
        and (now is None or now["attempts"] == fin["attempts"])):
    return True
```

`now is None` freezes. And the same fold files backlog #595: the CI runs listing is capped at 1,000 runs, ~10 days at
the measured ~101 runs/day. A record exists only for a run older than 31 days by `observed_at`, so for every recorded
run the real listing returns nothing, `now is None`, and the push is frozen. The only way such a run re-enters
`runs_now` is its PR's own re-decision, and a `settled` PR is not re-decided. The unfreeze is circular: it requires
a re-decision that only an unfreeze would trigger.

Failing input (construction A, run): run 55 created 2027-01-01T10:00Z, #620 `clean` at attempt 1. GitHub's time is
2027-01-30T10:00Z (day 29, a re-run still legal); the report runner's clock reads 2027-02-01T10:00:01Z (2 days fast).
#620 is unsettled (no record; 55 is past the capped listing), so it is re-decided, its run joins `runs_now` at
attempt 1 completed, `observe_final` is True by the runner's clock, and `final_runs` records `{55: {attempts 1}}`;
the absorb takes it (the report `may_loosen`). The owner re-runs 55 at GitHub's day 29.5; attempt 2 replays a stable
miss. Every later report: 55 absent from the capped listing → `settled` True → #620 omitted for ever; attempt 2 is
never downloaded or compared. CONTROL: the same ledger with a listing that shows 55 at attempt 2 → `settled` False;
the rule works only on a listing the plan itself says cannot exist past day ~10.

So after the fold the ENTIRE defence against a premature observation is `SKEW_DAYS = 1`; the "later disagreement
always wins" clause adds nothing in production. A runner more than one day fast is called "a broken runner" in the
plan, but nothing detects it: it is a silent drop, not a loud failure. That the precondition is unlikely on
`ubuntu-latest` does not make it loud, and the plan's own text claims coverage "from any cause".

Cheapest fixes (either removes the precondition rather than bounding it): take `observed_at` from GitHub's clock,
the `Date` header of the first runs-listing response, so `observe_final` compares two GitHub times; or keep the
runner clock but FAIL the report (no upload, `cannot run`) when it differs from that `Date` header by more than an
hour. Then correct the "from any cause" sentence: the unfreeze only reaches runs the listing returns (≤ ~10 days old),
i.e. never a recorded one, unless #595's fix gives recorded runs a per-run fetch.

**FAILS IF:** construction A (runner clock 2 days ahead of GitHub's, run 55 absent from `runs_now`, attempt 2
re-run after the record) still returns `settled("620", …) == True`.

### F2 — MAJOR: the r6 B1 cases pin the unfreeze on a listing shape that cannot occur, so they pass while the property is absent

The plan's r6 B1 cases ("a recorded observation contradicted ... a listing shows run 55 at attempt 2 → NOT settled";
"the same in an ARCHIVED epoch"; `newest_finals` archive-vs-active) all hand `settled` a `runs_now` that contains a
run older than 31 days. With the cap (#595, same fold) the real listing never contains one (construction B: reach
~9.9 days vs. a record age > 31 days). The cases are green over code whose unfreeze branch is unreachable in
production; they test the mechanism, not the property. Add a case with the CAPPED listing (the run absent) and a
re-run after the record, which must go red today (it does, construction A). Same root as F1; filed if F1 is fixed by
the clock source alone.

### F3 — MINOR: "newest" is ordered by runner clocks, and the absorb refuses a newer-by-GitHub disagreeing record that carries an earlier runner stamp

`newest_finals` and the absorb's replacement both order by `observed_at`, a per-runner clock. A fast runner's record
`(attempts 1, T+2d)` outranks a correct runner's later `(attempts 2, T+1d)`: the absorb keeps attempts 1
(`fin.observed_at > old.observed_at` is False). With the run listed at 2 this is fail-closed (unfrozen, re-decided
while listed); it only drops a miss through F1's path. Ordering by GitHub's time (F1's fix) removes it.

### Checked, no finding

- **Replacement from a report that may not loosen** (construction C): `report from another epoch` with
  `{55: {attempts 2}}` → not recorded, `ABSORB MISSES ONLY` logged. The replacement sits under `if not why`.
- **Guard rebuild** (construction D): `absorb_errors` rebuilds the replacement; a HEAD keeping the first record is
  refused (`final_runs differs from the rebuilt absorb`); a HEAD equal to the rebuild passes.
- **An older agreeing record outranking a newer disagreeing one:** the absorb keeps the FIRST agreeing stamp, so a
  disagreeing record later than that first stamp replaces it even if an agreeing repeat was later still; attempt
  counts only increase, so this can only move the record toward the true count (fail-closed).
- **Skew ≤ 1 day:** with `FINAL_AFTER` = 31 days, a record implies GitHub's time > 30 days after creation, so no legal
  re-run follows it; Codex's 2 s reproduction is closed by the margin (not by the unfreeze).

VERDICT: NOT CONVERGED
