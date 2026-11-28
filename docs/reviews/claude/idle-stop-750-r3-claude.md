Reviewed head: 5677ff59293fea9c7d6e4f00a064be0de915e150

# idle-stop-750 r3 — Claude half

Subject: `scripts/check-idle-stop.py` `log_decision` and `_open_log` (the round-2 fold), plus `git diff origin/master...HEAD` for regressions.

Mandate: refute the claim that the decision log can never change the hook's verdict, its exit code or its bounded timing.

## What I ran

- `python3 scripts/check-idle-stop.py --self-test`: 77/77 pass, in 2.8 s.
- `python3 scripts/check-plan-code.py --mutate . --only scripts/check-idle-stop.py`: all 79 mutants were killed, each by the case it names, and the re-control passed (rc=0). Each case added in round 2 therefore goes red without its fix. The `--only` run covers only this script, so it is a diagnostic slice and not the full mutation gate.
- **A concurrency stress test** against a temporary directory under the scratchpad, never the real `~/.claude`. Setup: 16 processes each called `log_decision` 300 times, with `LOG_MAX_BYTES` lowered to 3000, which forced 161 rotations. `os.replace` was patched to give each rotated generation a unique name, so a lost line would be visible. Result: all 4800 lines were written, none were duplicated, no failure was reported on stderr, and the slowest single write took 0.27 s. Every rotation therefore happened under the lock, and no line landed in a file that had already been rotated away.
- **Probes of the real `--hook` process**, with a temporary `HOME` and `gh` removed from `PATH`. For each probe I ran the same input against this head and against an `origin/master` copy of `scripts/` and compared the exit codes:
  - deeply nested `cwd` and `session_id` values, at depths 10 to 100000;
  - a directory, a FIFO and a held lock at the log path, from code reading plus the cases in the suite.

## Attempts that did not refute the claim

- **The timing bound holds.** The first `_open_log` waits at most until the deadline, and so does each pass of its moving-path loop. The deadline is checked after every `BlockingIOError` and after every mismatch on `_is_at`. The reopen during rotation shares the same deadline. If the deadline has already passed, that reopen makes exactly one uncontended attempt, and a contended one fails on its first `BlockingIOError`. Worst case is about `LOG_WAIT_S` + 10 ms of sleep granularity + one open. Against the 10 s hook timeout (`.claude/settings.json`) with `GH_TIMEOUT_S` = 3.0, that leaves more than 6 s of margin.
- **No descriptor is closed twice and none leaks.** `_open_log` has three exits, and each one closes every descriptor it opened: on a mismatch it calls `os.close` before looping, on any raise it closes in the `except BaseException` handler, and on success it returns the descriptor. In `log_decision`, a failed reopen leaves `fd` as the old, still-open descriptor, and `finally` closes it once. A successful reopen swaps the two with `old, fd = fd, new` before `os.close(old)`.
- **A directory, a FIFO or a symlink at the path** is either refused or harmless:
  - A directory gets `EISDIR` from `os.open`, which runs outside the `try` that would close a descriptor, so there is none to leak.
  - A FIFO with no reader gets `ENXIO`; with a reader, the `S_ISREG` check rejects it.
  - A path replaced mid-wait fails `_is_at` and is reopened, then rejected as above.
  - A symlink to a regular file passes `samestat`, because `stat` follows it. Rotation then renames the link itself. That is harmless to the verdict.
- **A `.1` that is a directory** makes `os.replace` raise `OSError`. The error is caught and reported, and the verdict stands. Every later write then fails the same way and is reported each time. That loses log lines, but it does not change the verdict.
- **The refactor is behaviour-preserving.** `running_tasks` now goes through `_live`, and the filter it applies is unchanged. Every `_decide` return gains a `why` dict and keeps the same verdict and message.

## Findings

### 1. NIT — the log line is built outside the `try`, and only `OSError` and `ValueError` are caught

**Where:** `scripts/check-idle-stop.py:321` (the `line = json.dumps(...)` call, together with `str(d.get("session_id"))` and `str(d.get("cwd"))`) and `:335` (`except (OSError, ValueError)`).

**What breaks:** any other exception escapes `main()`, and the process exits 1, which is an ALLOW. Examples are a `RecursionError` from `str()` of a deeply nested value, a `TypeError` from a future `why` field that cannot be serialised, and a `MemoryError`.

**Reproduction:** calling `main(["--hook"], stdin_bytes=...)` in-process with `cwd` nested 90000 or 100000 deep raised `RecursionError` at `log_decision` `:321`. The `origin/master` copy returns 2 on the same input.

**Not reachable from the production path today:** in a real `--hook` process, `bounded_read.parse_json` already gives up at a depth of about 993. The payload is then NOT CHECKED, and this head and master both exit 1, so the two match. At depth 991, which is the deepest that still parses, both exit 2. I measured this at depths 991–998 on Python 3.14.4.

**Why I filed it anyway:** the docstring states the property unconditionally ("never changes the verdict"), but the code holds it only because the current inputs are well-behaved.

**Fix (two lines):** build `line` inside the `try`, and catch `Exception` there. Writing to the log is best-effort, and it is the only code inside that block.

### 2. NIT — a short `os.write` is not detected

**Where:** `scripts/check-idle-stop.py:334`.

**What breaks:** on a disk that is nearly full, `os.write` can return fewer bytes than the line without raising. The log then holds a torn line, and the next decision is appended directly after it. A reader of the JSONL sees one unparseable record. The verdict is not affected. This only matters for the log's purpose, which is tracing a false allow.

**Fix:** compare the return value with the line's length and raise `OSError` when they differ. The existing handler then reports it.

VERDICT: CONVERGED
