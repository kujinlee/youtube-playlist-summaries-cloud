Reviewed head: 4a7327904e019069368a2576d1bafdddbb9717c0

# suite-cost-b — round 5, Claude half (the merge gate's flagged lines)

Scope, narrow: the 8 lines `check-merge-ready.py --pr 538 --flagged-block` flags in `scripts/check-plan-code.py`
(master line numbers). Each was read in context on this tree (`git diff origin/master...HEAD`) and judged on its own.
`python3 scripts/check-plan-code.py --self-test` on this head: **418/418 passed, rc 0** (23 s wall).

## What each path does on master vs this tree

- **A suite that times out** (`run_suite_parts`, master :1156/:1160, branch :1256-1283). Master: `timeout=SUITE_TIMEOUT`,
  on `TimeoutExpired` return `(2, "", "CANNOT RUN ... NOT CHECKED.")`. Branch: `timeout=cap`, where `cap` is the
  smaller of `limit` and the budget left; on `TimeoutExpired` it STILL returns rc 2 with `CANNOT RUN ... NOT CHECKED`
  (two wordings, one for the budget cut, one for the own limit). New: when the budget is already spent the child is
  not started and the call returns the same rc 2 / NOT CHECKED. `limit` is `suite_limit(...)`, which is always finite
  (`min(SUITE_TIMEOUT_CEILING=600, max(SUITE_TIMEOUT, 20 x control))`), so a real hang still times out. The consumer is
  unchanged: `run_mutations` reads rc 2 as `measured: False`, a survivor, `ok = False`, and "did NOT COMPLETE ... NOT
  CHECKED" (:2337-2352); under seeds `seed_outcome` returns rc 2 if ANY seed is rc 2 (:323-325). No path turns rc 2
  into `caught`. Controls and re-controls keep the flat `SUITE_TIMEOUT` (`control_parts` passes no limit; the `limits`
  dict is consulted only for mutant runs, :2301).
  The one behavioural change: a mutant that takes 120-600 s (bounded by 20x its own control) now COMPLETES and gets
  its real verdict, where master reported it NOT CHECKED. That is the purpose of backlog #558, not a loosening: the
  verdict is still "red via the case it names", earned by a finished run; nothing a hung mutant produces is read as
  a kill.
- **The `run_suite` signature** (master :1164). Gains `limit=None`, which falls back to `SUITE_TIMEOUT`; every
  existing caller without the keyword gets master's behaviour.
- **The self-test stub** (master :3849/:3853, branch :4399/:4403). The stub gains `limit=None` and forwards it; it
  still returns rc 2 on the mutated run only, and both cases ("counted but NOT a verdict", "reported as a cannot-run,
  not as a catch") still assert what master asserted. Without the keyword the stub would TypeError under the new
  call shape, so this is a forced signature update, not a weakened oracle.
- **The budget running out mid-sweep** (new). Every stop point returns `ok = False`: before/among the controls
  (:2162-2167), inside `run_mutations` (:2258-2262, naming the unfinished and the unreached), after `run_mutations`
  (:2179, returns `False` with a `NotMeasured`), and in the re-controls (:2213-2218, `ok = controls_green = False`).
  `main` returns `0 if ok else 1` (:7330), so a budget stop exits 1, never 0, and the verdict is `NotMeasured`
  (no tally line). A budget that cannot be derived on CI is rc 2 before anything runs (:7232-7237). I also traced the
  edge "budget expires during the LAST mutant": that mutant's rc 2 is `measured: False` and `ok = False`; the
  re-control loop then breaks, `len(recontrol_rc) < len(targets)` fires, and the stop line names it.
- **The sweep call and the failure print** (master :6583-6589, branch :7268-7279, :7326-7327). The call gains
  `hold=` and `deadline=`; `budget`, `only`, `seeds`, `shard`, `select` are passed as before. The print loop now
  skips lines starting with `BUDGET_STOP`, and prints exactly those after the tally / not-measured line, flushed.
  The two loops partition `report`, so every line master printed is still printed, with the same `  ✗ ` prefix;
  the `LOCAL_REFUSAL` early return is unchanged except that it closes `hold` first.

No findings.

## Loosening answers
LOOSENING-CHECK 8d2f8bd4cc54: not a loosening
LOOSENING-CHECK 3f833ef4b8d9: not a loosening
LOOSENING-CHECK 38f234e35820: not a loosening
LOOSENING-CHECK 7dd25f6d44c9: not a loosening
LOOSENING-CHECK af4690f3e18e: not a loosening
LOOSENING-CHECK d1158d019edf: not a loosening
LOOSENING-CHECK 2ff4eab35bd1: not a loosening
LOOSENING-CHECK a08be7d2cf13: not a loosening

VERDICT: CONVERGED
