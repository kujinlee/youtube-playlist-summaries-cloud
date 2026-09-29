# Adversarial review — round 7 (Claude half) — `explainer-src-root-self-configures` (PR #295)

Subject: `024185f9` (the lock release) and `a5b0d95b` (the child's bind pipe), plus the branch.
Everything below was measured by running, in a scratch copy on port **7893** with a redirected
`$HOME`. The user's server on 7391 was never touched; no pattern kill was ever issued.

## Verdict

**FINDINGS — one new High.**

`a5b0d95b` moved `detach_streams()` to run **after** the child sends its `K` byte. When
`detach_streams()` fails, the child dies *after* saying "I am bound, and I am the one serving", so
the parent writes the pidfile for a corpse, prints `serving … (pid N)`, and **exits 0** — the exact
damage r6 and r7 exist to eliminate, on an input the pre-fix tree handles correctly. Control-proved
on two separate triggers.

The pipe design itself is right, and I verified it closes the race: **2/2 deterministic corpses on
the pre-fix tree, 0/2 on the fixed tree**, single-writer, no timing luck (method below).

## What I reproduced

### The corpse, deterministically — and the fix kills it

The coordinator's 6 natural-timing trials found 0 corpses on both trees; my own 8-way concurrent
race (6 trials per tree) also found **0 on both**, because extra starters mostly lose the
`port_busy` pre-check rather than widening the window. So I replaced luck with a barrier.

**Method (different from the 1s sleep):** a FIFO parks the forked child at exactly the pre-bind
point (inserted after `os.setsid()` in both trees, the same point in each). With the child parked,
a **foreign listener** takes the port. Nothing else ever writes the pidfile, so the final state is
unambiguously this process's own decision. Then the child is released and dies of `EADDRINUSE`.
This is precisely the case the r6 code's own comment admitted it could not handle.

| Tree | What `start()` printed | Final pidfile | Verdict |
|---|---|---|---|
| pre-fix `024185f9` | `serving … (pid 72471)` | `72471` (**dead**), foreign listener `72472` | ⛔ CORPSE, 2/2 trials |
| fixed `a5b0d95b` | `FAIL: forked pid 72496 but it never reported back within 2s. NOT RUNNING — the pidfile was left untouched.` | none | ✅ 0/2 trials |

An earlier two-process variant also showed the pre-fix tree printing `serving … (pid 71841)` for a
child that never bound; it is recorded only because the final pidfile check missed it there (the
competing writer won the file last), which is why I removed the competing writer.

### The pipe's attack surface — what I checked and found sound

- **Partial write / full buffer.** One byte into a freshly created, empty pipe: `PIPE_BUF` is at
  least 512 on every POSIX system, so `os.write` of 1 byte is atomic and cannot short-write. It
  returns 1 or raises. Correct as written.
- **`select` on a raw fd.** `os.pipe()` yields raw ints and `select.select` takes ints on POSIX.
  Correct. PEP 475 retries on `EINTR` with a recomputed timeout, so the ~2s budget holds.
- **Child killed between fork and write.** Forced it by `SIGKILL`-ing the child immediately after
  `os.fork()` returned in the parent: the write end closes, `select` reports ready, `os.read`
  returns `b""`, and the unconditional `break` after the read means no spin. `start()` returned 1
  and left the pidfile alone. Correct (the *message* is wrong — Low 6).
- **`X` path end-to-end.** Never previously demonstrated. Parked the child, took the port, released
  inside the budget: `FAIL: forked pid 74744 but it could not bind — something else is already on
  the port. NOT RUNNING — the pidfile was left untouched.` rc=1, pidfile absent. Correct.
- **fd leak if `fork()` raises.** Both fds leak, but `start()` is called at most once per process
  (`main()` once, `respawn()` once) and the exception propagates to process exit. Inert.
- **`os._exit` vs `return`.** Both explicit child exits use `os._exit`, so the child does not run
  the parent's `sys.exit`/atexit path. That is right — but it does **not** cover the two paths
  where the child raises (`detach_streams()`, `serve_forever()`), and the first of those is High 1.
- **Does binding before `detach_streams()` reintroduce the wedge that function prevents?** No. The
  wedge is `log_message` writing an access line on the parent's pipe during request handling, which
  is after `serve_forever()` and therefore after the detach. Constructing `ThreadingHTTPServer`
  writes nothing. The wedge is not reintroduced — a different failure is (High 1).
- **`respawn()` → `start()`.** Traced with the new pipe. `respawn` runs in a fresh single-threaded
  interpreter, so `os.fork()` is safe and the pipe behaves identically. `start()` is never called
  from the threaded server process (`_restart` uses `Popen`, not `fork`), so there is no
  fork-in-a-threaded-process hazard. The difference is not in the pipe but in where the output goes
  — Medium 3.
- **The never-released lock (`024185f9`).** I exercised the exact path by making `_send` raise
  `BrokenPipeError`: the lock **is** released, and a second press afterwards spawns normally. The
  permanent-409 bug is genuinely fixed. What the same run exposed is Medium 2.
- **Guards.** In the real worktree: `explainer-serve --self-test` 138/138 rc=0, `page_chrome`
  76/76, `check-fixture-variation` 64/64, `gen-dashboard` 325/325, `check-plan-code` 128/128,
  `check-ratchet-contract` 41/41, `check-selftest-counts` 18/18, `check-docs` 13/13. All rc=0.

---

## Findings

### [High] The `K` byte says "I am serving" before the child has finished becoming a server — `detach_streams()` after it restores the corpse, and `start()` exits 0 while claiming success

**Where:** `scripts/explainer-serve.py:1337-1345`

**What:**

```python
        try:
            os.write(w_fd, b"K")              # K: I am bound, and I am the one serving
        except OSError:
            pass
        os.close(w_fd)
        detach_streams()
        with httpd:
            httpd.serve_forever()
        os._exit(0)
```

`detach_streams()` (`:834`) is the only code between the `K` and `serve_forever()`, it can raise,
and it is **not** inside a `try`. When it raises, the child unwinds out of `start()` through
`main()` and dies — after the parent has already accepted `K` as proof and written the pidfile at
`:1373`.

**Why it matters:** measured on the fixed tree, two independent triggers, with the pre-fix tree as a
red control on the identical input.

Trigger A — `~/explainers/.serve.log` is a directory:

| Tree | stdout | rc | pidfile | listening |
|---|---|---|---|---|
| fixed `a5b0d95b` | `serving … (pid 74182)` + `IsADirectoryError` traceback | **0** | `74182` — **dead** | none |
| pre-fix `024185f9` | `IsADirectoryError` traceback, then `FAIL: … NOT RUNNING — the pidfile was left untouched.` | 1 | none | none |

Trigger B — `.serve.log` is a plain file with mode `000` (the more realistic one: a log created once
under different permissions):

```
serving /…/explainers on http://127.0.0.1:7893  (pid 79538)
PermissionError: [Errno 13] Permission denied: '/…/explainers/.serve.log'
rc=0
pidfile=79538 listening=[]      ⛔ CORPSE — pidfile names DEAD pid 79538
```

So on this input the branch is **strictly worse than the code it replaces**: the pre-fix tree
reports the failure honestly and leaves the pidfile alone; the fixed tree reports success, returns
0, and leaves a pidfile naming a corpse. That pidfile then drives the whole r6 damage chain the
commit message itself catalogues — `--status` says `⚠ stale — that pid is gone`, `--stop` says
`not running`, and `--restart` is the only way out.

It also reaches the **button**. Running the detached respawn exactly as `_restart` does
(`--respawn <pid>`, stdout and stderr to `/dev/null`) with the log broken:

```
listening=[]                      ← the old server was killed, no new one came up
pidfile=77140   ⛔ pid 77140 is DEAD
.restart.log: (nothing — no trace of the failed restart)
```

The reader presses Restart, the server goes away permanently, and nothing anywhere records why.

The framing worth keeping: this is the branch's own architecture-review class again, one level down.
The fix made the child *carry* its bind result, which is right — but the byte it carries asserts
more than the child has established at the moment it is sent. `K` is documented as "I am bound, **and
I am the one serving**"; at that point it is only the first half.

**Suggested fix (hypothesis, not verified):** move `detach_streams()` back **above** the bind
attempt, where `024185f9` had it, and keep everything else. The pipe survives the move — `detach_streams`
only `dup2`s fds 0/1/2 and `w_fd` is not among them — and a detach failure then kills the child
*before* it can send `K`, which the pre-fix tree demonstrates the parent already handles correctly.
The stated reason for the current ordering does not survive scrutiny anyway (Low 5). If the ordering
must stay, the equivalent repair is to send `K` only after `detach_streams()` has returned, and to
wrap the child's post-bind code so any exception becomes an `X` plus `os._exit(1)` rather than an
unwind through the parent's `main()`.

---

### [Medium] Moving `_send` inside the `try` silently cancels the restart, and logs a cause that never happened

**Where:** `scripts/explainer-serve.py:1189-1213`

**What:**

```python
        spawned = False
        try:
            self._send(200, json.dumps({"ok": True, "pid": pid}).encode(), "application/json")
            try:
                self.wfile.flush()
            except OSError:
                pass                  # the reader navigated away; the restart still proceeds
            subprocess.Popen([...])
            spawned = True
        except (OSError, ValueError) as exc:
            …f"not spawn the replacement: {type(exc).__name__}: {exc}\n"
```

`BrokenPipeError` is a subclass of `OSError`, so the very exception `024185f9` was written about —
`_send` ending in `wfile.write` and raising when the reader left — is now caught by the handler that
means "Popen failed".

**Why it matters:** measured by driving `_restart` with a handler whose `_send` raises
`BrokenPipeError(32)`:

```
Popen called      : 0 -> RESTART SILENTLY DROPPED
lock released     : True
restart.log says  : 2026-09-15 12:44:36 NOT RESTARTED — could not spawn the replacement: BrokenPipeError: [Errno 32] Broken pipe
second press Popen: 1
```

Two things, one of them the lock fix working correctly and one not:

1. The lock **is** released and the next press works — `024185f9` achieves what it set out to.
2. But the restart no longer happens at all on this path, and the comment three lines below still
   says *"the reader navigated away; the restart still proceeds"*. That was r6's explicit design
   (`_restart`'s docstring: "⛔ THE REPLY GOES FIRST, AND NOTHING AFTER IT MAY BLOCK"). Moving
   `_send` inside the `try` inverted it without saying so. A reader who clicks Restart and then
   navigates gets no restart.
3. `.restart.log` — the file that exists precisely because a detached failure is invisible — records
   a cause that is false. Nothing was spawned, and no spawn was attempted. This is the same class as
   the branch's own `#124` ("a note that reports a signal it may never have sent").

**Suggested fix (hypothesis, not verified):** keep `_send` inside the `try` for the lock's sake, but
distinguish the two failures — set a `replied` flag after `_send` returns, and in the handler write
either "could not reply to the restart request" or "could not spawn the replacement" accordingly. If
the r6 intent (restart proceeds regardless) is still wanted, catch the reply failure separately and
fall through to the `Popen` rather than skipping it.

---

### [Medium] `respawn()` promises a trace for a restart that did not happen, and a `start()` failure leaves none

**Where:** `scripts/explainer-serve.py:1396-1433`

**What:** the docstring states the contract —

```
    ⚠ Called from the BUTTON it runs detached, with no terminal to print to, so a failure
    here is invisible by construction. It writes RESTART_LOG instead: a restart that did
    not happen must leave a trace somewhere a person can look.
```

— but `RESTART_LOG` is written in exactly one branch, the "port still busy after 20s" one. The
function then ends `PIDFILE.unlink(missing_ok=True); return start()`, and every way `start()` can
fail reports itself with `print()` to a stdout that `_restart` set to `DEVNULL`.

**Why it matters:** measured (the same run as High 1's button case) — the old server is gone, no new
server is listening, and `.restart.log` is empty. Every failure mode of `start()` inherits this:
the `X` path, the 2s-timeout path, and High 1. The docstring's promise holds for one branch out of
four.

**Suggested fix (hypothesis, not verified):** have `respawn()` check `start()`'s return value and
append the same kind of line to `RESTART_LOG` when it is non-zero — and, because `start()` currently
signals failure only through `print` and an exit code, give it a way to hand back *why* (return the
message, or have it write `RESTART_LOG` itself when not attached to a terminal).

---

### [Medium] `start()` abandons a child it could not account for; that child can bind afterwards, leaving a server nothing can stop

**Where:** `scripts/explainer-serve.py:1363-1372`

**What:**

```python
    if verdict != b"K":
        …
        print(f"FAIL: forked pid {pid} but {why}. NOT RUNNING — the pidfile was left untouched.")
        return 1
```

The parent gives up and exits. The child is neither killed nor reaped, and nothing prevents it from
binding a moment later.

**Why it matters:** measured — parked the child past the 2s budget, then released it:

```
FAIL: forked pid 73058 but it never reported back within 2s. NOT RUNNING — the pidfile was left untouched.
listening=[73058]    pidfile=none
curl http://127.0.0.1:7893/  -> http=200
--status : listening : yes …  pidfile : (none)
--stop   : not running
after --stop, listening=[73058]
```

A server that answers HTTP 200, that `start()` declared NOT RUNNING, that has no pidfile, and that
`--stop` cannot stop. `--restart` then burns the full 20s and logs `NOT RESTARTED`. Recovery
requires `lsof` and a manual kill.

**This is pre-existing, not introduced** — the pre-fix tree behaves identically (same 2s budget,
same abandonment), which I verified. I file it because `start()`'s failure semantics are this
round's subject and the new design makes the repair obvious: the parent now knows unambiguously
that the child never claimed the port, so it is entitled to `SIGTERM` it.

**Suggested fix (hypothesis, not verified):** on `verdict != b"K"`, `os.kill(pid, SIGTERM)` followed
by `os.waitpid(pid, 0)` before returning 1. On the `X` path the child is already gone and the kill is
a harmless `ProcessLookupError`; on the timeout path it is the whole point.

---

### [Low] The stated reason for "BIND BEFORE DETACHING" is a benefit the code does not deliver

**Where:** `scripts/explainer-serve.py:1326-1336`

**What:**

```python
        # ⚠ BIND BEFORE DETACHING. `detach_streams` exists because a child on the parent's stdout
        # wedges on its first access-log line; but a bind failure before it is detached is a
        # message the operator can still see, and the byte below is what the parent acts on.
        try:
            httpd = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
        except OSError:
            try:
                os.write(w_fd, b"X")          # X: I could not bind
            except OSError:
                pass
            os._exit(1)
```

The bind-failure branch prints nothing. It swallows the `OSError`, writes one byte, and
`os._exit(1)`s. There is no message for the operator to see.

**Why it matters:** measured on the `X` path — the only text that appeared was the parent's
`FAIL: forked pid 74744 but it could not bind — something else is already on the port.` The child
contributed nothing. The comment is the sole justification for an ordering that costs the High
above, and it asserts a property the code does not have. In a file whose self-test reads its own
source, a comment that is wrong about the code beside it is load-bearing.

**Suggested fix (hypothesis, not verified):** delete the claim along with the ordering (see High 1).
If the ordering is kept for some other reason, state that one instead.

---

### [Low] The timeout message reports a 2s wait that did not happen

**Where:** `scripts/explainer-serve.py:1368-1371`

**What:**

```python
        why = ("it could not bind — something else is already on the port"
               if verdict == b"X" else
               "it never reported back within 2s")
```

`verdict` is `b""` both when the budget genuinely expired and when the child died before writing —
in which case `select` fires on EOF immediately and `os.read` returns `b""`.

**Why it matters:** measured by `SIGKILL`-ing the child the instant `os.fork()` returned. The
message was `it never reported back within 2s`, for a child that reported by dying within
milliseconds. The operator is pointed at a hang; the cause was a kill. Same class as Medium 2 and
`#124` — a diagnostic naming a mechanism that did not occur.

**Suggested fix (hypothesis, not verified):** distinguish EOF from expiry. Track whether the read
returned `b""` (write end closed → "it exited before reporting") versus the loop running out
("it never reported back within 2s"), and mention `waitpid`'s status on the former.

---

### [Low] The case pinning the r7 property asserts source ORDER, not the property — it is green on High 1

**Where:** `scripts/explainer-serve.py:2158-2159`

**What:**

```python
        case("the pidfile is claimed ONLY after the child says it bound",
             lambda: _start.index('verdict != b"K"') < _start.index("PIDFILE.write_text"))
```

**Why it matters:** the case reads where two strings sit relative to each other in the source. High 1
leaves both strings exactly where they are, so the case stays green while the pidfile is written for
a corpse — I ran it: 138/138 on the tree that produces the corpse. The name promises the property
("claimed only after the child says it bound"); the lambda measures the mechanism. This repo has a
memory note for exactly this shape ("Assert the PROPERTY, not the mechanism").

Related and worth stating rather than filing separately: `scripts/mutations/` has no
`explainer-serve.json`, so none of these 138 cases has a manifest-recorded falsifier that CI runs.
That absence is already **recorded as a known debt** with a measured reason at
`scripts/check-plan-code.py:914-925` (`mutate_delivered` copies only `scripts/`, and the suite reads
`docs/`), so it is not a new omission — but it does mean the r6/r7 concurrency cases are
source-string assertions with nothing checking them back.

**Suggested fix (hypothesis, not verified):** add a case that runs the thing — fork a child in a
temp `$HOME` whose `.serve.log` cannot be opened, and assert `start()` returns non-zero and the
pidfile is absent. That is a behavioural falsifier for High 1 and needs no repo files outside the
temp tree, so it may also be the wedge that gets this file into the mutation manifest.

---

### [Low] A 409 is rendered to the reader as `restart FAILED`, for a restart that is in flight and will probably succeed

**Where:** `scripts/page_chrome.py:323-330`

**What:**

```js
fetch('/_restart',{method:'POST'})
.then(function(x){if(!x.ok)return x.text().then(function(t){throw new Error(t);});
return x.json();})
…
.catch(function(e){rfail('restart FAILED: '+e.message+' — run the commands below');});
```

**Why it matters:** the second presser sees `restart FAILED: {"ok": false, "pid": N, "error": "a
restart is already in flight"} — run the commands below`, with the fallback `<details>` forced open.
Raw JSON in a status line is cosmetic, but the sentence is wrong: the restart is in flight and is the
most likely outcome. The reader is told to intervene at the moment intervention is least useful. Mild,
recoverable, and the fallback commands are harmless if followed.

**Suggested fix (hypothesis, not verified):** branch on `x.status === 409` before the generic
`!x.ok` throw, render the server's `error` string as a status rather than a failure, and re-enable
the button without opening the help.

---

## On convergence

Six of the eight findings are Low or Medium and none of those would justify another round on their
own. The High is a genuine regression introduced by this round's own fix, control-proved on two
triggers, with a small and non-reopening repair. Noting for the coordinator, without arguing the
call: `a5b0d95b` fixed a defect in `6c4b5a8c`, `024185f9` fixed a defect in `6c4b5a8c`, and this
half now reports a defect in `a5b0d95b` — three consecutive rounds whose findings came from the
previous round's fix, in one component. That is the arming shape `docs/dev-process.md` describes for
Phase 6, and it is the coordinator's judgement whether the answer here is *thrashing* or simply a
hard concurrency surface converging.
