# Round 2 — `marketplace-task20` — coordinator — route costs must be complete per component; the unreached libraries meet a spec conflict

```yaml
round: 2
fixes_nontrivial: true
subject: marketplace-task20
halves:
  codex: ran
  claude: "GAP: alternation"
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: true, component: inventory-rows, disposition: accepted}
  - {id: X2, severity: Major, aim: deliverable, fix_induced: false, component: inventory-rows, disposition: accepted}
  - {id: X3, severity: Minor, aim: deliverable, fix_induced: true, component: inventory-rows, disposition: accepted}
```

The Codex half reviewed 2fdb9cd3, the round-1 fold (`git diff 19b774cb..HEAD`): [`codex/marketplace-task20-r2-codex.md`](../codex/marketplace-task20-r2-codex.md). Verdict NOT CONVERGED.

REVIEW GAP: claude — alternation

## Dispositions

- **X1 (MAJOR, fix-induced): the template-route costs are incremental allocations, not each component's cost by that route. ACCEPT.** The r1 fold priced the shared 4 h template once, in `skill-brief`, and gave the other 29 rows only their increment. It also counted on `brief-compose`'s 0.25 h practice route as if publishing practice 28 fixes S2 for a template user. It does not: the S2 code fix is 8 h. D10 asks for *each component's* cheapest route and its cost.
  - **Fix:** every route figure is the COMPLETE cost of publishing that component by that route, including every dependency it needs: the shared template and the S2 fix where the row's own notes require it.
  - Shared work is named in the notes with the row that owns it, so a reader summing rows knows it is shared. The cheapest route is then re-selected on the complete figures.
  - D10 compares routes per component; it does not ask for a sum, so complete per-row figures are the honest reading.
  - **Fixed in 52094467.** Evidence verified first: the r1 fold's template rows gave only their increment (e.g. `skill-explain-diff` 0.5 h, with "the template repository itself is priced once, in skill-brief's row"), and `brief-compose`'s practice route publishes prose, which does not fix S2. All 34 phase-1 rows were re-derived, not only the ones Codex named: each route is now a sum of named parts (own work + the template, 4 h, owned by `skill-brief` + S2's code fix, 8 h, owned by `brief-compose`, where the row's operation reaches brief-compose + the delivery-contract fix, 3 h, owned by `contract-explainer-delivery`, on `skill-brief`'s plugin-channel route). S2 is added only where the code makes the operation fail on it (gen-dashboard.py:3563, gen-goals-page.py:1375-1384, gen-features-page.py:790-799, regen-pages.py:865, the hooks that run them) and NOT where it degrades to a page without the tray, rc 0 (gen-backlog-page.py:4463-4479, goal-tree.py:3100-3101); each row's notes say which. 32 of 34 route figures changed; the cheapest route changed for three rows, all to portable-core: `explainer-serve` (template 12.5 h vs portable-core 9 h), `agent-watchdog` and `check-docs` (template 4.5 h vs portable-core 2 h). Unchanged: `brief-compose` and `contract-explainer-delivery` (practice 0.25 h; `brief-compose`'s notes now say the practice route does not fix S2 for any consumer). `contract-handoff-path` and `contract-corpus-search` went 1 h → 2 h, the price their own public-bar basis gives the same prose. A one-off written check (scratch `fold2/check.py`) confirms, for every row, the recorded route equals the cheapest complete route, the notes state every complete figure, and the route is at least the row's own unshared work, with four stated exemptions where the route removes that work by construction (the two practice routes; `gen-backlog-page` and `goal-tree`, whose public-bar basis is S1, which the template removes): `34 rows, 0 failing; 32 route figures changed; 3 cheapest routes changed`. All figures stay `argued`: nothing was run. ⚠ Not in this fold's scope: the 12 later-phase rows; `check-rc-contract` and `check-ratchet-contract` price a 1 h route that "travels with check-surface-recall's template" (4 h) — the same incremental shape, left for round 3 to judge.
- **X2 (MAJOR): the three unreached libraries still produce Task 22 work. ACCEPT; the conflict is FILED for the owner.** The libraries are `page-chrome`, `page-markup` and `fixture-git`.
  - **The conflict:** spec §4b says a component the experiment never reached is graded `argued`, is not NEEDS-WORK, and files no backlog row. That leaves SHIP + argued, which §4b calls permitted. But §9, enforced by the guard's `[ship-experiment]` rule, refuses SHIP for a plugin-channel library the tier-A experiment does not back. DON'T-SHIP has no reason. **For these three rows, the spec allows no verdict.** That is a spec fork, so it is the owner's to decide.
  - **Fix now, without deciding it:**
    - the three rows remove every proposed backlog item and every priced re-run;
    - each row's notes say: "§4b: unreached; files no backlog row at Task 22. The verdict is held at NEEDS-WORK only because §9 refuses SHIP; see backlog #<new>";
    - grade `argued`, if the guard allows it for these rows.
  - **File ONE backlog row** asking the owner, at the Task 21 stop, to resolve §4b against §9 for unreached plugin-channel libraries. The options are: SHIP + argued, with §9 relaxed for libraries; a fourth verdict; or NEEDS-WORK with §4b amended.
  - **The coordinator's recommendation:** relax §9 for a library none of whose importers failed on it, because §4's role table exists for exactly that case.
  - **Fixed in 52094467.** Evidence verified: §4b (spec lines 637-639; also §4, line 590) says an unreached component is `argued`, not `NEEDS-WORK`, and files no backlog row; the guard's `[ship-experiment]` refuses SHIP for these rows. In all three rows the "Task 22 files it ... as ONE work item, 're-run an importer scenario ...' (round 1 C6)" sentence is replaced by the disposition's sentence ("§4b: unreached; files no backlog row at Task 22. The verdict is held at NEEDS-WORK only because §9 refuses SHIP; see backlog #704."), and the basis no longer points at a re-run priced elsewhere. Grade `none` → `argued`: the guard allows it (`check-inventory.py` has no rule refusing `argued` for a library; it passes). ⚠ The spec disagrees with itself here too: §4's all-importers-fail row (line 500) gives `none` and records that its `argued` branch was deleted (r3 CLAUDE M2); the rows say so, and backlog #704 names it as a second thing the ruling settles. Filed as **backlog #704** with the three options and this recommendation. The spec was not edited.
- **X3 (MINOR, fix-induced): a template route is cheaper than its own row's stated verification. ACCEPT.** `skill-explain-diff` and `skill-explain-topic` say their remaining work is one 1 h tier-A re-run, yet price the route at 0.5 h. This is folded under X1: every complete route cost includes the component's own unshared verification.
  - **Fixed in 52094467.** Evidence verified: both rows' notes named a 1 h tier-A re-run and priced the template route at 0.5 h. Their own part is now 1 h (the re-run), complete 13 h (1 + template 4 + S2 8); `skill-explain-findings` likewise (its basis names a re-run); `ask-answerer`'s route now carries the --once run its public bar names (1 h; complete 6 h).

## Thrashing watch

X1 and X3 are fix-induced, in `inventory-rows`. **If round 3 also carries a fix-induced finding in `inventory-rows`, that is two consecutive rounds, and Phase 6 arms** (dev-process.md, *The arming condition*). Round 3 alternates to the Claude half.
