Reviewed head: 24d0380d192a8bcda1271b0bf452f594b1ef013e

# Round 3, Claude half: `explainer-port-631` (PR #651, backlog #631)

Scope: the round-2 fold (`git diff 1745c1b9 24d0380d`) and the whole branch against `origin/master`. Every probe ran on
ephemeral ports with temp roots under the session scratchpad. Nothing touched 7391 or any process on it.

## What was run

- `python3 scripts/explainer-serve.py --self-test` at HEAD: **343/343 passed** (85 s).
- **A real legacy server.** I started a server from `origin/master`'s `scripts/explainer-serve.py` in a temp checkout on
  a non-default port (56877). ps showed the framework build:
  `…/Python.app/Contents/MacOS/Python scripts/explainer-serve.py`. I then replaced the file in place with HEAD's copy,
  the way a `git pull` does. `--status` gave rc 0 "ours, older code". `start` gave rc 0 "already serving (older code)",
  both through a **symlinked checkout** and through `./scripts/explainer-serve.py` (shebang). `--stop` through the
  symlinked checkout gave rc 0 "stopped pid … (older code)". **The r2 Y2 fold works: an older server on a non-default
  port can be stopped.**
- **A real current server** (`python3 scripts/explainer-serve.py`, then `--stop`): rc 0 both times. Only `.serve.log`
  was left afterwards: no record and no `*.tmp`.
- **Concurrent starts**, two CLI processes per trial: 12/12 trials gave `(FAIL, SERVING)`, with no `*.tmp` left. Under
  36 busy-loop processes on 12 CPUs (load average 68) 7/8 trials gave `(FAIL, SERVING)` and **1/8 gave `(ALREADY,
  SERVING)`**, meaning the two starts ran one after the other. No trial failed both starts, so the 2 s wait held even at
  that load.
- **A record write that fails** (the token path is a directory): rc 1, the child is gone, the port is free, and no
  `*.tmp` is left.
- `argv_runs_script` was called directly with 23 argv shapes (listed under F5). Hand mutations on temp copies of
  `scripts/` were compared with an unmutated control copy, which fails the same 4 repo-dependent cases each time.

## Findings

### F1: MAJOR. A legacy server started from ANOTHER CHECKOUT that serves the same root is "a program that is NOT explainer-serve". Start and stop give rc 3. `fix_induced: false`

`scripts/explainer-serve.py:1628` (`bound_legacy` → `argv_runs_script(…, SCRIPT_FILE)`). The default `ROOT` is
`~/explainers` (`:142`), and every checkout and worktree shares it. In this repo sessions run from
`.claude/worktrees/*`. So the owner's older server holds 7391 and the pid in `~/explainers/.serve.pid`, and the OS
reports that pid as the listener. If that server was started from the main checkout, then the delivery doc's
`python3 scripts/explainer-serve.py`, run from any worktree, gets this:

```
NOT STARTED — NOT this server: port 56877 on 127.0.0.1 is held by a program that is NOT explainer-serve — pid 18318
(…/Python scripts/explainer-serve.py). … choices: run on another port …   rc=3
```

**Reproduced:** a master-code server was started from temp checkout T, and the worktree's copy was run against the same
root and port. `--stop` from the worktree also refuses with rc 3. The delivery doc (§4) tells the skill to put this to
the user as a foreign program. That contradicts the doc's own line that an older server "IS this server … never present
it to the user as one", and it contradicts the requirement that a server "started from older code … can still be
started, reported and stopped". It fails closed: nothing is signalled.

**Evidence that it predates round 2:** the exact-path rule came in with the r1 fold `9b42334e`. Its own cases encode it:
`git show 9b42334e:scripts/explainer-serve.py` line 5372, "…another checkout's copy… is not this file", and line 5687,
"…or runs another copy, is not ours". The r2 fold moved where the program is found in argv. It did not change what the
program is compared against.

**Fix, which is a decision for the coordinator.** The binding is already strong: this root's legacy pidfile names the
pid, and lsof reports that pid as this port's listener. Since r2, the program must also be the interpreter's program,
not just any argument. Given that, accepting a program whose basename is `explainer-serve.py` would admit another
checkout's copy. That loosens the r1 X2 "another copy" case, so it is the owner's call. If the exact-path rule is kept,
then the message must not say "NOT explainer-serve", and §4 must say that rc 3 can be our own older server started from
another checkout.

### F2: MINOR. A legacy `.serve.pid` read on every port makes `--stop` on an idle port give rc 3, and makes `--status` show another port's pid. `fix_induced: true`

`scripts/explainer-serve.py:164-168` (`pidfile_candidates` now returns `root / LEGACY_PIDFILE` for every port; this is
the round-2 change). `stop()` at `:2730` then takes the legacy pid as this port's recorded pid. If that pid is alive
because it serves some OTHER port, the code goes on to `listener_verdict`, which finds nothing on this port and returns
"foreign". The result is rc 3 and "pid N is not our server". **Reproduced:** with a legacy server on 56877,
`EXPLAINER_SERVE_PORT=56878 --stop` gives

```
NOT STOPPED — pid 18318 is not our server (…/Python scripts/explainer-serve.py); it was left alone. Kept the pidfile …/.serve.pid   rc=3
```

and `--status` on 56878 prints `pidfile   : 18318` with no stale mark.

This answers the question for the calling skill: yes, it is a real defect, though a narrow one. The usage text says
`--stop` on nothing running is "0 … not running". §4 maps rc 3 to "put the choice to the user", so the skill raises a
false "another program" prompt about the owner's own server. It is reached by a second `--stop`, or a `--stop` before a
restart, on any port other than the legacy server's own while that server lives. The fold agent's noted risk is real.

**Fix:** a legacy-pidfile pid applies to a port only when `bound_legacy(pid, port)` holds. Otherwise skip it in
`recorded_pid`, which falls back to the per-port path, and `stop` then says "not running", rc 0. Add a case: a live
legacy server on port A and `--stop` on port B give rc 0 and "not running", with A still alive.

### F3: MINOR. When the child's record write fails, the parent says "nothing is listening", and §4 says re-run. The cause is only in `.serve.log`. `fix_induced: true`

`scripts/explainer-serve.py:2665-2669` (round 2 added the child's write-failure exit) and `:2703` (the parent's
message). The child's `FAIL: could not write the record … ([Errno 21] Is a directory …)` goes to the detached
`.serve.log`. The parent prints `FAIL: forked pid N but 127.0.0.1:P never answered as it — nothing is listening.` and
returns rc 1. §4 reads rc 1 as "another program won the port in between … re-run", so a permanent cause (a directory,
EACCES, a read-only filesystem) gives the same rc 1 on every re-run. **Reproduced** with a directory at
`.serve.<port>.token`.

The parent also waits the full 2 s for a child that has already exited. A `waitpid(pid, WNOHANG)` in the loop would
catch that early. **Fix:** when the child has exited, the FAIL line should name `.serve.log` (or its last line), and §4
should stop saying that every rc 1 is a lost race.

### F4: MINOR. New guards that no case kills, and a race case that can pass without a race. `fix_induced: true`

All of these were added by the r2 fold.

- **A surviving mutant: the interpreter guard's `isfile` clause.** At `:1583`, `(k > 1 and not
  os.path.isfile(" ".join(toks[:k])))` was deleted. Result: 339/343, the same failures as the control, so it survives.
  Without the clause, `"/bin/sh /x/python3 <script>"` makes `k = 2` an "interpreter", and a shell that runs our path as
  its argument passes. No case puts a python-named token after a non-Python argv[0].
- **A surviving mutant: the temp-file cleanup.** At `:1442-1444` the `unlink(tmp)` was removed from `write_identity`'s
  `except`. It survives. The r2 Y3 case checks the record and the port, but not the directory. **Reproduced:** the
  mutant leaves `..serve.<port>.token.<rand>.tmp` behind, and HEAD leaves nothing.
- **A redundant line (equivalent, so no mutation can kill it).** At `:1601`, `if ch in "cm": return False` can be
  deleted with no change in behaviour, because `c` and `m` are not in `_PY_FLAGS` and already fall through to
  `return False`. The mutant survives for that reason. Either drop the line or say in a comment that it only documents
  intent.
- **The race case can pass vacuously.** `_concurrent_starts` (`:5970`, `:5994`) takes `sorted(rc)[0]`. It passes just
  as well when the two starts run one after the other (`already serving`, rc 0), in which case nothing races. Measured
  under load: 1 trial in 8 was sequential. Make it assert that both starts forked (one rc 0 "serving" and one rc 1
  FAIL), or report a vacuous run as such and retry it.

(A hand mutant that made `forget_own` always unlink the pidfile was killed by the r2 Y3 case.)

### F5: NIT. A spaced script path whose leading part exists as a directory is not recognised. `fix_induced: true`

At `:1614`, `if os.path.exists(cand): return os.path.realpath(cand) == want` ("the shortest run that names an existing
path"). This replaced r1's "try every run". With the checkout at `…/My Projects/…` and a sibling `…/My` present,
`argv_runs_script("python3 …/My Projects/scripts/explainer-serve.py")` returns False (reproduced). It fails closed, and
the relative-argv form that the delivery doc uses still matches. `os.path.isfile` would narrow this.

The other shapes I tried were all handled correctly:

- **Matched:** `-E -s -I`, `-Wd`, `-X dev`, `-X frozen_modules=off`, `-u --`, `-i -S -q -P`.
- **Refused:** `-W x -c y`, `<SF>.bak`, `<SF>x`, `--help`, `uv run python3`, `/usr/bin/env python3` as argv text, and
  `python3-dbg`.

`/usr/bin/env python3 <script>` is never seen by ps in that form, because env execs python, and a real start through
the shebang matched.

### Not findings (probed, held)

- **Y1, foreign program in argv:** an argv[0] forged with `exec -a` can still pass, but it also needs this root's
  pidfile to name the pid and that pid to hold the port. That is the same-user impersonation limit already documented
  in r1 X10.
- **Pid reuse:** a reused pid that is another root's **older** server on the same port would pass the binding, because
  an older server's argv does not carry its root. That needs a stale legacy pid reused by exactly that server, so I
  judge it negligible. It is pre-existing (r1).
- **Y3/Y4, records:** only the child writes the records, after its bind, through mkstemp and `os.replace`. The loser of
  a race writes nothing and leaves the winner's record byte-identical. `forget_own` touches only a record that carries
  this start's token. No `*.tmp` was left on any path at HEAD. A child that hangs is SIGTERMed after 2 s and SIGKILLed
  after a further 2 s by `reap_child`. A child killed in the middle of a write can leave a hidden `*.tmp`, which is
  harmless.

## Thrashing assessment

This round has **four fix-induced findings in `explainer-serve`**: F2, F3 and F4 are MINOR and F5 is a NIT. Round 2's
four findings were all fix-induced too. That makes two consecutive rounds of fix-induced findings in one component,
which is the literal Phase 6 arming condition. The severity is falling, though: round 2 had a BLOCKER and three MAJORs,
and this round's fix-induced findings are all MINOR or NIT.

The one MAJOR this round, F1, is **not** fix-induced. It comes from r1's exact-path rule, and it calls for a decision
rather than another fold. This is round 3, so from round 4 any finding that is not a BLOCKER is FILED.

VERDICT: NOT CONVERGED
