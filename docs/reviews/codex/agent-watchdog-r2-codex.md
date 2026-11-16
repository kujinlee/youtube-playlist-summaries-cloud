<!-- codex-review: model=gpt-6.1-sol -->

- **MAJOR — scripts/agent-watchdog.py:229 (XM1/CF1): activity remains masked by the maximum mtime.** Concrete input: retain a file stamped `4102444800`, then rewrite another file every poll with ordinary current mtimes. With `QUIET_MIN=10`, reproduction exited 1 and reported `QUIET a` after ten writes. Deleting a nonmaximum file likewise left `newest()` unchanged. The fold fixes indefinite activity from a future stamp by introducing false quiet reports during continuing activity.

- **MAJOR — scripts/agent-watchdog.py:207,231: clock steps still distort the quiet window.** Concrete input: unchanged worktree, ten-minute window, wall clock advances one hour after the first 60-second sleep. Reproduction reported 61 minutes quiet and exited after only 60 elapsed seconds. A backward step extends the wait instead. The elapsed timer uses `time.time`, contradicting the fold’s clock-step claim.

- **MAJOR — scripts/agent-watchdog.py:130–134 (XM3): `.git` validation races with opening it.** Concrete input: `.git` is regular when `isfile()` checks it; replace it with a FIFO before `open()`. Deterministically scheduling that replacement reproduced a blocked reader until the harness supplied a writer. This blocks the entire watchdog, including other builders.

- **MAJOR — scripts/agent-watchdog.py:157,226: malformed gitdir pointers escape builder isolation.** Concrete input: builder b’s regular `.git` contains `b"gitdir: bad\x00path\n"`, followed by valid builder a. Reproduction raised `ValueError: stat: embedded null character in path`, aborting before a was judged and without a CANNOT RUN report.

- **MINOR — scripts/agent-watchdog.py:207: the default production clock is untested.** An in-memory mutation replacing `clock=time.time` with `clock=lambda: 0` survived: `"60/60 self-test cases passed"`; mutant exit 0. Production watching would never reach its quiet boundary. Required baseline results were `"60/60 self-test cases passed"` and `"OK — delivered scripts mutated: 1 file(s), 53 mutation(s), 53 killed, 53 attributed to the case each names, 0 survivor(s) — measured over ONLY scripts/agent-watchdog.py — a DIAGNOSTIC slice, not the gate"`.

VERDICT: NOT CONVERGED
