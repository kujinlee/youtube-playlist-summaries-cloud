Reviewed head: 0bc51b60463991737d654429e0402f0c2c472f37

# tree-leaf-row-status — round 1, Claude half (adversarial)

Subject: `git diff origin/master...HEAD`. The new else-branch in `derive_thread` (`scripts/goal-tree.py:893-899`),
2 self-test cases (`:5839-5850`), 3 mutations (`scripts/mutations/goal-tree.json`, last three entries), pin 502 -> 505,
and doc rows (backlog #689, backlog #630, `docs/goal-threads.md`, register row 23, dashboard entry).

## What I ran

- `python3 scripts/goal-tree.py --self-test` in the worktree: `584/584 self-test cases passed`.
- Each of the 3 new mutations, and 2 extra mutations of my own, applied to a full COPY of the tree under
  the scratchpad (`689r1-claude/c-*`). The unmutated control copy: 584/584.
  - `m689a` (`all` -> `any`): 583/584, the ⭐ #689 case FAILS. Bound.
  - `m689b` (`leaf_cells is None or …`): the ⭐ #689 case FAILS, plus the agenda cases (#515/#611/r1 H1 …), then the
    suite CRASHES with `IndexError` in `_cases_650` (`:3537`). The named `[FAIL]` line prints before the crash, so it
    counts as a kill.
  - `m689c` (`if False …`): 582/584, both #689 cases FAIL. Bound.
  - mine, drop `live_rows and`: 583/584, killed by the existing all-fated case (`...and a leaf whose rows are ALL fated`).
  - mine, drop `if not by_row else None`: **584/584, survives** (see MINOR 4).
- A live derivation from this worktree (`collect` + `derive`, scratchpad `689r1-claude/measure.py`): `errors: {}`,
  **7 leaves** take the new branch, all `merged`, all bucketed `recent`, all with `merged_at None`: backlog #544, #499,
  #515, #611, #612, #689, #630.
- A probe of the new branch's interactions with the ledger, `waits`, an unread gh and the bucket clock
  (scratchpad `689r1-claude/probe.py`).

What I checked and found SOUND: fated rows (`live_rows` excludes them; all-fated still reads ✖ by `:930`), a row
missing from the Items table (never in `closed_rows`, and `:926` makes it CANNOT RUN anyway), unread backlog
(`closed_rows` None goes to ⬜, then `:923` makes it CANNOT RUN), mixed PR+backlog refs (the `if prs:` branch is taken,
so the new code is never reached), agenda steps (`by_row=True` gives `leaf_cells None`; a step with a PR has
`by_row` forced False but takes the `prs` branch), an open PR titled for the row (the `elif opened` branch comes first;
case 5 of `_l689` uses fixture PR #30 `work (backlog #11)`), a declared `waits on` (not applied to a finished leaf,
which is right for a done row), `merged_at` None in the agenda's `late` list (`:1977-1979` requires a stamp, so it
says nothing) and in the HTML/text render (no consumer dereferences a merge SHA or PR for state `merged`).

## MAJOR

**M1. A ✅-by-cell leaf is "recent" FOREVER: it never folds into `older`, and its goal never folds as "nothing
current".** The new branch sets no `whens`, so `merged_at` is None (`scripts/goal-tree.py:967`) and no `ended_at` is
stored (`:981-984`). `bucket()` then reads `ends = [None]` (`:782`), `_age_hours(None, at)` is None (`:750-755`), and
`:784` returns `recent` — by the rule "a time that cannot be read is RECENT". That rule was written for an UNREAD merge
minute (a transient gap), not for a leaf that has no merge minute by construction.
- Failing input: leaf `fix · backlog #12`, `closed_rows={12}`, no PR anywhere, bucketed at `2027-06-01 10:00` (six
  months later): `merged | recent` (probe output).
- Live: all 7 leaves the change flips (above) read `recent`, including backlog #499, #515, #611, #612 and #544, which
  closed days to weeks ago. RECENT is a VISIBLE bucket (`:183`), so they are drawn open under "recent" indefinitely,
  and a goal whose only leaves are such rows can never reach `counts = "nothing current"` (`:2273-2275`). The
  `older` fold line says "merged more than 48 h before" — these leaves are exactly that and never get there.
- The change's own claim (dashboard entry, backlog #689 Fix) is that the leaf now "reads done, not queued". It reads
  done in its glyph, but sits in the "landed in the last 48 h" region of the tree permanently, so the tree still
  misstates Goal 2's shape — the defect #689 was filed for, moved one bucket.
- No case binds the bucket of a ✅-by-cell leaf.

**M2. The ✅ is read from the RUNNING checkout's `docs/backlog.md`, so in the house flow (the tick is written on the
branch BEFORE the PR opens) a leaf reads ✅ before any PR exists — and that is logged, and drops the in-flight work from
the agenda.** `collect(root)` reads `root / BACKLOG_REL` (`:1517-1523`), where `root` is the checkout the script runs
from; `--snapshot` logs to the MAIN checkout's log (`main()`, `main_root / LOG_REL`, about `:3146`) whatever checkout
derived it. The stated bound beside `cells_held` (`:855-861`, r3 F2) covers only the window AFTER the PR opens (the open
PR outranks the ✅); the window between the tick and `gh pr create` is uncovered for a tree leaf, and that code's own
cost rule says "a false ✅ hides open work".
- Measured, now: derived from this worktree, backlog #689 and backlog #630 read `merged · ✅ in its Status cell · no
  merged PR names it`; both rows are ✅ only on this unmerged, unopened branch (`origin/master` has #630 🟠 and no #689).
  A `--snapshot` from here would log them as landed (the timeline's `landed` list, `:2419-2420`).
- In-flight work vanishes from the agenda: leaf `fix · backlog #12`, `closed_rows={12}`, ledger entry
  `{"id": "work-12", "what": "building backlog #12"}` (not parked). Before: `next` -> `inflight` (`:950-951`) -> listed in
  `agenda_digest(...)["now"]`. After: `merged`, so `:961-962` (`t["state"] not in _FINISHED or open_prs`) drops it —
  probe output `digest now: []` vs `digest now if next: ['backlog #12']`. `merged` is not in the `inflight` promotion
  set at `:950`, so the leaf keeps ✅ with "in flight: …" trailing its detail.
- The agenda steps (`by_cells`) already have this window; the change extends it to every tree leaf. If it is to be
  accepted, the bound needs stating in the docstring BOUNDS (`:84-86`) and a case; otherwise the ✅-by-cell reading
  should yield to a non-parked ledger entry (as an open PR already does).

## MINOR

**m3. With git or gh unread, a leaf whose rows are all ✅ still reads ⚠ CANNOT RUN, while the agenda step for the same
row reads ✅ (r1 C7).** `:869-870` (`elif unread and not by_cells and not cells_held`) is reached before the new branch,
and `by_cells` is False for every leaf. Input: leaf `backlog #12`, `closed_rows={12}`, `errors={"gh": "gh down"}` ->
`cannot | CANNOT RUN — gh down` (probe). Not a regression, but the new reading needs neither git nor gh (exactly C7's
argument), and the BOUNDS text (`:85-86`) says the leaf "reads ✅" without this exception.

**m4. The `if not by_row else None` guard at `:895` is EQUIVALENT — no mutation can kill it.** Deleting it leaves the
suite 584/584. With `by_row` True the branch is reached only when `closed` is None (so `leaf_cells` is None anyway),
`row_open` is non-empty (so `all(...)` is False), or `live_rows` is empty. It is dead defence; either drop it or state
it as equivalent so a manifest audit does not count it as covered. Related: `m689b` replaces two clauses at once and
is killed mostly through the AGENDA cases before crashing (`IndexError`, `:3537`); a mutation that changes only
`leaf_cells is not None` (keeping `not by_row`) would isolate the leaf clause.

**m5. The detail "no merged PR names it" is false for the very rows that motivated the fix.** backlog #515, #611 and
#612 ARE named by merged PR #611 (`bdf16975`, subject tail `(backlog #515, #611, #612)`); the code only fails to match
that spelling (`:872`, `\(backlog #N\)`). Input: the live tree, leaf `fix · backlog #515` -> `backlog #515 ✅ in its
Status cell · no merged PR names it`. The honest wording is "no merge subject ends `(backlog #N)`" (backlog #689's own
title says exactly that).

**m6. The first snapshot after this merges reports five rows as "landed" in that interval**, though they landed days
earlier: #544, #499, #515, #611, #612 move `next` -> `merged`, and the timeline's `landed` list (`:2419`) tells every
such transition as a landing in the interval. One-off, but it is a false event on the record; worth a line in the
dashboard entry or the row.

**m7. Register row 23 (`docs/optimization-register.md:47`).** "18 rows on 11-21" reads as eighteen rows dated 11-21;
`.claude/fable-pilot.jsonl` holds 18 rows dated 11-13 to 11-17 (file last modified 11-17), read on 11-21. "Builds: 6
over 4 rounds on Fable (1 run)" omits the second Fable build row (`start 11-17 05:07`, no `review_rounds` or
`fix_induced_findings` recorded); say "1 run with data, 1 unrecorded". The other figures check out against the file:
3 Fable Phase 6 rows, folds 5 and 4 (Fable) against 2 and 0 (Opus), builds 0 and 0 on Opus over 2 runs.

Doc rows otherwise accurate: backlog #689's cause and measurement match `bdf16975` and the regex; `docs/goal-threads.md`
lines parse (the live derivation read them without error); the pin 502 -> 505 matches the 3 added entries.

VERDICT: NOT CONVERGED
