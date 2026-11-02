<!-- codex-review: model=gpt-6.1-sol -->

1. **Major — malformed reset crashes instead of reporting CANNOT RUN.** `scripts/check-usage-pace.py:100` accepts `resets_at: 1e300`; formatting it at line 79 raises `OverflowError`. Concrete cache: `{"at":1800000000,"rate_limits":{"seven_day":{"used_percentage":95,"resets_at":1e300}}}`, evaluated with `--now 1800000000`. The spawn wrapper exits 1 with no verdict, allowing the spawn; the prompt loses the required loud CANNOT RUN context. Catch unrepresentable timestamps.

2. **Major — malformed cache can stall every prompt.** `scripts/check-usage-pace.py:161` performs an unbounded blocking open/read. Passing a temporary FIFO through `--cache`, with no writer, stalled the full prompt hook beyond my one-second test deadline. The registration at `.claude/settings.json:65` sets no timeout; Claude Code documents a **30-second default** for UserPromptSubmit. Reject nonregular files and bound the read. [Hook timeout documentation](https://code.claude.com/docs/en/hooks#userpromptsubmit)

3. **Minor — future cache reads OK.** `scripts/check-usage-pace.py:127`: with `--now 1800000000`, cache `{"at":1800000060,"rate_limits":{"seven_day":{"used_percentage":10,"resets_at":1800086400}}}` returns **OK**. The explicit 60-second allowance contradicts the stated future-cache rule and the comment that both processes share a clock. Clock rollback within that allowance silently accepts a future cache.

4. **Minor — DST reset display is ambiguous, and its tests cannot detect a broken formatter.** `scripts/check-usage-pace.py:79`: under `TZ=America/Los_Angeles`, epochs `1793521800` and `1793525400` both display `Sun 11-01 01:30 local`, although one is PDT and the other PST. Include the offset or abbreviation. **Measured surviving mutation:** replacing the formatter’s entire return value with `"WRONG RESET"` still passes **79/79** cases. Assertions at lines 294 and 298 derive their expected text from the same formatter.

Additional coverage:

- **Matcher:** `Agent` agrees with the existing `Agent|Skill` registration and current [Claude Code documentation](https://code.claude.com/docs/en/hooks#subagentstart). No matcher defect found.
- **Payloads:** empty, malformed, ordinary spawn and `resume` payloads all deny at 95%, because stdin is discarded. Consequently the hook also denies a resume; it does not distinguish that from a new agent.
- **Worktree override:** with a temporary `.git` file and `CLAUDE_PROJECT_DIR` pointing at another checkout, only the working checkout’s override allowed spawning. The main checkout’s override did not.
- **Boundaries:** 79.95 returns OK correctly; `"95"` and missing `at` return CANNOT RUN. Below 90%, missing/stale caches and an exit-2 checker did not block.
- **Timing:** 25 full prompt-hook runs measured **73.5 ms median, 90.5 ms p95**, including a cache-argument injection shim. **68 ms per prompt is acceptable**; the unbounded stall is the concern.
- **Ambient pass:** the “another checkout” override test at line 367 passes because `elsewhere` does not exist. It does not establish behavior between two populated checkouts. Likewise, hook integration tests invoke filenames directly without exercising the registered matcher.

Required runs completed: **79/79 self-tests**; mutation diagnostic **27/27 killed, 0 survivors**. The mutation runner explicitly labels this `--only` run a diagnostic slice, not the full gate. No repository changes; no `~/.claude` modifications or `.claude/plans/` reads.

**NOT CONVERGED**
