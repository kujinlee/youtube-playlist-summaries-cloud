# Architecture review (Phase 6, narrow): `explainer-port-631`, the server-identity rules in `explainer-serve.py`

Subject: `scripts/explainer-serve.py` at `ba45518b` (branch `explainer-port-631`, draft PR #651, backlog #631): the
identity rules at `:1344–1669` and their callers `start` (`:2640`), `stop` (`:2730`), `status` (`:2757`).
Read: `CONTEXT.md` and `docs/adr/` (both silent on server identity, so no ADR is touched), backlog row 631, the three
coordinator round documents, the r2 Codex and r3 Claude reviews, the precedent
`architecture-review-2026-11-27-s3-priority-detection.md`.
Every claim below was read at the cited line or run by me, 2026-11-27 12:03–12:06, on macOS, on ephemeral ports with
temp roots in the session scratchpad. Port 7391 was observed with `lsof` and `ps` only: no connection, no signal.

## Arming evidence

| Round | Findings | Caused by the previous fold? |
|---|---|---|
| r1 both halves, X1–X10 | identity is claimed, never bound | no (the build) |
| r2 Codex, Y1–Y4 | argv position, legacy pidfile port, record-write order | yes, all four, the r1 fold `9b42334e` |
| r3 Claude, Z2–Z5 | legacy pidfile on an idle port, the write-failure message, surviving mutants, a spaced path | yes, all four, the r2 fold `24d0380d` |

Two consecutive fold-induced rounds in one component: THRASHING. Z1 is not fold-induced, but it sits in the same rules.

## 1. Can a redesign remove the class? Yes: identity is the token, and nothing else

**The class.** The branch has two ways to be "ours" (`:1332–1339`). The token path is one equality over a record the
server wrote itself (`classify_listener`, `:1492`). The legacy path (`bound_legacy`, `:1619`) INFERS identity from
what the OS says about a process: `lsof` for the listener, `ps` for argv, `lsof` again for the cwd, then a hand-written
parser of Python's command line (`argv_runs_script`, `:1569`, with three option tables at `:1555–1558`). An inference
over an open input set has an edge on each side, and every round moved one. Sorting the fold-induced findings:

| Finding | Lives in |
|---|---|
| Y1, Z4 (`isfile` mutant, redundant `-c`/`-m` line), Z5 | the argv parser |
| Y2, Z2 | the legacy `.serve.pid` (`pidfile_candidates`, `:164`) |
| Z1 | the exact-path compare (`:1627`, `SCRIPT_FILE`) |
| Y3, Y4, Z3, Z4 (temp cleanup, the concurrent case) | writing the token record |

Six of the nine are in the legacy inference, and so is Z1. The token record's three are r2's Y3/Y4 redesign settling:
its rule (only the child writes, after its bind) held in r3's probes, and what is left is a message and a case.

**The legacy path helps one process on one machine, and not from where the work is done.** Observed: 7391 is held by
pid 59316, started 2026-11-23 17:52 with argv `…/Python scripts/explainer-serve.py` and cwd the MAIN checkout;
`~/explainers/.serve.pid` names it. `argv_runs_script` on that exact argv and cwd returns **False** with this
worktree's `SCRIPT_FILE` and True only with the main checkout's (pure call, run). `git worktree list` shows 94
checkouts, so the owner's server is "ours" from 1 of 94. That is Z1, and it is the only real legacy server there is.

**For a stranger the legacy path can only be wrong.** A fresh install never had the old code, so no legitimate
legacy server exists. `listener_verdict` (`:1653`) still runs `bound_legacy` on every listener that gives no token,
so for a stranger its true positives are zero and every "legacy" verdict is a false one that licenses a SIGTERM.
It also needs `lsof`, which a minimal Linux image does not ship (r2 Codex noted the same).

**Token identity is already checkout-independent** (run): a server started from a sibling copy of `scripts/` was
`yes (ours)`, `already serving`, and stopped (rc 0 each) from this worktree's copy, same root and port. The record
lives in the root, and `classify_listener` never reads `SCRIPT_FILE`.

| Design | Makes impossible | Makes loud | Costs |
|---|---|---|---|
| keep the heuristics, fold Z1–Z5 | nothing new | Z2, Z5 | a fourth fold in the argv/lsof rules, at the round cap, so its findings are FILED and ship in a path that sends signals. Z1 stays (message only), or is fixed by accepting any copy, which loosens r1 X2 |
| **token only (recommended)** | a signal or an "ours" decided by `lsof`, `ps`, argv or a pidfile with no token | an older server: exit 3, naming its pid and the command | the owner's server on 7391 is restarted once |

**What the redesign deletes.** Functions: `bound_legacy`, `argv_runs_script`, `_resolve_arg`, `pid_cwd`,
`gives_token`, `pidfile_candidates`, the `_PY_*` tables (87 lines, `:1542–1628`), `LEGACY_NOTE`, `LEGACY_PIDFILE`
and its unlink at `:2691`, and the `"legacy"` verdict at 8 sites. `recorded_pid` becomes `read_pid(pidfile_for(…))`.
Kept, for MESSAGES only: `listening_pids`, `lsof_pids`, `port_holder`, `pid_command`.
Cases: the 6 `argv_runs_script` cases (`:5456–5499`), the `pidfile_candidates` case (`:5433`) and the two
older-server cases (`:5834`, `:5836`). Mutations, RETIRED WITH THEIR SUBJECT: 5 (the legacy binding skips lsof; the
argv compare is a substring; argv[0] need not be an interpreter; the script may be any argument; the legacy pidfile on
the default port only). Against `origin/master` the pin still rises (127 → 139 plus what the fold adds).

**Measured on a prototype** (a scratch copy with `bound_legacy` returning False and `pidfile_candidates` returning
the per-port file only; control: an unpatched scratch copy, 339/343, its 4 failures repo-dependent). The prototype is
336/343: the same 4, plus exactly the three positive legacy cases (`:5433`, `:5834`, `:5836`). Every negative case
stays green, including `:5776`, `:5854` and `:5861`; keep those, they now hold against reintroduction.
Against a real `origin/master` server on an ephemeral port: `start` rc 3, `--status` rc 3, `--stop` "not running"
rc 0, the server alive afterwards. `--stop` on a second, idle port: rc 0 "not running" (HEAD: rc 3, which is Z2).

**What the redesign must write (text and one case; no new predicate).**
- The exit-3 message. Today it says "a program that is NOT explainer-serve" about our own older server (`:1666`).
  Say what was observed: "port P is held by pid N (`<argv>`), which did not answer as this server. It was left
  alone." Then the choices, with a third: "to free the port yourself: `kill N`". Print that command only when `lsof`
  names exactly ONE pid; today `port_holder` picks `min(pids)` (`:1635`), which names one of several arbitrarily.
- `explainer-delivery.md` §4: delete the "older code … IS this server" paragraph. Exit 3 is always put to the user.
- The usage text (`:70–77`) and the comment block at `:1332–1339`: one way to be ours.
- The X5 case inverted: an older server is NOT proven; start 3, status 3, it is alive after `--stop`, and the
  message carries its pid and `kill <pid>`. One mutation on it.

**The owner's cost, concretely.** After the merge, `python3 scripts/explainer-serve.py` exits 3 on this machine from
every checkout until pid 59316 is stopped and the server started again: two commands, once. A stranger never pays it.

## 2. Dispositions under the token-only design

| id | Disposition |
|---|---|
| Z1 | **Fixed by the redesign.** A sibling checkout's CURRENT server on this root is ours, proven by the token (run). A sibling's OLDER server is not proven, from any checkout including its own: exit 3, never signalled, and the message no longer calls it "NOT explainer-serve". r1 X2's "another copy is not ours" is not loosened: no copy is accepted by path at all |
| Z2 | **Moot.** Nothing reads `.serve.pid`; measured rc 0 "not running" on the prototype |
| Z3 | **A fold, text only.** When nothing listens after the wait, the FAIL line (`:2703`) names `<ROOT>/.serve.log`, where the child wrote its reason. §4 stops saying every exit 1 is a lost race: re-run once, and a second exit 1 goes to the user with that line. No `waitpid` branch; a 2 s wait on a dead child is not worth a new path |
| Z4 | `isfile` mutant and the redundant `-c`/`-m` line: **moot** (deleted). Temp cleanup (`:1442`): **a fold**, the Y3 case also asserts no `*.tmp` is left, with a mutation. The concurrent case (`:5999`): **no change to the gate**; its assertion (one server, records match) is true in either order by design, and the losing-start rule is carried deterministically at `:5915`. Say so in its comment |
| Z5 | **Moot** (deleted) |

Earlier rounds: X5 (r1) is REVERSED on purpose, and this review is the record. X2, Y1, Y2 lose their subject.
X1, X3, X4, X6–X10, Y3, Y4 stand unchanged.

## 3. Does this loosen a gate, or need the owner? No gate loosens; one thing is the owner's to know

- **Nothing loosens.** Every changed behaviour refuses more: an older server goes from exit 0 to exit 3, and `--stop`
  goes from signalling it to leaving it. Backlog 631's two "Fails if" clauses are met more strictly. The retired
  mutations and cases name code that no longer exists.
- **The owner's requirement is met as written**: "asking permission rather than stopping current process". The
  script stops nothing it cannot prove, and names the command for the person to run.
- **Not a decision, but owed a notice:** the restart of the owner's server on 7391. The standing permission
  (`docs/memory/may-free-port-7391.md`, owner 2026-11-13) covers stopping and restarting it when work needs the
  PORT; adopting new server code is a neighbouring reason, not that one. Its recipe (`--stop` from the owner's
  checkout) works only while that checkout still has the old code, so do it before the fast-forward, start after,
  and say so in the closing message.
- **Decided here and written down nowhere else:** (a) identity belongs to the ROOT and PORT, never to the script
  file; (b) `--stop` with no record is "not running", exit 0, whatever holds the port, and the holder is `start`'s
  and `--status`'s to report; (c) `lsof` and `ps` may inform a message and never a decision; (d) the same-user
  bound of r1 X10 is unchanged. Put (a)–(c) in the comment block that replaces `:1332–1339`.

## Recommendation

1. Take the token-only design in ONE fold: the deletions above, the message, the inverted X5 case, Z3's text, the
   Z4 temp-file case. Do not fold Z1–Z5 into the heuristics.
2. Review that fold once (round 4, Codex by alternation). It is the round cap: a finding is FILED unless a BLOCKER.
3. Restart the owner's 7391 server around the merge, and tell them.

**FAILS IF:** `grep -cE 'bound_legacy|argv_runs_script|pid_cwd|LEGACY_PIDFILE|"legacy"' scripts/explainer-serve.py`
is not 0; or `listening_pids` or `pid_command` has a caller outside `port_holder`, the two not-ours messages and
the self-test; or `stop` reaches `os.kill` under any verdict but `"ours"`; or a server started from
`origin/master`'s script on an ephemeral port gets anything but exit 3 from `start` and `--status`, is dead after
`--stop`, or the message lacks its pid and `kill <pid>`.
**STOP:** the redesign failed too if round 4 carries a finding in which an OS observation or a record without a
token decides "ours" or a signal, or a BLOCKER in `classify_listener`, `read_identity` or `stop`. Then stop tuning.
The retreat is that the CLI never signals a pid: `--stop` sends the token to the listener and the server exits
itself. That adds an endpoint and loses the stop of a hung server, so it goes to the owner, not into a fold.
