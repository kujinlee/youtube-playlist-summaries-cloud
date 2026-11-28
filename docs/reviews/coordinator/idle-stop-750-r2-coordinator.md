# Round 2 — `idle-stop-750` (PR #652, backlog #750 step 1) — coordinator — Codex NOT CONVERGED; all folded

Codex reviewed `eafd6671`. The Claude half did not run this round, because rounds 2 and later alternate between the halves. All five findings are in `log_decision`, and round 1's own lock-and-rotation code caused every one of them (`fix_induced`). The rule is the same as in round 1: the decision log must never change the hook's verdict, its exit code or how long it takes.

| id | from | sev | finding | disposition |
|---|---|---|---|---|
| X1 | codex B | BLOCKER | `flock(LOCK_EX)` blocks for as long as another process holds the lock. `O_NONBLOCK` on the descriptor does not make `flock` nonblocking. A refusal can therefore reach the 10 s timeout and become an allow. | **Fixed:** the new `_open_log` takes `LOCK_EX \| LOCK_NB` and retries until one shared deadline, `LOG_WAIT_S` = 0.5 s. When the deadline passes it raises `OSError`, so the existing handler SAYS the write failed and the verdict stands. Case: a test process holds the lock, and the hook still exits 2 within 2 s and says so. Went RED first: `HUNG`. |
| X2 | codex M | MAJOR | After rotation, `fd` was closed. If the reopen then failed, `fd` still held the closed number, and `finally` closed it a second time. The `EBADF` raised there turned the BLOCK into a traceback and exit 1. | **Fixed:** the old descriptor stays open until the new one is open and locked (`old, fd = fd, new`, and only then `os.close(old)`). `_open_log` closes every descriptor it does not return, so no descriptor is closed twice. Case: the second `os.open` of the log path is made to fail, and the hook exits 2, says the write failed and raises nothing. Went RED first: `raised OSError`. |
| X3 | codex M | MAJOR | The reopened descriptor was never checked for being a regular file. A FIFO with a reader, put at the path between the rotation and the reopen, would be written to. | **Fixed:** the reopen also goes through `_open_log`, so it gets the same `S_ISREG` check and the same bounded lock. Case: a FIFO with a reader appears right after `os.replace`, nothing is written into it, and the failed write is said. ⚠ **This case did NOT go red on macOS against the round-1 code.** macOS `flock` refuses a FIFO with `EOPNOTSUPP` (measured), so the old code failed there by accident. Linux allows `flock` on a FIFO. The case's mutation, a reopen that bypasses `_open_log`, is red on both platforms. |
| X4 | codex M | MAJOR | Rotation closed the old file, and so released its lock, before the new file was locked. A writer already waiting on the old file then appended to `.1`, and the next rotation would destroy that line. | **Fixed:** once `_open_log` holds the lock, it checks that the locked file is still the file at the path (`_is_at`, `samestat`). If it is not, or if nothing is at the path because a rotation is halfway done, it closes the file and opens the path again, within the same deadline. Case, in two variants: the log is rotated away while the writer waits for the lock, with the new file either not created yet or already created by another writer. In both, the line lands in the new file and `.1` is unchanged. Went RED first: the line was in `.1`. A further case covers a path that keeps moving: it is retried only until the deadline, then reported as a failed write. Before the fix, that case was red too: the write went silently to the moved file. |
| X5 | codex m | MINOR | No case covered a held lock, a failed reopen after rotation, or a non-regular file at the reopen. | **Fixed:** the five cases above. Self-test count 72 → 77, and the docstring says 77. |

Mutations: 72 → 79, one per new guard: the lock taken blocking, the lock wait with no deadline, writing to a rotated-away file, a missing path mid-rotation treated as an error, the moving-path retry with no deadline, the reopen bypassing `_open_log`, and the old file closed before the new one is open. Three round-1 mutations were re-bound to the lines that moved into `_open_log`, with the same intent: the blocking open, the regular-file check and the 0600 mode.

REVIEW GAP: claude — alternation (round 2 is the Codex half's turn).

```yaml
round: 2
fixes_nontrivial: true
subject: idle-stop-750
halves:
  codex: ran
  claude: "REVIEW GAP: claude — alternation"
findings:
  - {id: X1, severity: Blocking, aim: deliverable, fix_induced: true, component: check-idle-stop, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: true, component: check-idle-stop, disposition: fixed}
  - {id: X3, severity: High, aim: deliverable, fix_induced: true, component: check-idle-stop, disposition: fixed}
  - {id: X4, severity: High, aim: deliverable, fix_induced: true, component: check-idle-stop, disposition: fixed}
  - {id: X5, severity: Medium, aim: deliverable, fix_induced: true, component: check-idle-stop, disposition: fixed}
```

Review: `docs/reviews/codex/idle-stop-750-r2-codex.md`.
