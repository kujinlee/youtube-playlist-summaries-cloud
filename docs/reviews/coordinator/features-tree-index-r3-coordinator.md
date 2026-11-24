# Round 3 — `features-tree-index` (PR #624) — coordinator

```yaml
round: 3
fixes_nontrivial: false
subject: features-tree-index
halves:
  codex: skipped
  claude: ran
findings:
  - {id: C3-1, severity: Minor, aim: tests, fix_induced: true, component: gap-counts, disposition: filed}
  - {id: C3-2, severity: Minor, aim: deliverable, fix_induced: true, component: fragment-ids, disposition: filed}
```

REVIEW GAP: codex — alternation

Reviewed head `be768f8e` (Claude half only). Verdict CONVERGED: no Blocker or Major.

## Findings

**C3-1 — the 10-row inline cap and the "N more" count are untested. FILED as backlog #711.** The reviewer
measured it in a scratch copy: removing the cap, or counting closed rows as "more", still passes 41/41. The cap was
untested on master too; what round 2 added is a comment and a round document that claim coverage. Fix-induced in
that sense (the false claim). Minor, so filed rather than folded, and the code is left as reviewed.

**C3-2 — the comprehensibility spec's key table still names `/features#<slug>`. FILED as backlog #712.** Round 2's
`f-` prefix made that table row stale; the goals row was stale before this PR. No link of that shape exists in the
repo or in `~/explainers`.

## Refutations that failed (recorded so round 4 is not owed for them)

- Every card id and index link goes through `frag_id`; `key_link("feature")` agrees with it; ids stay injective.
- `row_disagreements`' expected sets are literals; the one shared input (severity order) fails red when wrong.
- The self-test lookup that reads a miss as empty cannot pass vacuously at any of its four uses.

## Not run this round

Full mutation sweep (round 2 ran the two touched manifests in a scratch clone: 43/43 and 80/80), a real-browser pass,
`check-page-links --build --ci` (round 2: rc=0).
