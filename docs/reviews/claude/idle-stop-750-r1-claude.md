Reviewed head: 593dd524785cd35e318a830d909172f4e647a522

# idle-stop-750 r1 — Claude half

Subject: `scripts/check-idle-stop.py` decision log (backlog #750), `git diff origin/master...HEAD`.

What I ran:
- `python3 scripts/check-idle-stop.py --self-test`: 65/65 pass.
- Live probes with temp HOMEs under the scratchpad, never the real `~/.claude`.
- The 6 mutants this diff adds or re-anchors, built by hand on a copy of `scripts/` (the 4 new #750 ones plus the 2 re-anchored to `decide_why`/`home`). Each one turns its named case red. The edits apply exactly once.

## Findings

### 1. MAJOR — a payload string with a lone surrogate crashes the hook: exit 1 instead of 2, so the BLOCK is lost
`scripts/check-idle-stop.py:263` (`ensure_ascii=False`) and `:269-270` (`f.write` under `except OSError` only).

`json.loads` turns `"\ud800"` into a lone surrogate str. With `ensure_ascii=False` it reaches the utf-8 text writer, which raises `UnicodeEncodeError`. That is a `ValueError`, not an `OSError`, so the `except` does not catch it. The traceback escapes `main()` and the process exits 1. Claude Code treats that as a non-blocking hook error, so the stop goes through. This breaks two of the required properties: the log changed the exit code, and the failed write was not reported as one.

The trigger is real. `session_id`, `cwd` and, for rule (a), each task `description` are logged. A description cut in the middle of an emoji by a JS-side truncation is the likely carrier, because `JSON.stringify` writes the half pair as `\udXXX`.

**Reproduced:**
`printf '{"session_id":"\\ud800","cwd":"/x","background_tasks":[]}' | HOME=<tmp> PATH=/usr/bin:/bin python3 scripts/check-idle-stop.py --hook` prints a traceback (`UnicodeEncodeError ... surrogates not allowed`) and gives rc=1. Without the log this stop is a BLOCK (rc 2).

Fix: drop `ensure_ascii=False` (ASCII escapes cannot fail to encode). Or catch `Exception` around the whole log body, including the `json.dumps`, and add a case with a surrogate in `cwd`.

### 2. MAJOR — the NOT CHECKED warning no longer says why the payload was unreadable
`scripts/check-idle-stop.py:289` and `:295`.

`main()` binds `why` to the parse or read failure reason at `:283`. The new line `verdict, message, why = decide_why(...)` at `:289` overwrites it with the reason dict. The warning at `:295` interpolates `{why}`, so it now prints the dict repr where the bounded_read diagnosis used to be. On master the same line printed the parse error (`the input is not JSON ...`).

The message goes to stderr, which the human reads. The diagnosis that tells them what was wrong with the payload is gone. The case at self-test `:543` checks only `"NOT CHECKED" in err`, so nothing went red.

**Reproduced:**
`printf 'not json' | HOME=<tmp> python3 scripts/check-idle-stop.py --hook` prints `⚠ idle-stop guard: NOT CHECKED — the Stop payload is not a JSON object {'rule': 'unreadable'}. This stop is ALLOWED...` and gives rc=1.

Fix: rename one of the two variables (e.g. `why_rule`). Assert the bounded_read reason text in the `:543` case, and add a mutant for it.

### 3. MINOR — a non-regular file at the log path hangs the hook until the 10 s hook timeout
`scripts/check-idle-stop.py:268`.

`open(path, "a")` on a FIFO blocks with no reader. The hook is then killed at `timeout: 10` (`.claude/settings.json`), which makes it a non-blocking error, so a BLOCK becomes an allow. The house already knows this hazard: `_pace.read_regular` exists to refuse non-regular files, and mutation "main opens the transcript again, blocking: a FIFO holds the hook" guards the same class on the read side. The log write does not get the same protection.

The trigger is contrived: someone has to `mkfifo` the path.

**Reproduced:** `mkfifo <tmp>/.claude/idle-stop-log.jsonl` with `agent_id` set. The process was still running after 6 s and I killed it.

Fix: `os.open(path, O_WRONLY|O_APPEND|O_CREAT|O_NONBLOCK)`, then refuse it unless it is a regular file.

### 4. MINOR — 5 of the 8 rule names are never asserted
`scripts/check-idle-stop.py:221-247`.

The new cases assert `a`, `block` and `c`. `unreadable`, `stop_hook_active`, `subagent`, `usage` and `block-unseen` are never read by any case. If you swap any two of them, for example by labelling the usage allow `"a"`, every case still passes. That would log a false rule, and for `"a"` it would also attach a `tasks` list.

Since the stated purpose of the log is to name WHICH rule excused a stop, the reason dicts need a table case. Something like: one payload per rule, through `decide_why`, asserting `why["rule"]`. Not reproduced as a mutant run; it follows from grepping the self-test, which has no assertion on those five strings.

### 5. NIT — rotation has a check-then-act race
`scripts/check-idle-stop.py:266-267`.

Two concurrent hook processes can both see the file past the limit. The second `os.replace` then moves the first one's fresh one-line file onto `.1`, and the 2 MB generation is lost. Or `exists` is true and then `getsize` raises `FileNotFoundError`. That one is caught and reported, but that decision's line is dropped. Neither changes a verdict. Reasoned, not reproduced.

### 6. NIT — task descriptions can carry command text into a plain-permission file
`scripts/check-idle-stop.py:202`.

For rule (a), up to 80 characters of each live task `description` are logged. For shell tasks that can include command text, such as an env assignment. The file is created with the default umask (0644) under `~/.claude`. The number of tasks per line is also unbounded, because only each field is trimmed. A very long line is no longer a single atomic `O_APPEND` write, so concurrent lines could interleave. Reasoned, not reproduced.

## Checked and found sound
- `live_entries` reads `_live`, the same function `running_tasks` uses. The "(a) logs every listed entry" mutant kills the case it names.
- The log is never read: `idle-stop-log` / `LOG_NAME` is referenced only by `log_decision`'s caller and the self-test.
- All four new mutants and the two re-anchored ones turn their named case red. I ran them on a copy.
- The `decide_why.*` EXEMPT reasons in `scripts/check-fixture-variation.py` are true. `decide` and `main` forward all four arguments unchanged. There is exactly one direct `decide_why` call in the suite (self-test `:729`), and it reads `[2]`.
- The `prs` values are ints from `pending_ci`, and every other field goes through `str()`. Nothing else is non-serialisable, apart from finding 1.

VERDICT: NOT CONVERGED
