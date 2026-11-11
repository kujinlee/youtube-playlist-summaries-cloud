<!-- codex-review: model=gpt-6.1-sol -->

1. **MAJOR — Unknown start% returns OK and disappears from the prompt hook** (`scripts/check-usage-pace.py:533–535,642`).
   Input: fresh cache, weekly 21%, now `2026-11-17 08:00 PST`, reset `2026-11-20 02:00 PST`, no meter rows for this window, no five-hour warning. `evaluate()` returns `OK` (rc 0); `prompt_output()` returns `None`. The owner receives no UNKNOWN notice. This violates “an unknown start% must never read as fine.” The self-test at line 1351 explicitly expects this incorrect OK result.

2. **MINOR — Last-day rule excludes midnight itself** (`scripts/check-usage-pace.py:487`).
   Input: now `2026-11-19 00:00:00 PST`, reset `2026-11-20 02:00 PST`, start 10%, weekly 31%. The band remains 22–30 and reports **NO NEW STARTS**. At midnight + 0.001 seconds it becomes **USE IT ALL**, with 66% under the stop. Use an inclusive boundary for the band without changing the hard stop.

Validation:

- Hard-stop functions are unchanged; 7,308 comparisons across three time zones found no former WARN→OK or REFUSE weakening.
- Zone boundaries, binding floor caps, and local-date override hit/miss checks passed.
- Self-test: **403/403 passed**.
- All **188 mutation anchors bind**. All **19 changed mutation entries**, applied in memory, failed their expected assertions.
- Official mutation coverage remains **NOT MEASURED**: the requested bare filename was rejected; the corrected path was blocked by missing `node_modules/typescript`.
- Comments and docstrings describe the new band rule.
- Worktree remains clean.

## Loosening answers
LOOSENING-CHECK 4c9a3bf15757: not a loosening
VERDICT: NOT CONVERGED
