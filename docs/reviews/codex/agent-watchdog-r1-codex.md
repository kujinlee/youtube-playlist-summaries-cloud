<!-- codex-review: model=gpt-6.1-sol -->

- **MAJOR — scripts/agent-watchdog.py:205:** A future mtime prevents quiet detection. Input: valid worktree, `QUIET_MIN=10`, one file stamped `armed + 86400`, then no activity. With an injected clock, the watchdog remained running after 20 minutes with empty stdout. It cannot report quiet until 24 hours plus 10 minutes after arming.

- **MAJOR — scripts/agent-watchdog.py:148:** Git metadata errors escape without a watchdog report. Input: `.git/index` is a symlink to `index`. Observed uncaught `OSError: [Errno 62] Too many levels of symbolic links`, with empty stdout. Only `FileNotFoundError` is handled here; this also prevents reporting any other quiet builders in that poll.

- **MAJOR — scripts/agent-watchdog.py:119:** A malformed `.git` can block observation indefinitely. Input: `mkdir builder; mkfifo builder/.git`, then watch `builder` with no FIFO writer. The subprocess timed out with no stdout or stderr because `open()` blocks before polling. Neither this builder nor subsequent builders receive a CANNOT RUN report.

- **MINOR — scripts/agent-watchdog.py:160:** A directory is accepted as a transcript. Input: `10 builder=/valid/worktree:/existing/directory`. The injected-clock probe exited 1 with `0 CANNOT RUN` and claimed `no file, git or transcript activity for 10 min`. No transcript file was observed; unrelated directory changes can also delay the quiet report.

- **MINOR — scripts/agent-watchdog.py:121:** Error-handler coverage has a surviving mutation. In memory, replaced `except (OSError, UnicodeDecodeError) as exc:` with `except OSError as exc:`. The mutant still returned 0 and printed `51/51 self-test cases passed`; a `.git` containing invalid UTF-8 would now escape as a traceback instead of CANNOT RUN. Required check results:
  
  `51/51 self-test cases passed`
  
  `OK — delivered scripts mutated: 1 file(s), 43 mutation(s), 43 killed, 43 attributed to the case each names, 0 survivor(s) — measured over ONLY scripts/agent-watchdog.py — a DIAGNOSTIC slice, not the gate`

VERDICT: NOT CONVERGED
