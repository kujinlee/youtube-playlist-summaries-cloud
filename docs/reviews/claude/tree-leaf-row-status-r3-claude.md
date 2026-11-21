Reviewed head: d237dfe772a9888c6ac6ba36b3045fecf67002a0

# Round 3 — `tree-leaf-row-status` — Claude adversarial review

Subject: backlog #689, `scripts/goal-tree.py`, with the round-2 fold d237dfe7 (`_subject_merges_row`, the `named`
context split, the `older` fold that separates `by_cell` leaves).

## What was run

- `python3 scripts/goal-tree.py --self-test` at HEAD: **592/592 passed** (origin/master 75f2c581: 582, so +10, as the
  dashboard entry says). The branch contains origin/master.
- **Every backlog #689 mutation (17), run on a copy** (`git archive HEAD` into the scratchpad, each edit applied, the
  self-test re-run, the `[FAIL]` lines checked against `expect`): **17/17 killed by their named case.** All 519 manifest
  anchors in `scripts/mutations/goal-tree.json` resolve exactly once, so the pin of 519 matches the manifest. The two
  older entries the fold re-anchored (backlog #650 "finished prerequisite loses the day", backlog #515 "merged PR that
  named an open row") are still killed (3 and 5 failures).
- **A live derivation, run in-process from the worktree** (`collect` + `derive`, no snapshot written; git log origin/master
  n=500, gh read, no errors), checked against `git log origin/master` and the Status cells in `docs/backlog.md`:
  - The list-tail rows (backlog #515, #611, #612) read `merged 11-21 01:17 · bdf16975 via PR #611`, which is correct.
  - The `by_cell` leaves are backlog #544, #499, #630 and #689. #689 reads ✅ only because this branch ticks its row
    (the bounded r1 M2). #630 has no subject naming it as a row, which is correct. **#544 and #499 do have real merges**:
    `(backlog #544, owner card A) (#543)` and `(backlog #499, slice 1) (#502)` / `(… slice 2) (#503)`. See m3.
  - Across the 500-subject window, every row a list tail names is either ✅ (so the list tail counts) or open. The
    open ones are backlog #395, #406 and #588, and none of them has a declared no-PR leaf today.

## Findings

### MAJOR M1 — a leaf that names BOTH rows of a list tail still reads ✅ merged while one row is open (X3 is not closed)

`scripts/goal-tree.py:909-910` (`hit = next(... if any(_subject_merges_row(subj, n, …) for n in live_rows))`) and `:919`.

The gate is applied per row, but the leaf combines rows with `any`. In a list tail, one ✅ row is enough to make
the whole subject count as the leaf's merge, and that includes the rows that are still open. The fold's own contract
says otherwise. Its dashboard entry says the list tail counts "only when the row is ✅ … so … a PR that only touched
an open row does not close it". The by_cell path just below it requires EVERY live row to be ✅.

Failing input (in-process, `derive_thread`, tree leaf, `by_row=False`):

```
refs [["backlog",23],["backlog",46]], closed_rows {23}, fates all None,
merged_rows [("311d363", 537, "Part (backlog #23, backlog #46) (#537)")], all_merged_at {537: "2026-11-08 10:00"}
→ state "merged", detail "merged 11-08 10:00 · 311d363 via PR #537"      (backlog #46 is open)
```

This is the backlog #406 shape that X3 named, written as a two-row leaf. `docs/goal-threads.md:204` declares exactly
`fix · backlog #231, backlog #406, PR #537`. It is saved today only by its `PR #537` ref, which sends it down the PR
path. A false ✅ hides open work, so I rate it MAJOR, as X3 was.

On origin/master a list tail never matched, so this input read `next` there. The `any` combination already existed
for the exact form (`(backlog #23) (#50)` gives the same ✅ on master). The list-tail route into it is new.

**fix_induced: no for d237dfe7.** The defect entered through 4c191f00 (round 1's list-tail matcher). Round 2's per-row
gate left it open, but did not cause it. A fix is any of these, in narrowing order:
- a list-tail subject counts for the leaf only when EVERY live row it names is ✅;
- `all` over the rows the subject names;
- an open row the leaf names vetoes the list-tail hit.

No case covers a multi-row leaf with a list tail: all four `_x3` leaves name one row.

### MINOR m2 — a ✅ row gets the credit and the age of a PR that only touched it

`scripts/goal-tree.py:482-489` (`_subject_merges_row`), `:909-921`, and `_blocker` at `:563`.

The gate checks that the row is done. It never checks that THIS PR did it. Take a row that a partial PR named in a list
tail, which was later ticked by a commit that does not name it. The leaf then reads merged by the partial PR, at the
partial PR's time, and it falls into `older` at once. The row reads as finished more than 48 h ago, although it was
finished an hour ago.

Failing input:

```
refs [["backlog",46]], closed_rows {23, 46},
merged_rows [("bbb",593,"other (backlog #651) (#593)"), ("311d363",537,"Part (backlog #23, backlog #46) (#537)")],
all_merged_at {537: "2026-11-08 10:00", 593: "2026-11-20 09:00"}
→ "merged 11-08 10:00 · 311d363 via PR #537", by_cell None, bucket "older" at 2026-11-20 10:00
```

Real data has this shape. `_blocker("backlog", 231)` takes PR #590 (`(backlog #588, #231)`, 11-15 06:00, and backlog
#588 is still open) as the merge. But `git log -S"| 231 | ✅ (was 🟠; REOPENED"` shows that the ✅ was written by PR #593
(11-15 14:07), whose subject names only backlog #651. The cell-only reading of 0bc51b60 was the honest one: "✅ in its
Status cell, no merge known".

**fix_induced: no for d237dfe7.** It came from 4c191f00, and for ✅ rows d237dfe7 behaves the same. It is MINOR
because the glyph is right and only the PR and time are wrong. It could be bounded: say in the docstring that the PR
is the newest subject naming the row, not the commit that ticked it.

### MINOR m3 — a tree leaf whose open row a list tail names says "no PR names it yet", while the agenda step says the PR

`scripts/goal-tree.py:911` and `:943`. `named` is computed for every leaf, but it is read only under `row_open`, and
`row_open` is always `[]` for a tree leaf. With `refs [["backlog",46]], closed_rows {23}` and the PR #537 subject
above:
- the tree leaf reads `next · no PR names it yet`;
- the agenda step for the same row (`by_row=True`) reads `backlog #46 is not ✅ in its Status cell · PR #537 (311d363)
  merged naming backlog #46 · no open PR names it`.

The leaf's sentence is false, which is the r1 m5 complaint in its open-row form. The same matcher gap affects the
by_cell detail "no merge subject names it as a row". It is true by the letter, but backlog #544 (`(backlog #544, owner
card A) (#543)`) and backlog #499 (`(backlog #499, slice 1) (#502)`) have real merges that the tail regex
`_ROW_TAIL_RE` (`:473`) does not read, because a qualifier after the number breaks the list. On live data, 2 of the 4
by_cell leaves have such a merge.

**fix_induced: no.** origin/master said the same thing for this input. Round 2 added the context split but scoped it
to agenda steps.

## Hunted and not found

- **The `ticked` word and the timeline story.** `_said_state` feeds `changes`, and the story's `trans` regex
  `: (\w+) → \S+ (\w+) — ` reads `ticked` as a word. `landed` is only `b == "merged"`, so `ticked → merged` (a later
  real merge) is told as landed, and `merged → ticked` as moved. Both are right.
- **The agenda digest `late` list** reads `merged_at`, and a by_cell leaf has none, so it is never late.
- **The `older` fold.** The by_cell leaves are counted apart. A whole goal folded (`counts`) says `N older` and claims no
  age. The page's `older (N)` summary prefix is unchanged (the case at `:4940`). No other script parses the fold text
  (grep of `scripts/`).
- **`_blocker`'s change** is behaviour-neutral, since `n in closed` is already guaranteed there. Its mutation passes
  `None` and is killed.
- **Ambient passes.** I flipped each X3 and X4 case's claim through its mutation, and each goes red on the named case
  only.

VERDICT: NOT CONVERGED
