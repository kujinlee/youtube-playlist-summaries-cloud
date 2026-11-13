Reviewed head: 9c2078bd30f11cbe92d283b0a21bc2c87ddc8f70

# flakes-483-427 — round 1 — Claude half

Reviewed range: `origin/master...origin/build-flakes` (head `9c2078bd`, PR #486).

Method: I read the whole script diff (`scripts/backfill-work-lines.py`, `scripts/check-main-drivable.py`) and the
memo factory `_memo_by_node` (`scripts/check-main-drivable.py:314-359`), `case()` (`:2575`), and the harness's
attribution rule (`scripts/check-plan-code.py`, after `run_suite`: caught = rc 1 AND every `expect` names a
`[FAIL]` case). I worked in a detached worktree of `origin/build-flakes`. I applied mutations ONLY to scratch copies
of `scripts/`, never to the worktree. No git writes, no Postgres. Everything marked EXECUTED was run (macOS,
system `python3`). Linux was NOT run and is labelled UNVERIFIED.

Mandate: REFUTE. Find a mutant or input where the new early STOPPED return, or the `samestat` comparison, lets a
real defect pass.

---

## What I ran (EXECUTED)

| Run | Result |
|---|---|
| `backfill-work-lines.py --self-test` (branch) | 268/268, rc 0, 0.8 s |
| `check-main-drivable.py --self-test` (branch) | 455/455, rc 0, 10 s |
| both suites from `origin/master` | 455/455 and 268/268. The case count is unchanged, and `case(` occurrences are 484 on both sides, so no case was removed |
| every manifest mutant whose anchor lies inside `_memo_by_node` or `case()` (13, found by anchor POSITION, not by keyword), plus the deadline one, each once | all rc 1, every named case red. STOPPED fires for exactly the two `(None, out)` entries and for nothing else, including the type-key, non-node-arg, no-reuse, case-insensitive, no-eviction, insertion-order, second-entry and `>=` mutants |
| the `(None, out)` mutant, both manifest entries, 40× each | 40/40 rc 1, STOPPED, named case red, 2 FAILs every time |
| backfill F5 mutant (`os.replace` → `p.write_text(...); tmp.unlink()`), 20× | 20/20 F5 red, `got (False, [])` (plus the mtime case) |

## The questions in the brief

**Can F5 pass when the file was written in place?** No. `os.path.samestat` compares `st_ino` AND `st_dev`
(CPython `genericpath.samestat`). Because the held `O_RDONLY` descriptor keeps the old inode allocated, a
replacement cannot be handed that inode's number. An in-place write keeps the same inode, so `samestat` is True,
`_replaced` is False, and the case is red. EXECUTED 20/20 above. The one shape it still accepts is unlink plus a
fresh create at the same path with no temp file. The old `st_ino !=` assertion accepted that too, so the test is
no weaker.

**Can the STOP hide a different defect?** It returns 1, so it can never turn the suite green. It is reached only
when the fresh-memo entry case is red, and that case reads nothing but `_memo_by_node`, `weakref`, `gc` and
`ast.parse`. Of the 13 mutants inside `_memo_by_node`, only `(None, out)` trips it (EXECUTED). A mutant elsewhere
cannot make a fresh `_memo_by_node(lambda t: len(t.body))` drop its arguments. So the stop cannot short-circuit a
named case for any other manifest entry. That was the attribution risk, and it is closed.

**Do both manifest entries still bind and attribute?** Yes. Each anchor matches once, and each named case is red
40/40. Both named cases now run BEFORE the stop, so attribution no longer depends on the suite reaching line ~4590,
which was the CI failure in run 41194535294.

**Is any test weaker?** The entry case moved from `note_globals_imports.memo` to a fresh memo. I looked for a
per-helper defect that the old form caught and the new one misses. The only one is a helper losing its
`@_memo_by_node`. Under the OLD form that crashed the suite on `.memo` rather than reddening a case, and the
BOUNDED case (`:4628`) still reads `note_globals_imports.memo`. So nothing is lost. The BOUNDED case used to
inherit a full memo from the 256-tree case just before it. It now builds its own 2×64 churn, and the no-eviction
and insertion-order mutants are still red (EXECUTED).

---

## L1 — Low — no case falsifies the STOP

**Where:** `scripts/check-main-drivable.py:2648` (`if fail > _fail_before:`).

**Scenario:** the mutant `if fail > _fail_before:` → `if False:` survives. On correct code the stop never fires,
and no case observes it. With the stop gone, the `(None, out)` mutant goes back to running the whole suite on
dead-tree answers: allocator-dependent FAIL sets, the #427 noise. Attribution still holds, because the two named
cases now run first. So no defect passes. What is unguarded is the flake-suppression itself. A cheap guard would
be a subprocess case that runs the suite under the `(None, out)` substitution and asserts `STOPPED` and exactly 2
FAILs. That is probably not worth it. File or drop at your discretion.

## L2 — Low — cosmetic

`scripts/check-main-drivable.py:4597`: `_two =ast.parse(` is missing the space after `=`. It was introduced by
this diff.

## L3 — Low — descriptor not closed on a raise

`scripts/backfill-work-lines.py:2780-2783`: if `run(...)` raises, `os.close(_old_fd)` is skipped. That leaks one
read-only fd inside a temp directory, so the effect is nil. It is noted for completeness, and `try/finally` would
silence it.

## Residual — UNVERIFIED on Linux

The 256-tree case ("a memoised helper answers for THIS tree") still goes red under `(None, out)` only through
address reuse. It ran 40/40 red on macOS, but I did not measure Linux 3.12. If it were ever green there, that
mutant's FIRST manifest entry would fail attribution. The direct entry case (the second entry) does not depend on
the allocator. Worth one look at the CI sweep output for this PR.

---

## Verdict

**CONVERGED.** No BLOCKER, High or Medium. Three Lows (L1–L3) and one UNVERIFIED residual.

VERDICT: CONVERGED
