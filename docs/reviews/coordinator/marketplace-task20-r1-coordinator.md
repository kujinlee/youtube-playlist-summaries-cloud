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
- **X2 + C2: the cheapest route is not established. ACCEPT.** D10 names four routes: decouple behind a config file, template repository, portable core, publish a practice. No row compares them. `template-repository` is never priced. For the two harvest rows (`brief-compose`, `contract-explainer-delivery`), the practice route is already written in this commit, yet it was not compared. **Fix:** every non-ship row names the four routes, prices the applicable ones on a one-line basis (which findings each removes), and records the cheapest. Where a route does not apply, it says why in one clause.
- **C1: the route labels describe the wrong work. ACCEPT.** Correct C1's own count while folding: it is **24 of the 27** `decouple-config` rows, not 23 of 26. Most of those rows are path-resolution fixes (`${CLAUDE_PLUGIN_ROOT}`, the project root from the caller), which spec §4 explicitly rejected as a config option. The three `portable-core` rows marked "no code change" leave nothing behind. **Fix:** label each row with the D10 route whose work it actually describes.
  - **The spec gap is FILED, not decided here.** D10 has no "fix it in place, then ship as a plugin" route. Adding a route changes the spec, which is the owner's gate. In the meantime a row whose cheapest work is a fix in place records that work in its cost record (the public-bar cost), and its route is the cheapest of the four, with a note naming the gap. File a backlog row asking the owner to rule at the Task 21 stop. Nothing is published before Task 21, so this blocks nothing.
- **C3: `session-state` is graded `none` on a false attribution. ACCEPT, pending verification.** The fold first quotes `scripts/session-state.py:799` and `goal-tree.py:1542`. If goal-tree's measured failure message is raised there, the §4 all-importers-fail rule makes the grade `measured`, and the verdict follows. If it is not, the fold says so and leaves the grade as it is.
- **C4: C4 is recorded `pass` on six rows where nothing established it. ACCEPT.** The six are `page-chrome`, `page-markup`, `fixture-git`, the two orphan contracts and `agent-watchdog`. C4 becomes `unanswered` on each, unless the row quotes what established it.
- **C5: the two DON'T-SHIP orphan contracts are still in the comprehensibility shipping set. ACCEPT.** The fold reads the spec on what a shipping set holds. Either it removes them, or it states the spec line that keeps them in. The checkpoint count is re-derived after the change.
- **C7: `skill-brief`'s note misstates tier B. ACCEPT.** Tier B found `brief-compose` and failed on S2 (`experiment-tier-b.md:39`).
- **C8: practice 27 misattributes the script failures. ACCEPT.** The record says S1 and S2 account for them (`experiment-tier-a.md:12`). Its remedy column was never run, so it is marked argued.
- **C9: shared fixes are priced in more than one row. ACCEPT.** Each shared fix is priced once, in one owning row; the other rows reference it at 0 h, naming that owner. That covers the delivery invocations, and the five hook rows sharing one `hooks.json`.
- **C10: the stale "Caller" paragraph in `scripts/check-inventory.py`. ACCEPT.**
- **C11: rc 3 prints as a plain echo. ACCEPT.** Use `::warning::` so the D1 checkpoint shows as a PR annotation.

## Round topology

Round 2 alternates to **one half**. The round cap applies: from round 4, findings are FILED unless a BLOCKER.
