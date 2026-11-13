Reviewed head: 2af17adfc4bee453f12918a80b018a9e913cd1e7

> **For the r3 fold of `suite-cost-a` (PR #537, backlog #406, backlog #231).** This review was triggered by
> **THRASHING** in one component, `goal-tree-sibling-cache` (`_sibling` and its helpers in `scripts/goal-tree.py`).
> r2's R2-F1 and R2-F2 were caused by r1's fold, and r3's R3-F1, R3-F3 and R3-F4 by r2's fold
> (`docs/dev-process.md` → *Phases*).
>
> **Verdict: REDESIGN. A redesign removes the class, and measured, it costs nothing.** Every finding from r1 to r3
> needed a caller that does something no real caller does: rewrite a sibling (or a file it reads) inside one
> process and ask again, re-enter `_sibling` from a sibling's import, or import from two threads or two instances.
> The cache was built to stay correct for those callers, and each fold added machinery for that (an audit hook, a
> stack of read-lists, a lock, a process-wide bytecode-settings swap). Each piece of machinery was what the next
> round found wrong. The only caller that needs the cache is the self-test. So the cache now lives ONLY inside an
> explicit sweep that the self-test opens. Every other caller gets a fresh import on every call, as on master. The
> suite stays about as fast as round 1 (1.95 to 2.34 s against master's 13.57 to 21.89 s, interleaved). **BLOCKERs:
> none.**

# Phase 6 architecture review (narrow, triggered by thrashing): the goal-tree sibling cache

Scope: `_sibling`, `_SIBLING_MEMO`, `_SIBLING_LOCK`, `_SIBLING_STACK`, `_note_open` and `_sibling_import` in
`scripts/goal-tree.py` at the reviewed head, their cases in `_self_test_body`, and the twelve backlog #406 entries in
`scripts/mutations/goal-tree.json`.

Read first:
- `docs/reviews/codex/suite-cost-a-r1-codex.md`, `docs/reviews/claude/suite-cost-a-r1-claude.md`,
  `docs/reviews/codex/suite-cost-a-r2-codex.md`, `docs/reviews/claude/suite-cost-a-r3-claude.md`;
- the r1 and r2 coordinator docs under `docs/reviews/coordinator/`;
- the `suite-cost-a` row of `docs/reviews/decision-scheme/decision-log.jsonl`;
- `docs/review-method.md` → *Can a redesign remove it?* and *The arming condition — full account*.

No ADR covers how a script imports its siblings, so none is re-litigated. Nothing under `.claude/plans/` was read.

## 1. Thrashing or prose floor?

**Thrashing, and this time a redesign removes it.** Every finding carried a repro or a surviving mutation, so none
is a prose floor. Each is classified below by what had to be true to reproduce it, and by whether it was a real
corruption (the cache served something other than a fresh import would) or a test gap (the code was correct and
no case pinned it).

| Round | Finding | Needed to reproduce | Kind | fix_induced |
|---|---|---|---|---|
| r1 | Codex F1: a same-size rewrite with the mtime put back is served stale | One process imports a sibling, rewrites it in place at the same size, restores its mtime, and asks again | Corruption, constructed caller | no |
| r1 | Codex F2: a change only in a file the sibling loads (`check-docs.py` for `gen-backlog-page`) is served stale | One process imports a sibling, rewrites its dependency, and asks again | Corruption, constructed caller | no |
| r1 | Claude F1: mtime and size are each untested on their own | Two one-part mutants of the stat key | Test gap | no |
| r1 | Claude F2: a miss can still run a stale `.pyc` (Python's check is mtime in seconds plus size) | A same-size rewrite in the same second, with a `.pyc` present | Corruption, older than the PR | no |
| r2 | Codex F1: a sibling that calls `_sibling` during its own import loses its later reads from its key | A sibling that re-enters `_sibling`, then reads a data file, then that file changes in-process | Corruption, constructed caller | yes (r1's shared read-list) |
| r2 | Codex F2: two threads' imports lose a read and leave `dont_write_bytecode`/`pycache_prefix` changed | Two threads importing at once, ordered by events | Corruption plus a leaked process setting, constructed caller | yes (r1's shared read-list and settings swap) |
| r3 | F1: the stack pop is not pinned to `finally` | A mutation; its effect needs an import that raises, then a stale `.pyc` | Test gap (code correct) | yes (r2's stack) |
| r3 | F2: two goal-tree INSTANCES in two threads leak the bytecode settings | Two module instances importing in two threads | Leaked process setting (a slowdown, not stale code), constructed caller | no |
| r3 | F3: a sibling whose import starts a thread that calls `_sibling` and joins it deadlocks | A sibling that does that at import | Hang, constructed caller | yes (r2's lock) |
| r3 | F4: the threads case kills the no-lock mutant only if T2 starts within 0.2 s | A slow scheduler | Test gap (timing) | yes (r2's case) |
| r3 | F5: a failing outermost import's settings restore is not pinned to `finally` | A mutation | Test gap (code correct) | no |

**What every row shares.** None reproduces with a real caller. Codex said so in r2 ("I found no current production
caller exercising these overlaps"), and r3 confirmed it: no real sibling re-enters `_sibling`, starts a thread, lists
a directory or runs a subprocess at import, and the only process that imports goal-tree in-process
(`session-state.py:_goal_tree()`) makes a new instance per call. All the corruptions need a caller that **changes the
files while it is still asking** or **overlaps imports**. The cache was being made correct for callers that do not
exist, and each round's machinery for that was the next round's finding. That is the thrashing mechanism, and it
is a property of the design's REQUIREMENT ("be a correct cache for any in-process caller"), not of any one line.

**Can a redesign remove it?** Yes. If the cache exists only where nothing changes the files and nothing overlaps,
it needs none of the machinery, and every row above either cannot occur or no longer has code to occur in.

## 2. The designs considered, measured

All timings are the goal-tree suite (`--self-test`) under harness conditions: a fresh `git archive` stage with no
`__pycache__`, `PYTHONDONTWRITEBYTECODE=1`, the four variants interleaved within each run, `__pycache__` removed
between runs. MEASURED on 2026-11-08, load average (5 min) falling from 48 to 20 across the runs:

| Run | origin/master `bd1284b4` | reviewed head `2af17adf` | **S: memo only in a sweep** | N: no memo, compile from source only |
|---|---|---|---|---|
| 1 | 21.89 s (428/428) | 2.94 s (437/437) | **2.34 s** (437/437) | 21.32 s |
| 2 | 17.49 s | 2.10 s | **1.95 s** | 14.46 s |
| 3 | 13.57 s | 2.38 s | **2.25 s** | 14.93 s |

(S here is the fold with 437 cases; the final tree adds one case, a single in-memory import, see §4. N is S with
the sweep switched off, so its two sweep cases fail: 435/437. The brief's "about 36 s" for master was measured at a
higher load; under the same load the ratio is what matters, and S keeps round 1's.)

- **N — drop the cache, keep only "never read bytecode".** It gives NONE of the speed: 14.46 to 21.32 s, the same
  as master. Under harness conditions there is no `.pyc` to skip anyway, so the cost was always re-executing the
  module, not loading it. Rejected.
- **D — key on the sibling's bytes plus a fixed declared list of the files it reads, failing closed when the list
  is wrong.** Its lookup does what the head's does (reads a few files and compares bytes), so its speed is the
  head's: ESTIMATED from the head's column, not built. It was not built because of what "failing closed when the
  list is wrong" needs: something must OBSERVE what the import read in order to compare it with the list. That is
  the audit hook again, with its re-entrance and thread questions (r2's findings), or a self-test case that imports
  each real sibling under a hook and checks its reads are declared (which moves the observation into the suite but
  still leaves an in-process cache whose correctness depends on that list). D keeps the requirement that thrashed.
  Rejected.
- **S — the memo exists only inside `_sibling_sweep()`, and only the self-test opens one.** Inside a sweep a sibling
  is imported once per path. Outside, every call is a fresh import, exactly as on master. 1.95 to 2.34 s, as fast as
  the head. **Chosen.**

**What S removes.** The audit hook (installed for the life of every process that loads goal-tree, which Codex r2
noted costs a callback on every `open`), the read-list stack, the lock, and the save and restore of
`sys.dont_write_bytecode` and `sys.pycache_prefix`. Replacing the production code alone was 87 lines removed and 43 added
(`git diff --stat` at that step, docstrings included). Nothing process-wide is changed by an import any more.

**What S keeps from r1.** The sibling's own source is compiled from the bytes just read
(`compile(..., dont_inherit=True)` and `exec`, which is what `SourceFileLoader.exec_module` does minus the
`.pyc`), so Claude R1-F2 stays fixed for the sibling itself, with no process setting touched. `dont_inherit=True`
matters: without it the sibling compiles under goal-tree's own `from __future__ import annotations`, and a case now
pins that.

## 3. The bound, and why it holds

**In scope:**
- Every caller outside a sweep. Each call is a fresh import of the bytes on disk at that moment, as on master, so r1
  Codex F1 and F2 cannot occur there. A re-entrant import, two threads and two instances share nothing that one can
  corrupt for another, so r2 F1, r2 F2 and r3 F2 cannot occur. There is no lock, so r3 F3 cannot occur.
- The self-test's sweep. It reads the tree as it stood when the sweep started, as a process's own `import` does.
  Measured at this fold: no case in the suite writes to a real sibling or patches a sibling module's attribute
  (`grep` over `scripts/goal-tree.py` for writes under `SCRIPTS` and for assignments to `gb.`, `gd.`, `wl.`, `_wl.`
  and `_SS.`: none). The mutation harness gives each mutant its own process over a tree already written, so a
  mutant never sees a module imported from another mutant's tree.

**Out of scope (stated, not defended):**
- A sweep in which a sibling, or a file one reads at import, is rewritten. It is served the first import. This is
  the reason the cache lives only in a sweep. Today only the self-test opens one.
- A module that the sibling ITSELF loads by path (`gen-backlog-page` loading `check-docs.py`). It is loaded by
  Python's own rules, `.pyc` included, as on master. The head compiled those from source too, by changing
  `pycache_prefix` for the whole process; that process-wide change is what r2 F2 and r3 F2 were about, and no
  current case or caller depends on it.
- Two threads in one sweep may import the same path twice. Both modules are correct imports of the same bytes, and
  the memo keeps one. There is no lock to take, so nothing can deadlock.

## 4. What the r3 fold does

The fold replaces the cache with S, and the cases and mutations follow it.

- **Cases (437 at the head → 438).** Nine backlog #406 cases at the head are replaced by ten. Outside a sweep,
  observed by `_sibling_outside_probe()` BEFORE the self-test's sweep starts (so it sees the module's own default,
  not a forced one): the same sibling twice is two imports; a sibling rewritten in-process is imported afresh; a
  same-size rewrite with the mtime put back and an old `.pyc` planted is the new source (r1 Codex F1, Claude F2); a
  change only in a file the sibling loads is seen (r1 Codex F2). Inside the sweep: the same sibling twice is one
  import; one name in two directories is two imports; a sibling compiles as itself, not under goal-tree's
  `__future__` flags; a nested sweep shares the outer memo; a sweep that RAISES leaves no memo on (R3-F1 and R3-F5's
  lesson, applied to the one restore that remains); SCRIPTS is restored.
- **Mutations (337 at the head → 336; master 325).** The twelve backlog #406 entries named code that no longer
  exists, and are replaced by eleven on the new code. Each is hand-checked by the harness's own rule (§5).
- **R3-F1, R3-F4, R3-F5:** the code they were about is gone (the stack, the threads case, the settings restore). Their
  lesson, that a restore in `finally` needs a case that raises, is applied to `_sibling_sweep`'s restore, with two
  mutations (restore moved out of `finally`; restore never run).
- **R3-F2:** dissolved. No import changes a process-wide setting, so two instances cannot leak one. No backlog row.
- **R3-F3:** dissolved. There is no lock.

## 5. Stop condition

From r4, findings are FILED unless BLOCKING (`review-method.md` §0 Q4c). In this component:
- A finding that needs a sweep in which files change, or a module the sibling itself loads by path, is out of scope
  under §3 and is recorded as such, not fixed.
- A BLOCKER is a caller OUTSIDE a sweep that is served anything other than a fresh import, or a real (not
  constructed) caller of the self-test whose result is wrong because of the memo.
- If a later round finds a defect caused by THIS fold, that is a fresh count under the arming condition, but the
  design question has an answer now, and the bound above is what a fold is checked against.

## 6. Not written down until now

The cache had no stated customer. Round 1 built it for the suite but described it as a general cache, so every
reviewer correctly attacked it as one, with the hardest in-process caller they could construct, and each fold
accepted that frame. The missing sentence was *"the only caller that needs this is the self-test"*. Once it is
said, the cache can be scoped to that caller, and the requirement that thrashed disappears. It is now stated in
`_sibling`'s docstring and in `_sibling_sweep`'s.
