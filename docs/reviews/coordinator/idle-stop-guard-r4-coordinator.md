# Round 4 — `idle-stop-guard` — coordinator — ⟳ NOT CONVERGED (Codex half) — one BLOCKER, fixed by removing signal (b)

Codex (`docs/reviews/codex/idle-stop-guard-r4-codex.md`) reviewed `11178c55`: 1 BLOCKER, NOT CONVERGED. Self-test
78/78 quoted. The removal audit found no remaining reader of the transcript or `.claude/paused`.

REVIEW GAP: claude — alternation (rounds 2+ run one half; Claude reviewed round 3).

```yaml
round: 4
fixes_nontrivial: true
subject: idle-stop-guard
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XB1, severity: Blocking, aim: deliverable, fix_induced: false, component: worktree-signal, disposition: fixed}
```

## Is XB1 a BLOCKER by this round's own definition?

Yes. The r4 brief defined a BLOCKER as an announcement-only first stop that exits 0 with nothing running and no
forged signal. Codex's input: a builder that FINISHED 120 s ago (its final write is real, not forged), no live
background task, CI idle, last message "Now starting backlog #657." → `main()` exit 0. That is the most common
shape of the incident the guard exists for: a completion notification arrives, the orchestrator announces the next
item, and stops. Signal (b) reads evidence that work HAPPENED as evidence that it IS HAPPENING — the same defect
r1 XM1/CM2 narrowed and could not remove, because recency cannot tell "still writing" from "just finished".

## Disposition: REMOVE signal (b), do not narrow it

- **(a) already sees a builder.** Measured 2026-11-16 05:07 (docstring, r1 CM3): a background Agent is
  `{"type": "subagent", "status": "running"}` in `background_tasks` while it runs and leaves the list when it
  finishes. Every builder this orchestrator launches is its own background task, so (b) only ever adds a builder
  that is NOT running — XB1 — or one another session owns, which is no reason for this session to stop idle.
- **Narrowing fails.** A shorter window keeps the class (a builder that finished 30 s ago); a longer settle hides
  real builders. No window separates "last write" from "finished".
- **It dissolves backlog #664** (one `touch` in a builder worktree allows a stop for ten minutes): the forgeable
  signal is the one removed. Its row is closed as dissolved.
- ⚠ **Bound kept in the docstring:** the interactive `in_process_teammate` entry is still not captured; if it stays
  `running` while idle, (a) over-allows. That over-allows; it never blocks a real builder.

Same principle as Phase 6 option D: an ALLOW reads state that says work IS running, from the harness, not a proxy.
This is round 4, so after the fold the next round files every non-BLOCKER.

## Fold

**Red before the removal.** Two cases were added FIRST, on `db0fafcb`'s code: Codex's XB1 fixture through
`main()` (a builder worktree whose last file was written 120 s ago, `.git` aged 86,400 s, `background_tasks: []`,
CI `[]`, no usage cache, "Now starting backlog #657.") and an identity case over a literal list of four worktree
states — a file written 5 s ago, 120 s ago, a `touch`ed file, an unlistable worktrees dir — each compared with the
same stop with no worktrees dir at all. `--self-test`: **78/80, 2 red** (XB1 exited 0; the identity case diverged on
all 4 of 4 rows). After the removal both are green.

**Removed from `scripts/check-idle-stop.py`:** `moved_worktrees`, `_recent`, `window_text`, the constants
`IDLE_WINDOW_S`, `SETTLE_S`, `WALK_BUDGET_S`, `SKIP_DIRS`, the `main`/`own` parameters of `decide`, the
`_pace.main_checkout` call in `main()` (`gh` now runs in the hook's own checkout), and the unread-(b) reason.
`WORKTREES` stays as a self-test constant. (a) and (c) and their labels are unchanged. The docstring says why (b)
is gone and keeps the `in_process_teammate` bound; the launcher's header comment no longer names it.

**Retired cases (20):** ⭐ replay 02:24 + (b) a builder worktree changed 2 min ago → ALLOW · (b) the window is
IDLE_WINDOW_S · (b) moved_worktrees at two windows · (b) moved_worktrees names only the moving builder · (b)
moved_worktrees is relative to its clock · (b) no `.claude/worktrees` at all is no builder · ⭐ (b) a fresh `git
worktree add` is not running work · (b) a file counts only SETTLE_S after the worktree's `.git` · (b) a fresh file
under `__pycache__` or inside a `.git` directory never counts · (b) a directory with no `.git` is not a builder
worktree · ⭐ (b) the orchestrator's own checkout never counts · (b) decide passes `own` on · ⭐ (b) the walk has a
wall budget · (b) the deadline is checked per DIRECTORY too · ⭐ (b) the walk deadline is checked per FILE (r2 XM5) ·
(b) a worktrees path that cannot be listed is None · no main checkout → BLOCK, naming (b) · an unlistable worktrees
directory → BLOCK, naming (b) · ⭐ main: the session's OWN worktree never counts as a builder · window_text at two
inputs.
**Changed, not weakened:** "(c) gh is not called when (a) or (b) already found work" → "(c) gh is not called when
(a) already found work" (its (b) half has no subject); "the block says what it saw" drops "10 min" and a new case
asserts the block names no worktree and no minutes; the 02:24 replay's name drops "worktrees quiet 2 h".
**Added (3):** ⭐ r4 XB1 (Codex) · ⭐ r4 XB1 identity · the block names no worktree signal. Self-test **61/61**.

**Retired mutations (26):** (b) a moving builder does not allow · (b) skipped directories are walked · (b) the
window doubles · (b) the window parameter is ignored · (b) one recent worktree marks every worktree · (b) no
worktrees dir is read as unread · (b) no main checkout is read as no builders · (b) an unlistable worktrees dir is
read as no builders · (b) a checkout counts as building: the settle margin is dropped · (b) the settle margin halves ·
(b) the settle margin doubles · (b) `__pycache__` is walked · (b) a `.git` directory is walked · (b) a directory
with no `.git` is a worktree · (b) the session's own checkout counts · (b) `own` is compared unresolved · (b)
decide does not pass `own` · (b) the walk budget is ignored · (b) a walk out of budget reads as nothing moved · (b)
the budget parameter is ignored · (b) an unread worktree signal is not named · the block message hard-codes 1 min ·
window_text rounds to whole minutes · main does not pass the session's own checkout · the per-FILE walk deadline
is dropped (r2 XM5) · the file loop ignores the injected lstat.
**Re-anchored (4, same behaviour, new anchor because the old line is gone or now shared):** main: the real gh is
never called · main opens the transcript again, blocking · a rejected card followed by an announcement excuses
the stop · a pause marker in the checkout excuses the stop again (it read `decide`'s removed `main`; it now
reads `root` in `main()`). One renamed: (c) gh is called even when (a) found work.
**Added (1, binding):** "a builder-worktree recency ALLOW is re-added (r4 XB1)" — `main()` returns 0 when any
file under `.claude/worktrees` changed in 600 s; killed by, and attributed to, ⭐ r4 XB1 identity.
`check-plan-code.py --mutate . --only scripts/check-idle-stop.py` on a COPY of the tree (one call, 2 m 25 s):
**61 mutations, 61 killed, 61 attributed, 0 survivors.** `expected_mutations.py` 86 → 61.
`check-fixture-variation.py`'s entry re-derived by `analyse()`: − `decide.main`, `decide.own`, every
`moved_worktrees.*`, `window_text.s`; `main.root`'s exemption reason rewritten (it now only locates `gh`'s cwd).

**Latency, re-measured** through `.claude/hooks/check-idle-stop.sh` with a `gh` that sleeps 30 s, empty HOME,
`background_tasks: []` (the worst case: (a) empty, so `gh` is asked): **3.23 s, 3.20 s, 3.16 s**, exit 2 naming (c)
TimeoutExpired. The walk's cost (measured ~0.2 s, budget 1 s) is gone; the bound is `GH_TIMEOUT_S` plus start-up.

**Backlog:** row 663's signal list now reads (a) and (c), with (b)'s removal stated; row 664 is ✅ CLOSED as
DISSOLVED BY REMOVAL, citing the identity case as its falsifier. The last dashboard entry no longer names a worktree
signal.
