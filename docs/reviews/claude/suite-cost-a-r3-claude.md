Reviewed head: b614db8528d35444d36479c4de30e873eb6e657e

# Round 3 — `suite-cost-a` (PR #537, backlog #231 / #406) — Claude half (adversarial)

Scope: `git diff origin/master...HEAD`, weighted on `scripts/goal-tree.py`'s sibling cache (`_sibling`,
`_SIBLING_LOCK`, `_SIBLING_STACK`, `_note_open`, `_sibling_import`'s bytecode save/restore), its cases and
mutations. The mandate was to REFUTE the decision-log prediction for `suite-cost-a`. `check-main-drivable.py` and
`check-usage-pace.py` were not re-attacked this round.

Method: each mutation was applied to a fresh `git archive HEAD scripts docs` stage in the scratchpad (no
`__pycache__`, `PYTHONDONTWRITEBYTECODE=1`), the suite was run, and the result was checked by the harness's rule:
rc 1 AND `parse_fail_names` (imported from `scripts/check-plan-code.py`) naming exactly the expected case. The repro
scripts load goal-tree by path from a stage copy. Load average was 56 to 300 throughout.

## What held (measured)

- All four r2 mutations go red on exactly their `expect` case: `del _SIBLING_STACK[:]` → the re-entrant case;
  `_SIBLING_STACK[-1:]` → the inner-failed case; no lock → the threads case (7 of 7 natural runs, 6 of them in
  parallel); never restoring → the threads case.
- Suite at HEAD: 437/437, rc 0.
- **The speedup holds.** With no `__pycache__` and `PYTHONDONTWRITEBYTECODE=1`, interleaved, run twice:
  `origin/master` took 36.75 s and 35.84 s, HEAD took 4.70 s and 3.83 s (load around 56 to 160).
- No stale hit within one goal-tree instance. Tried: an inner HIT under an outer import (the hit check's reads are
  noted in the outer list), an inner FAILED import, a sibling that opens files from a helper thread, and stdlib
  modules a sibling imports for the first time (they are recorded in the key).
- Real siblings' import-time reads: no `os.listdir` or `glob`, and no subprocess. The only non-open read event is
  one fd-based `os.scandir`, which is `shutil.rmtree` of the temporary prefix. The stated bound is not exercised by
  any current sibling.

## Findings

### R3-F1 — Medium — the "pop in `finally`" that r2 relies on has no case; moving it out survives, and the result is a stale `.pyc` served

`scripts/goal-tree.py:263-267` (`_SIBLING_STACK.append(opened)` / `try: exec_module` / `finally: _SIBLING_STACK.pop()`).

Input: the mutation that moves `_SIBLING_STACK.pop()` out of `finally` and into the `try` body, after `exec_module`.

Result: suite rc 0, 437/437. The mutation SURVIVES. Its consequence, constructed in
`scratchpad/stale.py` against the mutant: an import that raises leaves `len(_SIBLING_STACK) == 1` forever. From then
on every import has `outermost == False`, so none of them redirects `pycache_prefix`. A sibling with a same-size
rewrite, its mtime put back and an old `.pyc` planted, is then served the old code. Measured: `source says V = 2;
served V = 1` on the mutant, and `V = 2` with the stack at 0 at HEAD. Every open in the process is also appended to
the leaked list from then on.

The coordinator's r2 doc says "The pop is in `finally`" as part of the fold, but no case makes that line
load-bearing. The inner-failed case (case 2) does not catch it: the outer import's own `pop` removes the leaked
inner list, which leaves the outer list in place. Nothing afterwards checks that the stack is empty or that a stale
`.pyc` is refused. The `.pyc` cases run BEFORE case 2.

Fix: after case 2 (or after any import that raises), assert `_SIBLING_STACK == []`, or repeat the stale-`.pyc` check
after a failed import. Then add the mutation above, expecting that case.

fix_induced: **yes**. `_SIBLING_STACK` and its pop are r2's fold, and the gap is in r2's cases. The code at HEAD is
correct.

### R3-F2 — Low — two goal-tree INSTANCES in two threads still leak the bytecode settings (the literal prediction is refuted)

`scripts/goal-tree.py:219-221, 258-269`. The lock and stack are module globals, so they belong to each instance.
`sys.dont_write_bytecode` and `sys.pycache_prefix` belong to the whole process. `session-state.py:_goal_tree()`
(line 382) makes a NEW goal-tree instance on every call.

Input (`scratchpad/xinst.py`): load goal-tree twice (X, Y). T1 calls `X._sibling("sa")`, which waits for T2 to
enter. T2 calls `Y._sibling("sb")`, which waits for T1 to finish.

Result: before `(False, None)`, after `(True, '/var/folders/.../tmpc7op0re6')`, and that prefix directory no longer
exists. This is Codex R2-F2's interleaving, moved from two threads to two instances. Keys stay sound, because each
instance's hook notes the other's opens as extra entries, so a key only gains entries. The leak is a slowdown, not
stale code.

No current process has two instances importing in two threads. `explainer-serve.py`'s threaded server runs
goal-tree as a subprocess. The prediction says no concurrent import leaves the settings changed, and with this
input one does.

Fix: either a docstring bound ("one instance per process; a second instance's imports are not serialised against
the first"), or keep the lock, stack and depth on a process-wide object (for example under a fixed `sys` attribute
or in a `sys.modules` entry) that every instance shares.

fix_induced: **no**. r1 leaked the settings even with one instance. r2 narrowed the leak to the cross-instance case
and did not create it.

### R3-F3 — Low — a sibling whose import starts a thread that calls `_sibling` and joins it deadlocks

`scripts/goal-tree.py:209` (`with _SIBLING_LOCK:`, held across `exec_module`).

Input (`scratchpad/dl.py`): `outer.py` starts a thread that calls `_sibling('inner')` and joins it.

Result: the worker blocks on the RLock, which the importing thread holds. With `join(3)` the import yields
`'DEADLOCK: worker blocked on _SIBLING_LOCK'`. An unbounded `join()` hangs forever. Before r2 there was no lock and
this input completed.

No current sibling starts threads at import. Python's own import lock has the same hazard, so this is inherent to
serialising imports. It should be stated in the docstring's bound rather than designed away.

fix_induced: **yes**, since the lock is r2's. Severity Low, because it has no caller and a docstring line resolves it.

### R3-F4 — Low — the threads case kills the no-lock mutant only if T2 enters within T1's 0.2 s wait

`scripts/goal-tree.py:2477-2478` (`sib-t1`: `g.saw.append(g.ev['t2_in'].wait(0.2))`), mutation "r2 Codex F2: no
lock" in `scripts/mutations/goal-tree.json`.

Input: the no-lock mutant plus a 0.3 s sleep before `_t2.start()`, which simulates T2 being scheduled late.

Result: rc 0, 437/437, so the mutant SURVIVES. Without the lock, a T2 that arrives after T1's 0.2 s wait sees T1 has
already finished: `saw == [False]`, the settings are restored and the key is intact, so it is indistinguishable from
the locked behaviour. Seven natural runs (six in parallel, load around 160) all killed it. So this is a latent
sweep flake on a slow runner, not an observed one. With the lock in place the case cannot false-fail, because T2
cannot enter until T1 has released the lock.

Fix: have `_run` set a `t2_calling` event just before `_sibling(...)`. T1 then waits for `t2_calling` with a long
timeout before its bounded `t2_in` wait. That narrows the window to T2's own import prologue. Alternatively, assert
the mechanism directly: from inside T1's import, a second thread's `_SIBLING_LOCK.acquire(blocking=False)` returns
False.

fix_induced: **yes** (the case was added by r2's fold).

### R3-F5 — Low — a FAILING outermost import's settings restore has no case

`scripts/goal-tree.py:266-270` (`if outermost:` restore inside `finally`).

Input: the mutation that moves the `if outermost:` restore and `rmtree` out of `finally`.

Result: rc 0, 437/437, so the mutation survives. An outermost import that raises would leave
`dont_write_bytecode=True` and `pycache_prefix` pointing at a leaked temporary directory. The code is correct; this
is part of the prediction ("a failing import ... leaves sys.dont_write_bytecode or sys.pycache_prefix different"),
and no case checks it.

Fix: in the case that covers R3-F1, also assert `(sys.dont_write_bytecode, sys.pycache_prefix) == _orig_bytecode`
after a sibling whose top-level import raises.

fix_induced: **no**. r1 already had the restore in `finally` without a case.

## Thrashing note

R3-F1, R3-F3 and R3-F4 are fix-induced: each comes from r2's fold. None of them is a stale hit or a leak in the
shipped code's single-instance path. F1 and F4 are case and mutation gaps around correct code, and F3 is a hazard
with no caller that a docstring line resolves. The r2 coordinator doc says one more fix-caused round would be
THRASHING, so by that rule this round arms Phase 6 for `goal-tree-sibling-cache`. The coordinator should weigh
that the fix-induced findings are test gaps (F1, F4) and a bound to document (F3), not a third corruption.

VERDICT: NOT CONVERGED
