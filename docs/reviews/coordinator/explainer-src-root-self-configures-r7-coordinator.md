# Round 7 — `explainer-src-root-self-configures` (PR #295) — coordinator

```yaml
round: 7
fixes_nontrivial: true
subject: explainer-src-root-self-configures
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: true, component: start-restart, disposition: fixed}
  - {id: H2, severity: High, aim: deliverable, fix_induced: true, component: start-restart, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: start-restart, disposition: fixed}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: false, component: respawn-logging, disposition: filed}
  - {id: M3, severity: Medium, aim: deliverable, fix_induced: false, component: start-restart, disposition: filed}
  - {id: L1, severity: Low, aim: instrument, fix_induced: true, component: start-restart, disposition: fixed}
  - {id: L2, severity: Low, aim: deliverable, fix_induced: true, component: start-restart, disposition: fixed}
  - {id: L3, severity: Low, aim: deliverable, fix_induced: false, component: restart-ui, disposition: filed}
halves:
  codex: ran
  claude: ran
```

## ⛔ Q5 FIRST — THE ARMING QUESTION, ANSWERED BEFORE ANYTHING ELSE

**Three consecutive fixes in `start-restart` each introduced the next defect:**

| fix | what it introduced | found by |
|---|---|---|
| `024185f9` the lock | held forever on a broken pipe — a permanent refusal traded for a recoverable race | the coordinator, reading its own r7 brief |
| `a5b0d95b` the pipe | the race narrowed, not closed | Codex r7 |
| the pipe, again | `K` sent before `detach_streams` — **strictly worse than the code it replaced** | Claude r7 |

⚠ **BY THE LETTER IT DOES NOT FIRE, AND SAYING ONLY THAT WOULD BE A DODGE.** The condition is *two
consecutive **rounds*** carrying fix-induced findings in one component. Round 6's High was **not**
fix-induced — `start()` was byte-identical to master and the defect was original, made reachable by
the branch. So the counter says one round. **In substance this is thrashing**, and the procedure is
explicit that the trigger is thrashing and not a count.

### The test: *can a redesign remove it?* — **Yes, and it has been applied**

The class across H1, H2 and M1 is one sentence: **a signal was emitted before the thing it claimed
was true.** `port_busy` claimed "my child serves" from "a listener exists". `K` claimed "I am
serving" from "I bound". The lock claimed "in flight" for a process that was not going anywhere.

The change is structural rather than another patch:

- every step `K` claims — `setsid`, `detach_streams`, the bind — is inside **one guard** that
  reports `X` on `BaseException`, and the byte is the **last thing** before serving;
- a case asserts the **property**, not the ordering: *between the readiness byte and
  `serve_forever` there is nothing that can fail*. Adding a step after the byte is now refused by a
  test rather than by whoever is reading carefully.

That converts "the code happens to be ordered correctly" into "a wrong ordering is red".

### ⛔ WHAT ARMS IT FOR REAL, COMMITTED TO IN ADVANCE

**If round 8 finds another fix-induced defect in `start-restart`, this branch splits.** The `/src/`
self-configuring root — the bug the branch exists to fix — has taken **no finding since round 4**.
Every High since has come from the restart button, which is a *separate feature* that arrived in the
same branch. Splitting would ship the converged part and park the risky one.

Recorded now, before round 8, so it cannot become a post-hoc rationalisation either way.

## H2 — `K` was sent before the child had finished becoming a server → **FIXED**

`a5b0d95b` sent `K` and then called `detach_streams()`. Reproduced by the coordinator with
`.serve.log` as a directory (`detach_streams` raises `IsADirectoryError`):

```
pre-pipe tree : rc=1, FAIL, pidfile untouched      ← correct
pipe tree     : rc=0, "serving (pid 15650)", pidfile names a DEAD pid, nothing on the port
```

⭐ **A repair that loses a case the original handled is not a repair.**

⚠ **And the guard was green on the corpse.** The case asserted source ORDER — the pipe exists, the
pidfile follows the verdict — both still true on the broken tree. Replaced with the property above;
verified by re-inserting the defect (139/140, that case red).

## H1 — the race was narrowed, not closed → **FIXED** (Codex)

`waitpid` + `port_busy` accepts "my child has not died" plus "someone is listening" as proof that
"my child is serving". Two separate CLI invocations are different processes, which an in-process
lock cannot touch. ⚠ **The coordinator's first measurement failed to reproduce it** — 6 trials, 0
corpses on both trees — and the honest record is that a widened window (1s pre-bind sleep) made it
3/3 pre-fix and 0/3 fixed. The reviewer reproduced it a different way, with a FIFO barrier and a
foreign listener, and got 2/2 pre-fix and 0/2 fixed.

## M1 — a disconnected reader silently cancelled the restart → **FIXED**

Moving `_send` inside the outer `try` to fix the lock quietly changed what a broken pipe **means**:
the handler skipped `Popen` entirely and logged *"could not spawn the replacement:
BrokenPipeError"* — a cause that never happened, about a spawn never attempted — while the docstring
three lines up promised *"the restart still proceeds"*. The reply has its own `try` again.

## L1, L2 → **FIXED**

The `X` message named a cause (*"could not bind — something else is on the port"*) when the guard
now covers `setsid` and `detach_streams` too; it names the **observation** and says only the child's
own output can identify the step — the third time this branch has made that same correction. And an
empty verdict is split into *died without reporting* (EOF) versus *never reported back* (still
running), because they send a reader to different places.

## M2, M3, L3 → **FILED**

`respawn()`'s docstring promises a trace that is written in 1 of 4 branches; `start()` abandons a
child it could not account for, which can bind late and become unstoppable (**pre-existing** —
identical on the r6 tree); and a `409` renders as *"restart FAILED"* for a restart that is in flight
and will likely succeed. None is contained-and-mechanical.

## Q4 — another round owed?

**Yes.** Two Highs this round, and the fixes are code no round has seen.
