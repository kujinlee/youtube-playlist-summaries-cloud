Reviewed head: 10072913

> **For the r3 fold of `regen-fresh` (PR #536, backlog #408).** This review was triggered by **THRASHING** in one
> component, `regen-runner` (`scripts/regen-pages.py` and its process-group helpers). r2's Blocking and High findings
> were caused by r1's fix, and r3's R3-F1 and R3-F2 by r2's fix (`docs/dev-process.md` → *Phases*).
>
> **Verdict: state the threat model; do not redesign again.** Every data-loss repro after round 1 needed a process
> running as the SAME USER to rewrite a path inside the runner's own directories while a run was in flight. That
> process could already delete the main checkout outright, so no ordering of checks can defend against it. The runner
> is built to be safe against ACCIDENTS, and that line is written down here. R3-F1 gets the cheap exact-path fix;
> R3-F2 and R3-F3 are accident-class and are fixed. **BLOCKERs: none.**

# Phase 6 architecture review (narrow, triggered by thrashing): the regen runner's threat model

Scope: `materialise`/`fresh`/`discard`/`read_back`, `launch`/`run_in_group`, `_git` and `_env` in
`scripts/regen-pages.py`; `run_in_group` in `scripts/explainer-serve.py`; `main_checkout` in
`scripts/session-state.py`.

Read first:
- the r1–r3 reviews and the r1/r2 coordinator docs under `docs/reviews/`;
- backlog row 408;
- `docs/review-method.md` → *Can a redesign remove it?*

No ADR covers page regeneration (ADR-0010 covers what the goals view is built FROM, not how the tree is produced), so
none is re-litigated. Nothing under `.claude/plans/` was read.

## 1. Thrashing or prose floor?

**Thrashing, and design-caused, but the design is not what is wrong.** Every finding carried a repro, so none is a
prose floor. Classify each data-loss repro by WHAT had to happen for the loss to occur:

| Round | Finding | Needed to reproduce | Class |
|---|---|---|---|
| r1 | C1 (c): a REAL worktree already at `.claude/regen-tree` is force-cleaned | A fixed, reused path that something else may occupy | **Accident** — fixed by r1's fresh private path |
| r1 | X1 / C1 (a, b): a forged `.git` pointing at main or another worktree | A process rewrites `.git` inside the runner's tree | Same-user adversary |
| r1 | X2 / C3: a symlink swapped in between the proof and `checkout --force` | A process swaps the path at the exact moment | Same-user adversary |
| r2 | F1: `<common>/worktrees` swapped for a symlink before `rmtree` | A process swaps a directory inside `.git` mid-run | Same-user adversary |
| r2 | F2: a victim's `gitdir` text rewritten to name this run's tree | A process edits git admin files mid-run | Same-user adversary |
| r3 | F1: `<private>/tree` swapped for a symlink to main right after `clone` | A process swaps the path inside a 0700 dir this run created | Same-user adversary |
| r3 | F2: `REGEN_MAIN_CHECKOUT` names another repository | A stale or wrong environment variable is inherited | **Accident** |
| r3 | F3: an unbounded wait after SIGKILL in `_git`, leaving `*.lock` | A signal arrives mid-git | **Accident** |
| r1 | X3 / r2 F3, F4, F6: process-group escape and drain | A slow or hung generator, a signal | **Accident** (F3's `setsid` escape is a stated bound) |

Each fold closed the swap path the last round used, and the next round found another, because **there is always
another**. A process that can rewrite paths inside this user's directories can also run `rm -rf` on the main checkout.
No sequence of checks in a script running as that same user outlasts it. `review-method.md`'s question *can a redesign
remove it?* has an honest answer here: a redesign CANNOT remove the same-user adversary. It can only remove the
accidents. The r2 design removed most of them, and r3's F2 and F3 are two it left, fixed below.

## 2. The threat model (to be written into the runner's docstring and row 408)

**In scope (accidents):**
- a path that something else already occupies;
- a stale lock;
- a killed or hung generator, a signal mid-run;
- an inherited environment (`GIT_*`, `REGEN_MAIN_CHECKOUT`);
- a crash leaving debris;
- two runs at once.

The runner must never lose or move data, or write into the main repository, under any of these.

**Out of scope (stated, not defended):** a process running as the same user that rewrites paths or git admin files
inside the runner's private directory, or inside `.git`, while a run is in flight. The runner's directory is `0700`
and created fresh by `mkdtemp`, so only this user can touch it. Such a process needs no help from the runner to destroy
the checkout.

This is the same shape as the bound the repository already states for its hooks: a process that leaves its group is
not killed.

## 3. What the r3 fold does

- **R3-F1:** compare the tree path EXACTLY (no `realpath`) and refuse if `<private>/tree` is a symlink before the
  in-clone commands. This is cheap, removes `read_back`'s accidental acceptance of a redirected tree, and is NOT a
  claim of race-freedom. Its docstring must say so and cite §2.
- **R3-F2:** `main_checkout` accepts `REGEN_MAIN_CHECKOUT` only if it is a main checkout of THIS repository (its git
  common dir equals the runner's), and `_env()` strips it from everything that is not a generator the runner launches.
- **R3-F3:** `_git`'s signal path gets the same grace and bounded wait as `run_in_group`.
- **Remove, or keep but no longer cite as defences:** any docstring or case that claims a defence against the
  same-user swap class. Cases that pin the accident class stay.

## 4. Stop condition

From r4 findings are FILED unless BLOCKING (`review-method.md` §0 Q4c). A round-4 finding in the same-user swap class
is out of scope under §2 and is recorded as such, not fixed. Only an ACCIDENT-class path that loses or moves data, or
writes into the main repository, is a BLOCKER.

## 5. Not written down until now

The runner had no threat model. Each reviewer, correctly told to "refute data loss", took the strongest adversary
available, and each fold accepted that frame without saying so. That missing sentence is the cause of three rounds,
and §2 is it.
