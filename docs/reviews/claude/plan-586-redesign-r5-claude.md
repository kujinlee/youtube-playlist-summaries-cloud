Reviewed head: 442fcc1b1feddde26904a2b61189b25b0aa3bc05

# plan-586 redesign, round 5, Claude half

**Subject:** the round-4 fold only, `git diff 5ecf2954 442fcc1b`: the plan
`docs/superpowers/plans/2026-11-09-observed-reach-selection.md` (Tasks 7.2, 7.3, 8.1, 8.2), the spec
`docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md` (§2, §8.6), and
`docs/reviews/coordinator/plan-586-redesign-r4-coordinator.md` `## Fold`.

**Method:** I extracted the plan's Task 7.2 block (plan lines 1000-1052: `runs_from_listing`, `report_identity_ok`,
`decide_pr`, `RERUN_DAYS`, `settled`) and Task 7.3 block (lines 1189-1299: `miss_evidence`, `event_evidence`,
`held_by_archive`, `may_loosen`, `absorb_epoch`, `absorb_errors`, `new_start_errors`) into
`$TMPDIR/r5rev/t72.py` and `t73.py`. Both parse and import. Every claim below that says "ran" comes from
`$TMPDIR/r5rev/repro.py`, run with `python3 -I`. Its output is quoted verbatim.

Past the round cap (review-method §0 Q4c): only F1 is put forward as a BLOCKER. F2-F5 are for FILING.

---

## F1 — BLOCKER: `settled` freezes a run by its age, so a re-run attempt made near GitHub's 30-day limit is never compared, and its miss is dropped

**Where:** Task 7.2 `settled`, `frozen(p)`:

```python
age = today - datetime.fromisoformat(p["run_created_at"].replace("Z", "+00:00")).date()
return age.days > RERUN_DAYS or runs_now.get(p["run_id"]) == p["attempts"]
```

**The defect.** The age shortcut is only safe when some report has *observed* the run's attempt count after the
re-run deadline passed, with no attempt still running. Nothing records such an observation. The rule assumes
that the daily report which runs while `age.days <= 30` sees every attempt that will ever exist, and that each one
is complete by then. Neither is guaranteed:

- GitHub's limit counts elapsed time from the run's creation. `age.days` counts calendar dates. A re-run made
  after that day's report has run, on the last allowed date, is first seen by a report on which `age.days == 31`.
  That report freezes the run without calling `runs/<id>`.
- A re-run started before the deadline whose attempt is still running at the last `age.days <= 30` report makes
  the PR `pending` there (nothing is absorbed). The next report freezes the run by age, so the completed attempt is
  never compared.
- A daily report that fails or is skipped around day 30 loses the window outright. A failed listing RAISES, and
  GitHub sometimes delays or drops scheduled runs.

The fold's own claim fails on this input: "a later re-run attempt was never compared … fixed". So does spec §8.6's
new failure line: "a report omits a PR whose decided row does not cover a later attempt of its run".

**Concrete failing input (ran):** #620's row is `clean`, push run 55 with `run_created_at 2027-01-01T10:00:00Z`
and `attempts: 1`. GitHub allows a re-run until 2027-01-31T10:00Z. Someone re-runs it at 2027-01-31T09:00Z, and
attempt 2's view is a stable miss.

```
A1 report 01-31 06:00 (before the re-run), runs_now 55->1: True
A2 report 02-01, attempt 2 exists, runs_now 55->2: True
B1 01-31 runs_now 55->2 (attempt 2 running): False decide_pr -> pending
B2 02-01 attempt 2 completed, its view a stable miss: True (would decide miss)
```

In A2 and B2, `settled` returns True, so `report()` omits #620. The miss that `decide_pr` would latch
(`decide_pr([["clean","miss"]]) == "miss"`) is never compared, and the `clean` row keeps counting toward clause 5's
20. That is §8 of the architecture review exactly: a miss that should latch is silently dropped, and the switch
can open on it.

**Is the 30 days a fact?** It is GitHub's documented limit ("up to 30 days after its initial run"), and the plan
already relies on it for the 120-day window. The number is not the problem. The problem is reading "the deadline
has passed" as "the attempt count is final and was compared". If GitHub's real limit were longer, the same rule
would also fail toward omitting, which is the loosening direction.

**Fix direction (do not take this as the design):** freeze by age only on an *observation*. One way: a row's push
is frozen when a report read `runs_now[run_id] == attempts`, with that attempt complete, at a time later than
`run_created_at + 30 days`, and the absorb records that observation (for example `attempts_final_at`). Until then
`settled` calls `runs/<id>`. Another way: replace the shortcut with `age.days > RERUN_DAYS + K`, where K is at
least the longest run plus the longest gap between successful reports that the freshness clause allows. Pin the
fix with A2 and B2 above, plus one adjacent case: a run 32 days old, observed complete at its attempt count on day
31, gets no call.

---

## F2 — MAJOR (file): `settled` holds an empty push list as settled, which is the same vacuous-`all` class the fold fixed in `held_by_archive`

`all(frozen(p) for p in row["pushes"])` is True when `pushes == []`. `decide_pr([])` returns `not a sample`,
because `all(not p for p in [])` is True. So a PR whose push listing came back empty, without failing, is decided
`not a sample` with no pushes and frozen for good. Ran:

```
C empty pushes not a sample -> True
C empty pushes inconclusive -> True
C empty pushes clean -> True
```

The fold's prose says "every push of that row records its run". An empty row records no run, and the code still
holds it. This is not shown to drop a miss: it needs a PR-run listing that returns empty when it should not, and
I did not construct one. It is the exact class the fold searched for ("an empty evidence set was vacuously held"),
and the search missed it here. Fix: `bool(row["pushes"]) and all(...)`. Case: a decided row with `pushes: []` → not
settled.

## F3 — MINOR (file): `miss_evidence` counts every `differing` item of a miss push as missed, including items that did not replay

The schema says a push's `differing` lists *each differing* item, and `result: miss` means *a* difference at that
push replayed as a miss. Suppose an archived #600 push h1/b1 has `result miss` with `differing [x.py/m1 (replayed
stable), y.py/m2 (unreproduced)]`. A later attempt view at the same push in which y.py/m2 replays as a stable miss
is HELD. Ran:

```
D y/m2 miss held (y was unreproduced in the archived push): True
```

The owner saw y.py/m2 listed in a miss row, but not as a miss. This is arguably within "what the owner saw", so it
is a MINOR. Fix, if wanted: record per item which ones replayed as a miss, and use only those as evidence.

**Canonicalisation (attack 1, no finding):** `json.dumps(d, sort_keys=True)` cannot make two different items
compare equal. Extra keys, `null` against an absent key, `1` against `1.0`, `true` against `1`, and a string PR key
against an integer one all compare UNEQUAL. Each of these fails toward latching. Ran:
`E seed key absent vs null -> held: False`. `differing` is compared as a set of items, and order and duplicates
carry no meaning for "has the archive seen this item". The PR, HEAD and BASE are all in the tuple, so no item can
match across PRs or across pushes.

## F4 — MINOR (file): `settled` crashes on a push whose run fields are null, instead of returning "not settled"

The guard `{"run_id","run_created_at","attempts"} <= set(p)` checks the keys, not their values. A push recorded
with `run_created_at: null` (for example a push with no run) raises:

```
F null run_created_at raises: AttributeError 'NoneType' object has no attribute 'replace'
```

The report then fails every day, which fails closed through freshness, so this is liveness only. The prose says
such a row "is not settled", and the code disagrees. Fix: treat a null field as not frozen.

## F5 — MINOR (file): a pre-epoch PR can still feed a LOOSENING input, `q1_probe_delta`

The fold's Task 7.2 prose says a PR merged before the active `epoch.start` "can only latch, because gate clause 5
counts no row merged before the active start". Clause 5 is not the only loosening read. Step (4) computes
`q1_probe_delta` over the restored read sets of the PRs the report processes. Since the fold, that set includes
PRs pending at a reset, which are listed from GENESIS. `absorb_epoch` takes the newest current-epoch report's
value, and clause 6 opens on it. The delta probably measures the selector's code rather than per-epoch evidence,
so this may be harmless. Even so, the sentence "can only latch" is wrong as written: either name `q1_probe_delta`
as the exception or restrict its input set. Clause 5 itself is prose with no code block, so I could not run it.
Its stated rule (rows with `merged_at` at or after `epoch.start`, through `as_utc`) closes the counting path I was
asked about.

---

## Not found (attacks that held)

- **B1 itself:** Codex's reproduction, the same PR at another push, another mutant or seed, and empty evidence all
  latch under the new `held_by_archive`, judging by the code. I ran the conflation and canonicalisation cases
  above. The identity tuple leaves out no field that tells two different misses apart, except the
  replayed/unreproduced distinction in F3.
- **`settled` reading archived epochs:** a PR decided `clean` in an archive whose run gains an attempt within 30
  days is re-decided, and a resulting miss is not held, because the archive has no miss evidence for it. Correct.
- **A new push after the decision:** a merged PR gains no pushes, so the push set is fixed. Correct.

VERDICT: NOT CONVERGED
