<!-- codex-review: model=gpt-6.1-sol -->

1. **P2 — Unreadable meter is silently ignored below 80%.** [scripts/check-usage-pace.py:372](scripts/check-usage-pace.py#L372) discards `line_note` in the low-usage branches. Concrete input: fresh cache at 50%, reset three days away, missing `--meter` path. Observed: `--hook prompt` exits 0 with empty stdout; ordinary CLI reports only `OK: weekly usage is below 80%`. The required notice about falling back to 90% is absent.

2. **P2 — Negative meter percentages are accepted as usable readings.** [scripts/check-usage-pace.py:283](scripts/check-usage-pace.py#L283) checks finiteness but permits negative usage. Concrete input: `now=1800000000`, reset `1800086400`, meter row at `1799999940` with `used_percentage=-100`, and fresh cache at 91%. Observed: `pace_line()` returns `(97.0, '')`; the wake hook exits 0 with empty stdout, allowing the wake without an override. An invalid negative reading should be rejected, producing the unreadable-meter fallback of 90% and refusal.

3. **P3 — The stdin-reader docstring retains an obsolete fixed-threshold claim.** [scripts/check-usage-pace.py:416](scripts/check-usage-pace.py#L416) says “a 95% wake is still DENIED.” Concrete input: midnight meter reading 50%, reset one day away, cache at 95%, empty wake payload. Observed: wake hook exits 0 with empty stdout because the stop is 97%. Its “two deadlines” claim at line 420 also omits the newly added meter-read deadline.

Validation: `291/291` self-tests passed. All 11 new mutations failed every named expected case on temporary copies. All 113 manifest edit targets exist; the full mutation sweep was not run. Hostile-file probes returned promptly, and no HOME escape or stop outside `[90, 97]` was found. Nothing under `.claude/plans/` was read.

VERDICT: NOT CONVERGED
