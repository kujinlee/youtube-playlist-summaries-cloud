# Round 1 — `marketplace-task20` — coordinator — the rows' routes and grades are not established by their evidence; the guard is honest

```yaml
round: 1
fixes_nontrivial: true
subject: marketplace-task20
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: false, component: inventory-rows, disposition: accepted}
  - {id: X2, severity: Major, aim: deliverable, fix_induced: false, component: inventory-rows, disposition: accepted}
  - {id: C1, severity: Major, aim: deliverable, fix_induced: false, component: inventory-rows, disposition: accepted}
  - {id: C2, severity: Major, aim: deliverable, fix_induced: false, component: inventory-rows, disposition: accepted}
  - {id: C3, severity: Major, aim: deliverable, fix_induced: false, component: inventory-rows, disposition: accepted}
  - {id: C4, severity: Major, aim: deliverable, fix_induced: false, component: inventory-rows, disposition: accepted}
  - {id: C5, severity: Minor, aim: deliverable, fix_induced: false, component: shipping-sets, disposition: accepted}
  - {id: C6, severity: Minor, aim: deliverable, fix_induced: false, component: inventory-rows, disposition: accepted}
  - {id: C7, severity: Minor, aim: deliverable, fix_induced: false, component: inventory-rows, disposition: accepted}
  - {id: C8, severity: Minor, aim: deliverable, fix_induced: false, component: practices, disposition: accepted}
  - {id: C9, severity: Minor, aim: deliverable, fix_induced: false, component: inventory-rows, disposition: accepted}
  - {id: C10, severity: Nit, aim: deliverable, fix_induced: false, component: check-inventory, disposition: accepted}
  - {id: C11, severity: Nit, aim: deliverable, fix_induced: false, component: ci-caller, disposition: accepted}
```

Both halves reviewed 3719d9e1 (plan Task 20, PR #619), concurrently:

- [`codex/marketplace-task20-r1-codex.md`](../codex/marketplace-task20-r1-codex.md): X1 and X2, both MAJOR; NOT CONVERGED.
- [`claude/marketplace-task20-r1-claude.md`](../claude/marketplace-task20-r1-claude.md): C1–C4 MAJOR, C5–C9 MINOR, C10–C11 NIT; NOT CONVERGED.

This is round 1, so no finding is fix-induced.

**What held.** Claude ran the CI step's shell verbatim: rc 0 and rc 3 pass, and rc 1, rc 2, a crash and a missing script all fail. `check-inventory.py` gives rc 3, and that is honest: 31 of the 34 phase-1 rows cost at least 3× more for the public bar than for the next project, and the checkpoint still fires at 29 of 32 without the two orphan contracts.

**What did not hold.** Every MAJOR is about the rows' *judgment*, not the guard. The guard checks that a cited ground exists, not that it supports the verdict. Both halves found that independently, which is the sign the finding is real.

## Dispositions

- **X1 = C6 (+ C4 in part): phantom defects in `page-chrome`, `page-markup` and `fixture-git`. ACCEPT.** The three are NEEDS-WORK only because no importer reached them. Spec §4 grades such a library `none`, and §4b separates "the experiment did not reach it" from "there is no way to assess it", naming `page_chrome.py` as the phantom-row example. **Fix:** re-judge the three under §4/§4b, so that unreached evidence is never a defect, and drop any priced "re-run an importer" route that rests on a defect that does not exist.
  - **Fixed in e5becb9e.** The three rows' notes now say spec 4b's "we have not assessed it yet" (an importer scenario that passes would assess them), name no code defect, and keep NEEDS-WORK only because SHIP is spec 9's falsifier (`[ship-experiment]`) and DON'T-SHIP has no reason. The priced re-run is dropped: both costs are 0.25 h, the floor `[shape]` allows (0 h is refused), and the route is `template-repository` 0.25 h, travelling with the importers. Task 22 files the three as ONE work item.
- **X2 + C2: the cheapest route is not established. ACCEPT.** D10 names four routes: decouple behind a config file, template repository, portable core, publish a practice. No row compares them. `template-repository` is never priced. For the two harvest rows (`brief-compose`, `contract-explainer-delivery`), the practice route is already written in this commit, yet it was not compared. **Fix:** every non-ship row names the four routes, prices the applicable ones on a one-line basis (which findings each removes), and records the cheapest. Where a route does not apply, it says why in one clause.
  - **Fixed in e5becb9e.** All 34 effort (3) rows carry a `Routes compared (D10, all argued):` sentence in `notes` (no new field; the fold script asserts every row has it), pricing each applicable route and saying in one clause why the others do not apply, then `Cheapest:`. Routes after: template-repository 30, practice 4 (brief-compose and contract-explainer-delivery at the 0.25 h floor, the practice entries being written; the two orphan contracts at 1 h). The template repository itself is priced once, 4 h argued, in skill-brief's row.
- **C1: the route labels describe the wrong work. ACCEPT.** Correct C1's own count while folding: it is **24 of the 27** `decouple-config` rows, not 23 of 26. Most of those rows are path-resolution fixes (`${CLAUDE_PLUGIN_ROOT}`, the project root from the caller), which spec §4 explicitly rejected as a config option. The three `portable-core` rows marked "no code change" leave nothing behind. **Fix:** label each row with the D10 route whose work it actually describes.
  - **The spec gap is FILED, not decided here.** D10 has no "fix it in place, then ship as a plugin" route. Adding a route changes the spec, which is the owner's gate. In the meantime a row whose cheapest work is a fix in place records that work in its cost record (the public-bar cost), and its route is the cheapest of the four, with a note naming the gap. File a backlog row asking the owner to rule at the Task 21 stop. Nothing is published before Task 21, so this blocks nothing.
  - **Fixed in e5becb9e.** No row keeps `decouple-config`: each row's notes give why it does not apply (path resolution, which spec 4 rejected as a configurable option; or not a setting), and its route is the cheapest of the four. The fix-in-place work stays as each row's `Basis (public bar)`, with a note naming the gap. The three portable-core "no code change" rows are the X1 rows above. Gap filed as **backlog #703** for the Task 21 stop; the spec was not edited.
- **C3: `session-state` is graded `none` on a false attribution. ACCEPT, pending verification.** The fold first quotes `scripts/session-state.py:799` and `goal-tree.py:1542`. If goal-tree's measured failure message is raised there, the §4 all-importers-fail rule makes the grade `measured`, and the verdict follows. If it is not, the fold says so and leaves the grade as it is.
  - **Fixed in e5becb9e. Premise verified TRUE.** `session-state.py:799` (`_common_dir`) returns `git rev-parse --git-common-dir gave no usable path (exit …)`, the only producer of that message; `goal-tree.py:1542` calls `_SS.main_checkout(root, run)`, which calls `_common_dir`; `experiment-tier-a.md:82` records goal-tree's rc 2 with that message. Grade `none` → `measured`, scenario `goal-tree: A-script-goal-tree-print, failed in main_checkout/_common_dir (session-state.py:799)`, C4 fail measured through that run. regen-pages's failure is its own (`regen-pages.py:224`). The verdict stays NEEDS-WORK (the defect is real either way); `rests_on` stays spec 4, since session-state's own sidecar entry is unexercised and `[ground-experiment]` would refuse it.
- **C4: C4 is recorded `pass` on six rows where nothing established it. ACCEPT.** The six are `page-chrome`, `page-markup`, `fixture-git`, the two orphan contracts and `agent-watchdog`. C4 becomes `unanswered` on each, unless the row quotes what established it.
  - **Fixed in e5becb9e.** C4 is `unanswered` on all six (page-chrome, page-markup, fixture-git, contract-handoff-path, contract-corpus-search, agent-watchdog); none quoted what established a pass.
- **C5: the two DON'T-SHIP orphan contracts are still in the comprehensibility shipping set. ACCEPT.** The fold reads the spec on what a shipping set holds. Either it removes them, or it states the spec line that keeps them in. The checkpoint count is re-derived after the change.
  - **Not changed:** no spec line keeps a DON'T-SHIP member in a set, and none removes it at this task. `shipping-sets.json` is Task 5's file and the scan's measured input (spec 5), and `check-inventory.py`'s `[shipping-set]` rule refuses a phase-1 row absent from it, so removal now would turn two valid rows into errors. Spec D11 has Task 22 produce the phase-1 subset and its shipping set; both rows now say they leave the set there. Checkpoint re-derived: it FIRES over 25 of 34 phase-1 rows (23 of 32 without the two orphans), down from 31 of 34 (29 of 32); `check-inventory.py` rc 3.
- **C7: `skill-brief`'s note misstates tier B. ACCEPT.** Tier B found `brief-compose` and failed on S2 (`experiment-tier-b.md:39`).
  - **Fixed in e5becb9e.** skill-brief's note now says tier B found `brief-compose.py` and was refused on S2 (`experiment-tier-b.md:39`), and that the S3 failure is a single tier-A observation (isolation note I2); contract-explainer-delivery's attribution carries the same I2 bound.
- **C8: practice 27 misattributes the script failures. ACCEPT.** The record says S1 and S2 account for them (`experiment-tier-a.md:12`). Its remedy column was never run, so it is marked argued.
  - **Fixed in e5becb9e.** Practice 27 now says the two defects account for every failure to FIND a file: S3 for the three page skills with no page, S1 for 6 of the 7 script failures, the seventh and both trayless pages being S2 (§28's), per `experiment-tier-a.md:12` and its table. The remedy table is marked ARGUED. Its heading is unchanged (it is a `practice_entry` target).
- **C9: shared fixes are priced in more than one row. ACCEPT.** Each shared fix is priced once, in one owning row; the other rows reference it at 0 h, naming that owner. That covers the delivery invocations, and the five hook rows sharing one `hooks.json`.
  - **Fixed in e5becb9e.** The six delivery invocations are priced in contract-explainer-delivery only; skill-explain-diff and skill-explain-topic drop 2.0 → 1.0 h (one re-run), skill-brief and skill-explain-findings reference it at 0 h. `hooks.json` is priced in hook-regen-backlog-page (2.0 h); the other four hook rows drop 2.0 → 0.5 h (one entry each) and reference it at 0 h.
- **C10: the stale "Caller" paragraph in `scripts/check-inventory.py`. ACCEPT.**
  - **Fixed in e5becb9e.** The docstring names both CI steps and the rc 3 pass. Mutation manifests: all 107 resolve, 6,505 edits, 0 unbound (check-inventory's 144 entries included).
- **C11: rc 3 prints as a plain echo. ACCEPT.** Use `::warning::` so the D1 checkpoint shows as a PR annotation.
  - **Fixed in e5becb9e.** The `check-inventory (live)` step's rc 3 line is now `echo "::warning::check-inventory rc 3: …"`.

## Round topology

Round 2 alternates to **one half**. The round cap applies: from round 4, findings are FILED unless a BLOCKER.
