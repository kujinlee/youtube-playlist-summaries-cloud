# Round 1 — `retire-work-lines` (PR #434, backlog #389) — coordinator — NOT CONVERGED (both halves)

Claude half: `docs/reviews/claude/retire-work-lines-r1-claude.md` — a narrow check of the row's FAILS-IF.

```yaml
round: 1
fixes_nontrivial: true
subject: retire-work-lines
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: High, aim: instrument, fix_induced: false, component: mutation-manifest, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: retirement, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: false, component: goal-tree, disposition: fixed}
  - {id: X4, severity: Low, aim: deliverable, fix_induced: false, component: goal-tree, disposition: fixed}
  - {id: C1, severity: Medium, aim: deliverable, fix_induced: false, component: retirement, disposition: fixed}
  - {id: C2, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: C3, severity: Low, aim: deliverable, fix_induced: false, component: dashboard, disposition: deferred}
  - {id: C4, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

Both halves on `f8e974a4`. **X1 (Blocking)** a goal-tree mutation's `expect` is truncated, so `--mutate` matches 0 red
cases. **X2 + C1 (the same FAILS-IF, two directions)** the retired page is still reachable as current —
`/%77ork-lines.html` and `/./work-lines.html` serve a stale copy (retirement is decided on the RAW url while file
resolution decodes it), and the index `/` lists `~/explainers/work-lines.html` because `explainers()` does not filter
`RETIRED_PAGES`. **X3** a linked worktree's plans vanish when the main checkout has no `.claude/plans/`. **X4** two plans
with the same display label overwrite each other in the timeline. **C2** present-tense "the work-lines page shows"
comments remain; **C4** `docs/features.md` lacks a goal-tree node. **C3** (the dashboard's open-PR list overlaps the goal
tree) predates this branch and is recorded under backlog #384, not fixed here. **Held:** FAILS-IF 2 (the archive is the
real last output, 138 plan files, linked once from the goal tree) and 3 for the work-lines/goal-tree pair; all nine
edited scripts' suites and entry points; the Stop hook; 2,495 mutations; no gate loosened.

**Route: ACCRETE** — every finding is decidable and local. X2 + C1 are one class fix: retirement is decided on the page's
CANONICAL identity (decoded, normalised), in the server and the index alike, so a stale file on disk is unreachable and
need not be deleted.
