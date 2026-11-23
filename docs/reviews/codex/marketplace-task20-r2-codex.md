<!-- codex-review: model=gpt-6.1-terra -->

1. **MAJOR — Template routes omit required work and therefore do not establish the cheapest route.** `fix_induced: true`  
   **Where:** [inventory.json — skill-explain-diff](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/mkt-task20/docs/marketplace/inventory.json:560), `skill-explain-topic`, and other page consumers.  
   **Evidence:** The template comparisons say S2 still bites and is priced in `brief-compose`. That row selects a **0.25 h practice route**, while explicitly pricing the code fix at **8 h**. Publishing practice 28 does not bootstrap the Ask tray for a template user. Consequently the consumers’ 0.5 h route costs do not buy the behavior their own notes require. The shared 4 h template is also charged solely to `skill-brief`, although the other 29 template rows depend on it; their recorded costs are incremental allocations, not the cost of publishing each component by that route. D10 asks for each component’s cheapest route and its estimated cost.  
   **Fix:** Compare complete, dependency-inclusive route costs for each component, including the S2 code fix where required. If totals must avoid double counting, record shared costs and dependencies separately from each component’s full route cost, then reselect the cheapest route.

2. **MAJOR — The three unreached libraries still produce phantom Task 22 work.** `fix_induced: false`  
   **Where:** [inventory.json — page-chrome](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/mkt-task20/docs/marketplace/inventory.json:1381), `page-markup`, `fixture-git`.  
   **Evidence:** Each row explicitly names no defect but remains NEEDS-WORK and directs Task 22 to file one combined importer re-run. [Spec §4b](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/mkt-task20/docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md:637) says a component merely unreached by the experiment is argued, not NEEDS-WORK, and files no backlog row. Combining three phantom rows into one does not satisfy that rule. The rows identify a conflict with the SHIP guard, but the guard does not turn lack of evidence into a named defect.  
   **Fix:** Resolve the verdict/guard conflict against the spec and remove the proposed library backlog item. Keep importer verification with the actual importer work.

3. **MINOR — The shared-fix adjustment understates individual verification costs.** `fix_induced: true`  
   **Where:** [inventory.json — skill-explain-diff](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/mkt-task20/docs/marketplace/inventory.json:560) and `skill-explain-topic`.  
   **Evidence:** Each public-bar basis says its remaining work is **one tier-A re-run at 1 h**, with shared delivery and S2 fixes priced elsewhere, yet its template route is **0.5 h**. The route does not explain why its own verification costs less than the stated 1 h. Removing duplicate shared fixes does not remove this unshared work.  
   **Fix:** Include the applicable per-component verification in the template estimate, or explain and price a narrower verification that establishes the route.

**VERDICT: NOT CONVERGED**
