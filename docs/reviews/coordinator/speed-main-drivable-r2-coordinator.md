# Round 2 — `speed-main-drivable` (PR #449, backlog #401) — coordinator — NOT CONVERGED; route DEFER (redesign and split skipped)

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 2
fixes_nontrivial: false
subject: speed-main-drivable
halves:
  codex: ran
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - id: R2-1
    severity: Low
    aim: instrument
    disposition: fixed
    fix_induced: true
  - id: R2-2
    severity: Low
    aim: instrument
    disposition: fixed
    fix_induced: true
```

Codex reviewed `b3db82bc`, the round-1 fold.

**The cache is correct.** 68,698 cached-versus-uncached comparisons, including 573 reused tree addresses, found 0 differences, and the live output is identical.

**The speed-up holds**, measured on Python 3.12 as a median of 3, alternating versions, under heavy load:
- the suite went from 179.87 s to 21.52 s;
- the CI-shaped live run went from 139.98 s to 10.78 s.

The LRU cap costs almost nothing against the pre-fold tree (18.84 → 20.65 s, and 13.70 → 13.92 s).

Two Minor findings, both fix-induced and both test-only:
- **R2-1:** the LRU case passes for an ambient reason. An evict-the-second-entry mutant survives 445/445, because an earlier suite entry already populates the memo.
- **R2-2:** the capacity boundary is unpinned. A `>` to `>=` mutant survives.

**Route: DEFER, skipping REDESIGN and SPLIT,** recorded with its reason in the decision log. Neither rung has a subject when the design and the answers are both sound. The fold pins both; the final-tree round files whatever it finds.
