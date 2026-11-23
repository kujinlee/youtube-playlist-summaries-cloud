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
- **X2 (MAJOR): the three unreached libraries still produce Task 22 work. ACCEPT; the conflict is FILED for the owner.** The libraries are `page-chrome`, `page-markup` and `fixture-git`.
  - **The conflict:** spec §4b says a component the experiment never reached is graded `argued`, is not NEEDS-WORK, and files no backlog row. That leaves SHIP + argued, which §4b calls permitted. But §9, enforced by the guard's `[ship-experiment]` rule, refuses SHIP for a plugin-channel library the tier-A experiment does not back. DON'T-SHIP has no reason. **For these three rows, the spec allows no verdict.** That is a spec fork, so it is the owner's to decide.
  - **Fix now, without deciding it:**
    - the three rows remove every proposed backlog item and every priced re-run;
    - each row's notes say: "§4b: unreached; files no backlog row at Task 22. The verdict is held at NEEDS-WORK only because §9 refuses SHIP; see backlog #<new>";
    - grade `argued`, if the guard allows it for these rows.
  - **File ONE backlog row** asking the owner, at the Task 21 stop, to resolve §4b against §9 for unreached plugin-channel libraries. The options are: SHIP + argued, with §9 relaxed for libraries; a fourth verdict; or NEEDS-WORK with §4b amended.
  - **The coordinator's recommendation:** relax §9 for a library none of whose importers failed on it, because §4's role table exists for exactly that case.
- **X3 (MINOR, fix-induced): a template route is cheaper than its own row's stated verification. ACCEPT.** `skill-explain-diff` and `skill-explain-topic` say their remaining work is one 1 h tier-A re-run, yet price the route at 0.5 h. This is folded under X1: every complete route cost includes the component's own unshared verification.

## Thrashing watch

X1 and X3 are fix-induced, in `inventory-rows`. **If round 3 also carries a fix-induced finding in `inventory-rows`, that is two consecutive rounds, and Phase 6 arms** (dev-process.md, *The arming condition*). Round 3 alternates to the Claude half.
