<!-- codex-review: model=gpt-6.1-sol -->

## Findings

- **MAJOR — `scripts/check-usage-pace.py:664`: Missing/null 5h data silently reads as fine.** At `now=1800000000`, input `{"at":1800000000,"rate_limits":{"seven_day":{"used_percentage":10,"resets_at":1800259200},"five_hour":null}}` returns `('OK', '')`; omitting `five_hour` does too. Suggested fix: explicitly report the unavailable 5h check as CANNOT RUN/NOT RUN while preserving any weekly REFUSE. Add missing/null regression cases.

- **MAJOR — `scripts/check-usage-pace.py:606` and `:1112`: An unchanged zone repeats when usage changes.** In one session, keep weekly usage and all other inputs fixed, with `now=1800000000` and 5h reset `1800009000`; change 5h usage from `75` to `76`. Both are AT MOST 2 AGENTS, but the embedded usage changes the message hash, so both warnings print. Suggested fix: track the 5h zone separately from message text; test usage changes within one zone and transitions between zones.

- **MINOR — `scripts/check-usage-pace.py:604`: Wake time truncates seconds and permits an early restart.** With `TZ=UTC`, `now=1800000000`, weekly usage `10`, weekly reset `1800259200`, 5h usage `100`, and 5h reset `1800007230` (`10:00:30 UTC`), output says `WAKE at ... 10:01 UTC`. Reset + 1 minute is `10:01:30`, thirty seconds later. Suggested fix: use `local_time(resets + BLOCK_WAKE_AFTER_S, exact=True)` and test non-minute-aligned resets.

`python3 scripts/check-usage-pace.py --self-test`: **428/428 passed** despite these gaps.

VERDICT: NOT CONVERGED
