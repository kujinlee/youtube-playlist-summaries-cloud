# Round 8 — Claude half — `explainer-src-root-self-configures` (PR #295)

Subject includes `6a9bee20` (the r8 AST readiness case). Everything below was measured by running
the code, in a scratch mirror of the worktree, on port **7893**, with `HOME` redirected to a fake
home. No `pkill`. No git mutation. Port 7391 never bound.

## Verdict

**FINDINGS** — 1 High, 2 Medium, 1 Low.

**(a) Is there a new Blocking or High?** **Yes — one High, and it is in the TEST, not the runtime.**
The AST case added by `6a9bee20` is green on a live reproduction of the r7 High: I reintroduced the
corpse (`rc=0`, `serving … (pid N)`, pidfile written, **nothing listening**) and the suite still
reported `140/140 passed`.

**(b) Is any finding FIX-INDUCED in `start-restart` runtime code?** **Yes — finding 2, a Medium.**
r6's fix (`6c4b5a8c`) added a `409` response; the client that renders it (`page_chrome.py:329`) has
not been touched since r2 and renders it as `restart FAILED`, then tells the reader to run a manual
command. I report this because it is there, not because of the pre-committed consequence; applying
the split rule to a Medium is the coordinator's call, not mine.

Finding 1 is also fix-induced (by `6a9bee20`) but sits in the readiness **case**, so by the brief's
own parenthetical — *"the runtime code, not the tests"* — it is not the split trigger.
Finding 3 is **not** fix-induced: it arrives in `34b1c210`, the original feature commit.

---

## Findings

### [High] The new AST readiness case is green on a live reproduction of the r7 High

**Where:** `scripts/explainer-serve.py:2232-2267`

**What:** the case slices the child's statement list at the index of the statement *containing* the
readiness byte, and inspects only what follows it:

```python
k = next(i for i, s in enumerate(body) if "b'K'" in _ast.dump(s))
return body[k + 1:]
```

But the byte is not a bare statement — it lives inside a `try` (`:1364-1367`):

```python
try:
    os.write(w_fd, b"K")              # K: every step above succeeded; I am serving
except OSError:
    pass
```

So `body[k]` is the whole `try`, and **anything added after the write but inside that `try` is on the
far side of the byte and invisible to the case.** Codex's two bypasses were at the top level; the fix
closed exactly those two placements and not the class one indentation level in.

**Why it matters — measured, not argued.** Mutation M1b, one line, inside the `try`, after the byte:

```python
    os.write(w_fd, b"K")
    httpd.timeout = float(os.environ["EXPLAINER_TIMEOUT"])   # KeyError, not OSError
```

| | self-test | `start()` rc | printed | pidfile | listening |
|---|---|---|---|---|---|
| control | **140/140** | 0 | `serving … (pid 41626)` | 41626 | **YES** |
| **M1b** | **140/140 — GREEN** | **0** | `serving … (pid 41639)` | **41639** | **NO** |
| M3 (top-level step, positive control) | 139/140 — **[FAIL] nothing that can fail happens after the readiness byte** | — | — | — | — |

M1b is the r7 High verbatim: the parent announces a server, writes the pidfile and exits 0 with
nothing bound — the state the comment at `:1340` calls *strictly worse than the code it replaced* —
and the case written to make that impossible does not notice. M3 confirms the case is not simply
inert; it kills the one placement it was authored against.

A second, smaller hole in the same case: the first tail statement is checked only for the *name*
`close`, never the argument —

```python
ok = (isinstance(close_, _ast.Expr) and isinstance(close_.value, _ast.Call)
      and _ast.dump(close_.value.func).count("'close'") == 1)
```

so `os.close(r_fd)` substituted for `os.close(w_fd)` also stays green (M2, verified `140/140`).

**Why it shipped:** there is no `scripts/mutations/explainer-serve.json`. `grep -l explainer-serve
scripts/mutations/*.json` returns nothing, so none of this file's 140 cases has ever been shown to be
load-bearing — even though `:2281-2289` records that the `[FAIL] ` shape was repaired in r3
specifically so this file *could* join `--mutate .`. The class this round is an instance of is the
project's own *"fixing a PREMISE is not covering the BRANCH"*.

**Suggested fix (hypothesis, not verified):** stop slicing at a statement boundary. Walk the child
block with `ast.walk` and assert the property over *every* node that executes after the write —
simplest form: hoist the write out of the `try` (a bare `os.write` guarded by the existing
`except OSError` at the enclosing level, or accept the write's own failure as fatal), so
"after the byte" and "after `body[k]`" become the same set. Failing that, additionally assert
`len(body[k].body) == 1` so nothing can hide behind the write inside its own `try`. Either way, the
durable repair is a `scripts/mutations/explainer-serve.json` entry anchored on this case, with M1b as
the mutation — otherwise the next narrowing is invisible again.

---

### [Medium] A refused second press reports `restart FAILED` about a restart that is succeeding — and sends the reader to a manual command

**Where:** `scripts/page_chrome.py:329`, against `scripts/explainer-serve.py:1172-1176`

**What:** r6 added the refusal —

```python
if not RESTART_LOCK.acquire(blocking=False):
    self._send(409, json.dumps({"ok": False, "pid": pid,
                                "error": "a restart is already in flight"}).encode(), ...)
```

— and the client, unchanged since r2, funnels every non-2xx into the failure path:

```js
.then(function(x){if(!x.ok)return x.text().then(function(t){throw new Error(t);}); ...})
.catch(function(e){rfail('restart FAILED: '+e.message+' — run the commands below');});
```

**Why it matters.** Measured live: three concurrent `POST /_restart` gave `200`, `409`, `409`, and
the restart **succeeded** (old pid 47735 gone, new pid 47741 in the pidfile, port listening,
`.restart.log` correctly empty). The second tab is therefore told:

```
restart FAILED: {"ok": false, "pid": 47735, "error": "a restart is already in flight"} — run the commands below
```

with the help `<details>` forced open. Three things are wrong at once: the restart did not fail; the
status span shows raw JSON; and the reader is actively directed to run the manual restart against a
server that is mid-replacement. `rs.disabled = true` means this is unreachable by double-clicking one
button — it needs a second page, which is precisely the two-pages scenario r6's High was about, i.e.
the refusal path is only ever *reached* under the conditions where its rendering is wrong.

This is the branch's own signature class — *a message that names a cause that never happened* —
which r2 fixed once in `page_chrome`'s `_why` and r7 fixed again in the `_restart` log line.

**Fix-induced:** yes. `git log -S'a restart is already in flight'` → `6c4b5a8c` (r6 fix);
`git log --oneline master..HEAD -- scripts/page_chrome.py` → last touched `7b611620` (r2). The fix
introduced a status code its own client had no branch for.

**Suggested fix (hypothesis, not verified):** branch on `409` before the generic `!x.ok` throw —
re-enable the button, set `rsay` to *"another page is already restarting this server — waiting"*,
and enter `rwait(j.pid, …)` anyway, since the pid it is waiting to change is the same one. That turns
the second tab into a correct observer of the restart that is actually happening, and it reloads with
the first.

---

### [Medium] `RESTART_LOG` is silent on exactly the failure the pipe was built to detect

**Where:** `scripts/explainer-serve.py:1440-1477` (`respawn`), against `:1396-1416` (`start()`'s
`X`/EOF/timeout return)

**What:** `respawn`'s docstring commits to a contract:

```
⚠ Called from the BUTTON it runs detached, with no terminal to print to, so a failure
here is invisible by construction. It writes RESTART_LOG instead: a restart that did
not happen must leave a trace somewhere a person can look.
```

`RESTART_LOG` is written on two paths: the port-still-busy branch (`:1465`) and the `Popen` failure
in `_restart` (`:1216`). The third path — `return start()` at `:1477` returning **1** — writes
nothing. `start()`'s diagnosis is a `print` (`:1415`), and `_restart` spawns `--respawn` with
`stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL` (`:1206-1207`).

**Why it matters — measured on r7's own worked input.** With `~/explainers/.serve.log` made a
directory (the exact input r7 used to demonstrate the High), spawned detached exactly as `_restart`
spawns it:

```
listening   : NO
pidfile     : NONE            (respawn unlinked it at :1476, start() refused to rewrite it)
.restart.log: no such file — NOTHING WAS LOGGED
.serve.log  : a directory — the child's own output is unreadable too
```

Run in the foreground, the same tree prints the good r7 diagnosis —
`FAIL: forked pid 44454 but it reported that it did not become a server — the bind, the session
change or the log handoff failed…` — and under the button that sentence goes to `/dev/null`. The
message r7 spent a Low making precise is, on the button path, written where nobody can read it. The
reader is not left blind (the page's `rwait` times out and says *"it did not come back within 25s"*),
but the *why* — the whole point of the pipe — is lost, on the one input the branch chose as its
worked example.

**Fix-induced:** **no.** `respawn`, `RESTART_LOG` and that docstring promise all arrive together in
`34b1c210`, the original feature commit, and `master`'s `start()` already had a `FAIL … return 1`
path. This is a hole that has been open since the button was written and that seven rounds have not
looked at — not a fix's own wreckage.

**Suggested fix (hypothesis, not verified):** have `start()` return the observed cause rather than a
bare `1` (it already builds `why` at `:1410`), and have `respawn` write it to `RESTART_LOG` on a
non-zero return, with the same `NOT RESTARTED —` prefix the other two branches use. That also makes
the three failure causes one grammar in one file, instead of two-of-three.

---

### [Low] A natural refactor kills the readiness case with `StopIteration`, not a message

**Where:** `scripts/explainer-serve.py:2233-2245`

**What:** `_post_ready_statements` locates its subject with two bare `next(...)` calls over
`ast.walk(start)` — the `FunctionDef` named `start`, then the `If` whose test dumps with one `"Eq"`
and contains `"pid"` and `"0"`.

**Why it matters:** extracting the child block into a helper (`def _serve_child(w_fd): …`) — an
ordinary cleanup for a 60-line `if pid == 0:` — makes both `next()` calls raise, and the runner
reports `[FAIL] nothing that can fail happens after the readiness byte — StopIteration:`. Failing
closed is the right direction and `6a9bee20`'s message says so deliberately; the cost is that the
person who refactors sees an exception name where the property should be. Note also that
`count("Eq") == 1` matches `NotEq` as a substring — harmless today only because
`if verdict != b"K"` contains neither `"pid"` nor `"0"`.

**Suggested fix (hypothesis, not verified):** wrap the two lookups and raise a `RuntimeError` whose
text says *"could not locate the forked child block in start() — if it was refactored, re-point this
case; a case that cannot find its subject must go red"*.

---

## What I verified as SOUND (no finding)

- **r6's High is genuinely closed.** Two concurrent `python3 explainer-serve.py` invocations: A
  printed `serving … (pid 44993)`, B printed the `X` refusal and exited **1**, the pidfile named
  44993, which was alive and listening. The pipe does end the inference.
- **`--stop` immediately followed by a start** does *not* reproduce the `already serving`-about-a-
  corpse race (`SO_REUSEADDR` plus a prompt SIGTERM exit); ran it, start rc=0, correct new pid,
  listening after 2s, `--status` agreed. Reported as measured, not as a hypothesis I preferred.
- **The happy restart path, end to end:** old pid killed, new pid in the pidfile, port listening,
  `.restart.log` absent. The lock's asymmetric release behaves as documented.
- **The `with httpd:` / `os.close(w_fd)` / `os._exit(0)` tail as written is sound** — `__enter__` on
  `socketserver.BaseServer` returns `self` and cannot fail, and `w_fd` is open at that point. The
  finding above is about what the *case* permits, not about the shipped tail.
- **`/src/` paths** re-read this round: `src_root()` → `safe_path` → `is_file` → `relative_to`, with
  the no-second-read contract at `:1123` intact. Nothing new.

## Sanity numbers (all run this round, in the worktree)

| script | rc | cases |
|---|---|---|
| `explainer-serve.py` | 0 | **140/140** |
| `page_chrome.py` | 0 | 76/76 |
| `page_markup.py` | 0 | 74/74 |
| `check-plan-code.py` | 0 | 128/128 |
| `check-fixture-variation.py` | 0 | 64/64 |
| `check-ratchet-contract.py` | 0 | 41/41 |
| `check-selftest-counts.py` | 0 | 9/9 |
| `check-dashboard-entry.py` | 0 | 148/148 |
| `gen-dashboard.py` | 0 | 325/325 |
| `check-guard-coverage.py` | 0 | 37/37 |
| `check-backlog-closure.py` | 0 | 20/20 |
| `check-review-rounds.py`, `check-anchors.py`, `check-explainer-delivery.py`, `check-plan-file-tags.py` | 0 | — |
| `check-docs.py`, `check-arch-findings.py`, `check-vocabulary-collisions.py` | 0 | — |
| `check-test-counts.py` | **1** | **CANNOT RUN** — no `jest-results.json`; its own message says treat as NOT RUN. Environmental, not a branch defect |

Mutation results this round: **3 run against the new AST case, 2 survived** (M1b and M2), 1 killed
(M3, the positive control). Survivor rate on the freshest code in the branch: 2/3.
