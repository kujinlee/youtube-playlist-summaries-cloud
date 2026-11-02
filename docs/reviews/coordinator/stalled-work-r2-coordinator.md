# Round 2 — `stalled-work` (PR #452, backlog #410) — coordinator — NOT CONVERGED (Codex); the route moves to REDESIGN

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 2
fixes_nontrivial: true
subject: stalled-work
halves:
  codex: ran
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: R2-1, severity: Major, aim: deliverable, fix_induced: true, component: cache, disposition: fixed}
  - {id: R2-2, severity: Major, aim: deliverable, fix_induced: true, component: time-bound, disposition: fixed}
  - {id: R2-3, severity: Major, aim: deliverable, fix_induced: true, component: merged-check, disposition: fixed}
  - {id: R2-4, severity: Major, aim: deliverable, fix_induced: true, component: cache, disposition: fixed}
  - {id: R2-5, severity: Minor, aim: deliverable, fix_induced: true, component: cache, disposition: fixed}
```

Codex reviewed `f25c84ad`, the r1 fold plus the cap and the cache. Every finding is fix-induced, four of them Major:

| ID | Severity | Finding |
|---|---|---|
| R2-1 | Major | the cache stores the RENDERED block, so a planted cache file reaches the context verbatim, and `block: null` hides every stall |
| R2-2 | Major | no overall deadline: 64 local branches with 4 s git calls and a hung gh ran past 31 s with empty output, though every single call stayed under its own timeout |
| R2-3 | Major | patch-id ignores meaningful whitespace: `return 2` outside an `if` on the branch and inside it on master is declared MERGED |
| R2-4 | Major | a clear answer cached at 29m59s hides a stall that ripens at 30m until the cache expires at 39m59s |
| R2-5 | Minor | `at: NaN` passes both freshness comparisons, so a poisoned cache never expires |

**The wall: the cache holds a VERDICT, and the merged check holds a GUESS.** The round-1 cache stored text that had already been shaped, and an answer that was true only at the moment it was measured. Patching the reader (authenticate the file, expire at the next deadline) keeps both properties and adds a third mechanism. **The redesign stores measurements, not conclusions:**
- **The cache holds STRUCTURED DATA only** (kind, a ref or name token, the commit or PR timestamp, counts), never rendered text. On every read the ages are recomputed from now, every string goes through `shape`, and the block is rendered fresh. A file that fails a strict schema (types, finite numbers, bounded lengths, known kinds) is ignored and re-measured. Items 20 minutes old or more are cached as CANDIDATES, so a stall that ripens inside the TTL shows at the next prompt.
- **ONE monotonic deadline** for the whole check, under 60% of the hook's timeout. Every git and gh call takes the REMAINING budget, and expiry is a framed CANNOT RUN whatever the branch count.
- **MERGED only when EVERY commit's patch-id is on origin/master.** The combined-diff (squash) heuristic is gone. A squash-merged branch shows STALLED with a "check whether it was merged" hint, never a false MERGED.

**Route: REDESIGN.** Round 2 found four fix-induced Majors in two components (the cache, the merged check); patching each would add a mechanism per finding to the components that produced them.
