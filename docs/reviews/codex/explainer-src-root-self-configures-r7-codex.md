<!-- codex-review: model=gpt-5.5 -->

## Verdict
FINDINGS

There is a new **High**. The r6 fix narrows the original race but does not close it.

## Findings

### High `start()` can still write the loser’s pidfile when another starter binds first
**Where:** scripts/explainer-serve.py:1316

**What:**
```python
gone, _status = os.waitpid(pid, os.WNOHANG)
...
if gone == pid:
    break
if port_busy(HOST, PORT):
    alive = True
    break
...
PIDFILE.write_text(str(pid))
```

**Why it matters:** this still accepts “my child has not died yet” plus “someone is listening” as proof that “my child is serving.” Two separate `python3 scripts/explainer-serve.py` processes are not covered by `RESTART_LOCK`, because it is only in-process. In that race, starter A’s child can bind first; starter B’s parent can see B’s child still alive before it reaches `ThreadingHTTPServer(...)`, then see A’s listener via `port_busy`, set `alive = True`, and write B’s pid. B’s child can then hit `EADDRINUSE` and die. That recreates the r6 High shape: pidfile names a corpse while a real server is running.

**Suggested fix:** use a cross-process lock around `start()`/`respawn()` or a parent-child readiness pipe. The strongest version is: child creates/binds the HTTP server, reports success to its own parent through a pipe, and only that parent writes the pidfile. A file lock also serializes separate shell invocations so the second process reaches the initial `port_busy` check after the first has already won.

### Medium `_restart` can permanently refuse browser restarts if the response send fails
**Where:** scripts/explainer-serve.py:1172

**What:**
```python
if not RESTART_LOCK.acquire(blocking=False):
    self._send(409, json.dumps({"ok": False, "pid": pid,
                                "error": "a restart is already in flight"}).encode(),
               "application/json")
    return
self._send(200, json.dumps({"ok": True, "pid": pid}).encode(), "application/json")
try:
    self.wfile.flush()
```

**Why it matters:** after the lock is acquired, `self._send(200, ...)` is outside the `try`. If the client disconnects while headers/body are being written, `_send` can raise before `Popen` runs. The old process is not replaced, and the lock is never released, so later page restarts get 409 forever. Separately, if `Popen` succeeds but the respawner exits before sending SIGTERM, the old process also survives with the lock closed. The CLI `--restart` still bypasses this in-process lock, but the page button is wedged for that server lifetime.

**Suggested fix:** release the lock on every path where no replacement has been durably handed off. At minimum, wrap the 200 send/flush before `Popen` and release on send failure. For post-`Popen` failures, consider making the respawner handshake back before `_restart` commits to the one-way lock, or move restart serialization to the child/process lock so failure does not strand browser restarts.
