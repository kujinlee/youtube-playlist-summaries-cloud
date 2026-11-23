Reviewed head: b935580bd298378e593d3958bf8f2762f9c878c7

# Round 3 — `marketplace-task20` — Claude half (alternation) — PR #619

Scope: the round-2 fold (`git diff e7916e28..HEAD`: `docs/marketplace/inventory.json`, backlog #704, the r2
coordinator doc), plus whether the whole branch (`git diff origin/master..HEAD`) can merge. Brief:
`task20/r3-prompt.md`. Read: the r1 and r2 coordinator docs, the r2 Codex review, spec §4 (role table), §4b, §9, D10.

## What I ran (evidence)

| Check | Result |
|---|---|
| `python3 scripts/check-inventory.py` | **rc 3**: `CHECKPOINT: the D1 checkpoint FIRED over 34 phase-1 rows ... Stop: Human step H4.` |
| `python3 scripts/check-inventory.py --self-test` | `311/311 self-test cases passed`, rc 0 |
| `python3 scripts/check-features.py` | rc 0: `35 nodes ...; 15 anchors and 29 backlog areas all claimed exactly once` |
| `python3 scripts/gen-backlog-page.py --self-test` | `250/250 passed`, rc 0 |
| `python3 scripts/check-docs.py` | `Documentation integrity OK`, rc 0 |
| My own route check (`r3-work/r3check.py`, written from scratch; it does not reuse `fold2/check.py`) | `failing 0` over 34 phase-1 rows (output quoted below) |
| Rows the branch changed that already exist on master | `[]`: the branch adds the 34 effort-3 rows and edits no existing row |

**The independent check.** It parses every `<kind> N h = parts` figure in each phase-1 row's "Routes compared"
segment. It checks four things: the stated total equals the sum of its parts; the recorded `route.kind` and
`cost_hours` match one of the figures; the recorded figure is the minimum of the figures; and it flags whether
each figure carries S2 (`S2's code fix`) and the template (`the template repository`). Excerpt:

```
skill-brief template-repository 15.0 {'decouple-config': [(19.0,'S2','')], 'template-repository': [(15.0,'S2','T')]} ok
brief-compose practice 0.25 {'template-repository': [(12.0,'S2','T')], 'practice': [(0.25,'','')]} ok
explainer-serve portable-core 9.0 {'template-repository': [(12.5,'S2','T')], 'portable-core': [(9.0,'S2','')]} ok
gen-backlog-page template-repository 6.0 {'template-repository': [(6.0,'','T')]} ok
goal-tree template-repository 6.0 {'template-repository': [(6.0,'','T')]} ok
ask-answerer template-repository 6.0 {'template-repository': [(6.0,'','T')]} ok
hook-regen-backlog-page template-repository 4.5 {'template-repository': [(4.5,'','T')]} ok
agent-watchdog portable-core 2.0 {'template-repository': [(4.5,'','T')], 'portable-core': [(2.0,'','')]} ok
check-docs portable-core 2.0 {'template-repository': [(4.5,'','T')], 'portable-core': [(2.0,'','')]} ok
failing 0
```

## Refutation attempts, by brief item

1. **X1: S2 placement — the fold holds.** I opened every cited line.
   - **Fails (rc 1), so S2 is added:**
     - `gen-dashboard.py:3570-3573`: `FAILED — brief-compose did not write` → `return 1`.
     - `gen-goals-page.py:1381-1384` and `gen-features-page.py:796-799`: the same.
     - `regen-pages`: its `--all` returns 1 on any child rc ≠ 0 (`if a.all and any(r["rc"] != 0 ...): return 1`), and its
       page map includes `gen-dashboard.py`.
   - **Degrades (rc 0), so S2 is not added:**
     - `gen-backlog-page.py:4463-4479`: the page is written without the tray, then `return 0`.
     - `goal-tree.py:3100-3101`: "A missing tray is NOT fatal".
   - **Refuted: none.** One citation is weak (N1): `regen-pages.py:865` is a SELF-TEST table, not the runtime map. The
     runtime map is `regenerable()` (`regen-pages.py:566-571`), which imports `explainer-serve.py`'s `REGENERABLE`
     (`:223-230`). It does name `gen-dashboard.py`, so the conclusion stands.
   - **I also searched for callers of `brief-compose.py` that the fold did not list.** I found one, `ask_answerer.py`.
     See C1.
2. **Incremental routes outside the phase-1 rows: yes, more than the two named.** See C2.
3. **X2 holds for the rows, with one overstatement in backlog #704.**
   - **The three rows:** `page-chrome`, `page-markup` and `fixture-git` carry no Task 22 work item and no priced
     re-run. Each says "§4b: unreached; files no backlog row at Task 22 ... see backlog #704".
   - **Backlog #704:** it is well-formed. Its area `(process / deliverable #2)` is claimed (check-features rc 0), and
     `gen-backlog-page --self-test` passes.
   - **The §4 line-500 point:** #704 states it fairly. The rows grade `argued` (§4b, lines 637-639) where §4's
     all-importers-fail row (line 500) gives `none` and records that its `argued` branch was deleted. #704 names this
     "a second disagreement this ruling settles".
   - **Not a finding:** I judge the `none` → `argued` change a disclosed spec conflict, filed for the owner. It is not a
     defect, because either grade contradicts one clause of the spec.
   - **The overstatement:** #704's premise sentence is factually too strong. See C3.
4. **X3 holds.** No route figure is below the component's own unshared verification:
   - `skill-explain-diff`, `-topic` and `-findings`: own part 1 h, the re-run.
   - `ask-answerer`: own part 2 h, which includes the `--once` run.
   - The rows whose own part is the 0.25 h floor say why (no own work, or work already written).
5. **Fix-induced breakage in round 2's fold: none in behaviour.** The guard is rc 3 as expected, and the self-test,
   check-features, the backlog page and check-docs all pass. One prose glitch is fix-induced (N2).
   - **CI step (whole branch):** `check-inventory (live)` uses `set +e` under Actions' default `bash -e`. It turns rc 3
     into a `::warning::` and exit 0, and passes rc 1 and rc 2 through. Correct.
   - **`check-inventory.py`:** the branch changed only its docstring.

## Findings

### C1 — MINOR — `fix_induced: false` — component `inventory-rows` (row `ask-answerer`)
**The one `brief-compose` caller whose row does not say why S2 is left out.**
- **The coordinator's claim:** the r2 coordinator doc says S2 is added only where the code fails on it, and "each
  row's notes say which".
- **The code:** `ask_answerer.py` also composes through `brief-compose.py` (`compose_with_brief_compose`, `:636-643`,
  with no `--source`). So it lifts the tray from `~/explainers` (`brief-compose.py:76`), which in a stranger's world
  holds no tray page. That is S2, as the brief-compose row puts it.
- **What happens on S2:** the code degrades. `write_into_page` returns `False, "the page could not be recomposed"`
  (`:657-658`). The run is still recorded as `answered` with `written: False` (`:786-792`), and explainer-serve shows
  an answer the served copy does not hold.
- **So the figure is right:** under the fold's rule, leaving S2 out is correct, like `gen-backlog-page`.
- **What is missing:** the row's "Routes compared" segment does not mention S2 at all, unlike
  `hook-regen-backlog-page` ("S2 is not added: it runs gen-backlog-page, which writes the page without the tray").
- **Why it matters:** a reader of D10's figures cannot tell whether S2 was judged here or missed. Two things make
  "missed" the likely guess: the row's own text says its importer "failed on S2", and the fold's scratch check does
  not test the S2 rule.
- **Fix:** add one clause to the route: "S2 is not added: on a brief-compose refusal the answer is recorded
  (`answered`, `written: false`, ask_answerer.py:786-792) and shown in explainer-serve's panel, not lost".
- **Not fix-induced:** the r1 row had the same omission. The fold left it unfixed; it did not introduce it.

### C2 — MINOR — `fix_induced: false` — component `inventory-rows` (later-phase rows from Tasks 17 and 18, unchanged on this branch)
**X1's incremental shape survives in at least four rows outside the phase-1 set.** The coordinator named two.
- **The rows:**
  - `check-rc-contract`: route 1 h, "travels with that guard by the same template-repository route or not at all".
  - `check-ratchet-contract`: route 1 h, "with that guard, in a template repository". The guard is check-surface-recall,
    whose route is 4 h.
  - `sweep-red-alert`: route 3 h, "ship inside the same reusable workflow". That workflow is priced in
    `mutation-sweep-job`'s 12 h row.
  - `hook-surface-recall`: route 3 h. It is "the caller of recall-llm", which exits 6 in an install. That fix is
    recall-llm's own 8 h route, and it is not in this figure.
- **The problem:** each figure is an increment on another row's work, not the component's complete cost. That is the
  reading X1 rejected for D10.
- **Why it does not block this PR:**
  - These rows predate the branch. The branch edits no existing row (measured: changed existing rows `[]`).
  - The rows are phase `later`, and the D1 checkpoint reads only phase-1 rows' `cost` fields.
- **Why it still needs doing:** Task 21 publishes one inventory, and it would be priced under two readings of D10.
- **Fix:** file one backlog row: re-derive the later-phase routes as complete costs (same convention: name each
  shared part with its owning row), before Task 21. Alternatively, fold it here; it is four rows of prose and figures.

### C3 — MINOR — `fix_induced: true` — component `backlog-704` (docs/backlog.md row 704)
**#704's premise says more than the rows do.**
- **#704 says:** "Every importer of the three libraries was exercised and failed on a defect attributed elsewhere."
- **The rows say "every EXERCISED importer":**
  - `fixture-git`'s importers are "every script in the package (for its --self-test)", shared with recall and
    ci-layer. Many of them are rows graded `none` (not exercised), e.g. `check-goal-status`, `check-features` and
    `check-anchors`.
  - `page-markup` lists "the check-dashboard-entry library", graded `none`.
- **Why the difference matters:** the population is therefore failing-plus-unexercised, not all-failing. That is the
  very population whose grade (§4 line 500's `none` vs §4b's `argued`) #704 asks the owner to rule on. A ruling made
  on an overstated premise may be applied to the wrong rows.
- **Fix:** say "every EXERCISED importer ... failed on a defect attributed elsewhere; the rest were not exercised",
  matching the rows.
- **Fix-induced:** #704 is the round-2 fold's own text. It sits in a different component from the rows, so the
  coordinator should judge whether it bears on the `inventory-rows` thrashing watch.

### N1 — NIT — `fix_induced: true` — component `review-record` (r2 coordinator doc, X1 "Fixed in")
**The S2 citation `regen-pages.py:865` is a self-test table** (`table = {...}` inside `_self_test`). The runtime map
is `regenerable()` (`:566-571`) over `explainer-serve.py` `REGENERABLE` (`:223-230`); cite those. The conclusion is
unchanged.

### N2 — NIT — `fix_induced: true` — component `inventory-rows` (rows `gen-dashboard`, `ask-answerer`)
**Two route sums nest a sub-sum with no separator.**
- **The text:** `template-repository 16 h = 4 h 1 h next_project ... plus ... about 3 h + 4 h ... + 8 h ...` and
  `6 h = 2 h 1 h next_project ... plus the --once run ..., 1 h + 4 h ...`.
- **The arithmetic is right:** 4 = 1 + 3 and 2 = 1 + 1. The prose reads as two adjacent figures.
- **Fix:** write it as `4 h (1 h next_project + about 3 h the user doc and recovery advice)`.
- **For the thrashing watch:** this is phrasing, not a defect in any figure, route choice or verdict.

## Thrashing note for the coordinator

The rows' figures, route choices, verdicts and grades held against every refutation I tried. No fix-induced finding
in `inventory-rows` is above NIT: N2 is phrasing only, and C1 and C2 are not fix-induced. The one fix-induced MINOR
(C3) is in backlog #704's text, not the rows.

VERDICT: CONVERGED
