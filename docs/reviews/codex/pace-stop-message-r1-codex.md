<!-- codex-review: model=gpt-6.1-sol -->

Reviewed HEAD `599362671e9db61eddca2d6d5408d73ffdd0a362`, backlog #525, its source review, and `git diff origin/master...HEAD`. No `.claude/plans/` access, repository changes, or GitHub actions.

Found two MINOR issues; no BLOCKER or MAJOR.

1. **MINOR — the forecast fails when `RISE_END_S >= LAST_NIGHT_S`.**  
   Location: `scripts/check-usage-pace.py:429`.

   These reproductions change the module constant in memory; the shipped constants do not trigger them. All times are America/Los_Angeles, with reset **2027-01-16 02:00 PST** and weekly usage **98%**.

   - Set `RISE_END_S = LAST_NIGHT_S = 28800`; evaluate at **Jan 15 17:00**. The message promises **“99% from Fri 01-15 18:00 PST”**, but `refuse_at(18:00, reset)` returns **100**. Equality must select the hard limit because `last_night` uses `>=`.
   - Set `RISE_END_S = 32400`; evaluate at **Jan 15 17:30**. The message says **“99% now and 99% from Fri 01-15 17:00 PST”**. That endpoint has passed; the next actual transition is **100% at 18:00**.

   Select the next transition using both endpoint ordering and `now`. Add equality and post-plateau cases. The docstring’s unconditional assertion that 99% is never reached also depends on the shipped constants.

2. **MINOR — the newly forecast start can precede the actual boundary by 59 seconds.**  
   Location: `scripts/check-usage-pace.py:438`, through `local_time()`.

   With shipped constants, reset **2027-01-16 02:37:42 PST**, evaluate at **Jan 15 17:37:42**, weekly **98%**. The message promises **“100% (the hard limit) from Fri 01-15 18:37 PST”**.

   At **18:37:00**, weekly **99%** still produces `REFUSE-SPAWN`; the actual stop is **98.45281914547701%**. It remains refused at **18:37:41**, then becomes `WARN` at **18:37:42**, when the stop reaches 100%.

   Minute-only formatting is pre-existing, but the new forecast inherits this discrepancy. Show seconds when the transition is not minute-aligned.

Verification:

| Check | Result |
|---|---|
| Baseline `python3 scripts/check-usage-pace.py --self-test` | **338/338 self-test cases passed** |
| New M1 mutation | Anchor occurs exactly once; named M1 case fails; **336/338** |
| New M3 mutation | Anchor occurs exactly once; named M3 case fails; **337/338** |

Both mutations ran complete suites in temporary copies. Neither new case is vacuous.

With shipped constants, probes after the last-night boundary, above the current stop, across spring/fall DST changes, and with an unknown reset produced consistent messages and verdicts, apart from the timestamp precision issue above.

VERDICT: NOT CONVERGED
