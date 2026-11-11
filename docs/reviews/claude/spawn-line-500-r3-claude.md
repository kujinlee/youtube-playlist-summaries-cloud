Reviewed head: b8a1b2cda95baae89df29c3dc7ad4ce5146caccd

# spawn-line-500 r3 — Claude half (adversarial)

Subject: `git diff a797aef8..b8a1b2cd` (backlog #500, PR #500): the stop is now
`refuse_at(now, resets) = min(97, 100 − 5 × days_after_today(now, resets))`, and the pace line is only a guide.

Ground truth this round:
- `python3 scripts/check-usage-pace.py --self-test` at b8a1b2cd: **299/299 passed, rc 0**.
- Live (Wed 11-04 09:40 PST, reset Fri 11-06 02:00 PST): `WARN ... at 94.5% new spawns ... refused ... The stop
  keeps 5% for each of the 1.1 days after today. Today's pace line is 95.2% — a guide, not a stop.`
- Case count 299 and mutation count 122 (manifest length 122, `EXPECTED_MUTATIONS` 122) agree with the docs.
- The owner's 09:29 message (transcript) begins *"For example, emergency reserve is set to 5% ..."*; the
  coordinator's reply disclosed fractional days and today's 94.6, so the fractional reading is not a finding.

## Claim-by-claim

1. **Formula for every reset/now** — holds for month end (01-31 → 02-02: 1.0000 days, 95), year end
   (12-31 → 01-02: 95), 02-28 non-leap (95), 23:59:59 (95), a reset before the coming midnight (0 days, 97), and
   a reset at/before now (decided earlier: `_evaluate` returns CANNOT RUN at `resets <= now`, so the 97 that
   `refuse_at` would give is never used). **Refuted on DST spans** — C3.
2. **Meter content cannot change the verdict** — holds for the verdict value (no meter content raised: lists,
   strings, nested 4 MiB `[`, 4 MiB int list, booleans, out-of-range, all caught). **Refuted for latency** — C1:
   meter content alone stretches every hook call to ~19 s, and a hook that is killed is an allow.
3. **Every #500 case can fail** — each case is reddened by a named mutation in the manifest, or by an obvious
   edit (e.g. dropping `max(0.0, …)` reddens the `days_after_today` case: mutant run, 298/299). None found
   unfalsifiable. But two promised behaviours have NO case — C2.
4. **A mutation per promise** — missing for the DST/month-end normalisation (C2) and the `max(0.0, …)` floor (C7).
5. **Docs agree with code** — numbers 299 and 122 correct; 94.6% and 70% are not what the code computes or
   shows (C4); the quote drops "For example" (C8).
6. **No stale statement of the replaced rule** — `REFUSE_AT`, "90 floor", `max(90` have zero hits outside
   reviews and history; but `docs/process-checklists.md:190` still states the fixed 90% as current (C6).

## Findings

### C1 — Medium — `scripts/check-usage-pace.py:280-292` (`pace_line` loop), `:431-432` (bound claim)
**Input:** cache at weekly 98%, reset in 2 days; meter log = 4 MiB of blank lines (`"\n" * 4194304`, exactly
`METER_MAX_BYTES`, so the read accepts it).
**Observed:** `python3 scripts/check-usage-pace.py --cache c.json --meter m.jsonl` → REFUSE-SPAWN, correct
verdict, but **real 19.30 s** (vs 0.06 s with no meter). `pace_line` alone: blank lines 20.1 s, `x` lines 9.8 s,
`{}` lines 4.2 s, `1` lines 7.1 s, valid rows 0.2 s. Every prompt, spawn and SendMessage pays it.
**Expected:** the docstring at :431-432 says *"the hook's worst case is three deadlines"*, and :185 says reads are
*"well under the 30 s hook timeout"*. The parse is not under any deadline, so the stated worst case is false. On
a slower or loaded machine the 30 s (as the module states; the hooks set no `timeout`, so the harness default
applies — not verified here) is reachable, and a killed hook is a non-blocking error, i.e. the spawn is ALLOWED
at REFUSE. Since #500's stop is now computed before and independent of the line, the cheap fix is to bound the
meter's cost: parse only the tail (backlog #501's fix) or a bounded line count, and/or put the parse under the
same deadline and drop the line (message only) when it overruns. A case: 4 MiB of blank lines evaluates within
the bound.

### C2 — Medium — `scripts/check-usage-pace.py:301-306` (`days_after_today`); no case, no mutation
The docstring promises *"mktime with the day + 1, which normalises month ends and DST days"*. Nothing tests it.
Two mutants, each run on a `git archive HEAD` copy:
- (a) `nxt = local_midnight(now) + 86400` → **299/299 passed (survives)**. Under the suite's own TZ
  (`PST8PDT`), on the fall-back day Sun 11-01 10:00 it puts the next midnight at Sun 23:00, one hour early.
- (c) isdst `-1` → `0` → **299/299 passed (survives)**. For the whole PDT half of the year it reads the next
  midnight as 00:00 PST = 01:00 PDT: e.g. now Wed 07-01 12:00 PDT, reset Fri 07-03 00:00 PDT → 23/24 days → stop
  95.21 instead of 95.
**Expected:** a case at a PDT `now` (catches c) and one on a DST-change day (catches a), plus a month-end case
(e.g. 01-31 12:00 → 02-02 00:00 = 1.0 day), each with a manifest mutation.

### C3 — Low — `scripts/check-usage-pace.py:306` (`(resets - nxt) / 86400`)
**Input (TZ America/Los_Angeles):** now Sat 10-31 12:00 PDT, reset Mon 11-02 00:00 PST (one calendar day after
today, Sunday, which is 25 h long).
**Observed:** days 1.0417, stop 94.79 (shown 94.7%). Spring: Sat 03-07 12:00 → Mon 03-09 00:00 gives 0.9583,
stop 95.21.
**Expected:** the owner's "days (excluding today)" are calendar days → 1.0, stop 95. Off by 0.21 points on the
two weeks a year whose span contains a DST change. Fix: count whole local days by calendar date plus the
fraction of the reset's own day, or accept and STATE the bound in the docstring (it currently claims DST days
are normalised, which is true for the midnight only, not for the day length).

### C4 — Low — `docs/backlog.md:481`, `docs/dashboard-entries.md:18754`
**Input:** today's live cache (reset Fri 11-06 02:00), and now = Fri 11-06 02:01 with the next reset 11-13 02:00.
**Observed:** stop 94.583 → the hook prints **"at 94.5%"**; just after the reset the stop is **69.583**, printed
"69.5%" (6.083 days after today, because the reset is at 02:00, not midnight).
**Expected:** the docs say "94.6%" and "just after a reset it is 70%". The first is rounded UP, which `pct()` is
built never to do, so the owner reads 94.6 in the docs and 94.5 in the hook; the second is wrong by 0.4.
Write "about 94.6% (shown 94.5%)" / "about 69.6%", or "≈70%".

### C5 — Low — `scripts/check-usage-pace.py:379-382` (WARN message), `pct` at :215
**Input:** now Wed 11-04 09:40 PST, reset Fri 11-06 02:00, weekly 94.55 (stop 94.583).
**Observed:** `WARN: weekly usage is 94.5% (WARN at 80%; at 94.5% new spawns and agent wake-ups are refused)`.
The message says usage has reached the refusal level while the verdict does not refuse.
**Expected:** `pct`'s own invariant — *"the text cannot name a threshold the verdict did not reach"* — holds for
the usage figure only; flooring the STOP breaks it the other way. Show the stop rounded UP to 0.1 (94.6%), so a
WARN never displays usage ≥ stop. Now the common case: any reset not at local midnight gives a fractional stop.

### C6 — Medium — `docs/process-checklists.md:190`
**Observed:** *"at **90%** a NEW subagent spawn is denied, and so is a `SendMessage` the main session sends..."*
— present-tense description of the mechanism, untouched by this branch (`git diff master...HEAD` has no change
to the file). It is the doc agents read for the process rule.
**Expected:** "at the stop (100% − 5% × the days after today, never above 97%; backlog #500)". Lesser, same
class: backlog #404's FAILS IF still reads *"with the cache at 90% or more"* (`docs/backlog.md:386`), a live
falsifier whose threshold no longer exists; row 399 is a closed history row and can stay.

### C7 — Low — `scripts/mutations/check-usage-pace.json` (no entry for `max(0.0, …)`)
Removing the floor (`return (resets - nxt) / 86400`) is killed by `#500: days_after_today is never negative...`
(mutant run: 298/299), but the manifest has no such mutation, so a later edit that weakens that case is not
held. The promise is behaviourally masked in `refuse_at` by the 97 cap, which is exactly why it needs its own
pinned mutation.

### C8 — Low — `docs/backlog.md:481`, `docs/goal-threads.md` (the 09:29 quote line)
**Observed:** both quote the 09:29 message without its opening "For example," and the row calls it *"the rule
itself"*, then says today's stop is 94.6% — a reader sees the owner state 85 "for today" and the code give 94.6.
**Expected:** keep "For example," in the quote (the transcript has it), so the 3-day/85 figures read as the
owner's illustration, not today's numbers.

## Not findings (checked)
- Reset at/before now: CANNOT RUN before `refuse_at` is reached (`_evaluate`, `resets <= now`).
- `window()` bounds `resets` to now + 7 d + 1 h, so the stop is ≥ ~65; a stop below WARN refuses without a
  WARN first — tested ("reserve bites below WARN").
- No meter content raised out of `pace_line` (only `Malformed` is caught by `evaluate`, so a raise would have
  been a crash → allow): lists, scalars, nested depth, huge ints (`parse_int=float`), NaN/Infinity, booleans.
- The new goal-threads `>` quote line uses the established grammar (`goal-tree.py:223`).

VERDICT: NOT CONVERGED
