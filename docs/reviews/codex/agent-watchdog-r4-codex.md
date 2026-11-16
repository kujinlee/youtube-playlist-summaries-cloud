<!-- codex-review: model=gpt-6.1-sol -->

- **MINOR — scripts/agent-watchdog.py:759:** `shlex.split` does not test shell expansion. On a temporary copy, replacing `shlex.quote(w.spec())` with `(w.spec() if shlex.quote(w.spec()) == w.spec() else '"' + w.spec() + '"')` survives: `76/76 self-test cases passed`. Concrete input: `b=/w/$(printf expanded)` round-trips through `shlex.split`, but an actual shell changes it to `b=/w/expanded`. This is a witness gap; production quoting is correct.

- **MINOR — scripts/agent-watchdog.py:245:** Re-arm formatting loses accepted window precision. Concrete input: `QUIET_MIN=4.500001`, with one quiet builder and another active. The command prints `4.5`, which `parse_args` refuses because it equals 270 seconds. The original watchdog works; the suggested re-arm fails.

Required check results:

> 76/76 self-test cases passed

> OK — delivered scripts mutated: 1 file(s), 70 mutation(s), 70 killed, 70 attributed to the case each names, 0 survivor(s) — measured over ONLY scripts/agent-watchdog.py — a DIAGNOSTIC slice, not the gate

VERDICT: CONVERGED
