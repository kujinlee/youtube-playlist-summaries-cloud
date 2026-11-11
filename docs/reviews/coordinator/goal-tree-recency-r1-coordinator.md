# Round 1 — `goal-tree-recency` (backlog #497, PR #497) — coordinator — NOT CONVERGED (both halves)

```yaml
round: 1
fixes_nontrivial: true
subject: goal-tree-recency
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: bucket, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: merge-time, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: false, component: goal-number, disposition: fixed}
  - {id: C2, severity: Medium, aim: deliverable, fix_induced: false, component: bucket, disposition: fixed}
  - {id: C3, severity: Low, aim: deliverable, fix_induced: false, component: bucket, disposition: fixed}
  - {id: C5, severity: Low, aim: deliverable, fix_induced: false, component: style, disposition: fixed}
  - {id: C6, severity: Low, aim: deliverable, fix_induced: false, component: bucket, disposition: fixed}
```

Both halves on `fa54e005`. **Held (both):** the built page is valid HTML (no unclosed `<details>`, no duplicate ids); time
passing alone logs no snapshot; `--print` and page fold counts agree; NEEDS YOU is identical to master; 246/246.

- **X1 = C1 (fixed, the regression):** in-flight ledger work naming a thread that already merged or closed is folded away
  (both reproduced). `bucket` must return `now` for ANY non-parked ledger entry that names the thread, BEFORE the landed
  checks; and an open PR counts as represented only by a structured association (a thread's refs), never by a mention in
  detail text (Codex). Rule: **nothing current is ever inside a collapsed group.**
- **X2 (fixed):** prefer GitHub `mergedAt`; the commit date is the fallback, and a missing commit date never hides a
  readable `mergedAt`.
- **X3 = C4 (fixed):** numbers move when a goal is inserted. Fix: anchors by SLUG (`goal-<slug>`), and number goals by
  their FIRST request's timestamp (chronological, ties by file order), so insertion mid-file with a later date does not
  renumber; deletion still can, and that is stated in the grammar note at the top of `docs/goal-threads.md`.
- **C2 (fixed, the owner's word "queued (planned)"):** an unstarted `fix` or `blocker` thread declared under a goal IS
  planned — it is queued; unstarted `bookkeeping`/`side` stay later. The coordinator's reading of "planned" in the owner's
  01:00 request; the PR body says so.
- **C3 (fixed):** `PARKED` matched case-insensitively and as a word at the start of a clause; `NOT PARKED` does not park.
- **C5 (fixed):** fold summaries, goal counts and quote times use `--ink-soft` (AA in both themes).
- **C6 (fixed):** a PR closed within 48 h is `recent`, not `older` (read `closedAt`).
