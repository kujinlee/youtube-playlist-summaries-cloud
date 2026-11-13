# Round 2 — `needs-owner-settled` — coordinator — ⟳ NOT CONVERGED (Codex); history walk covers every line, merges never diffed

```yaml
round: 2
fixes_nontrivial: true
subject: needs-owner-settled
halves:
  codex: ran
  claude: skipped
findings:
  - {id: R2-1, severity: Medium, aim: deliverable, fix_induced: true, component: settled-history-reader, disposition: fixed}
  - {id: R2-2, severity: Low, aim: deliverable, fix_induced: false, component: settled-history-reader, disposition: declined}
```

REVIEW GAP: claude — alternation

**Subject:** `git diff origin/master...HEAD` on `needs-owner-settled` (PR #528, backlog #496), Codex half on `a5f32c3d`.
**Halves:** `codex/needs-owner-settled-r2-codex.md` (R2-1 Medium, R2-2 Low, model `gpt-6.1-sol`, 450/450 self-tests,
NOT CONVERGED). The Claude half sits this round out (rounds 2+ alternate).

**R2-1 (Codex Medium): fixed. Fix-induced:** the r1 fold chose `--first-parent --diff-merges=first-parent`. Codex
reproduced the defect. A feature branch forks, master introduces an ask under `OPEN`, then master rewrites the head
to `SPEC MERGED`, and master is merged into the feature. Diffed against its first parent, the MERGE "introduces" the
marker, already under the settled head, so the row is never flagged. Feature branches here merge master in routinely.

**The new walk** (`scripts/goal-tree.py`: `backlog_commits`): ONE `git log --topo-order --diff-merges=off -p -U0 …
-- docs/backlog.md`.
- Every line of history is walked, not only the first-parent chain.
- A merge is never diffed, so each change is attributed to the non-merge commit that made it, on whichever line.
- The order is topological: a child always comes before its parents, whatever the commit dates say. "Newest
  introduction" (`head_when_marked`) is the first introduction in that order. Two introductions on parallel lines,
  neither an ancestor of the other, are ordered as git's walk puts them. The docstring says so.
- Shallow → NOT READ, any git failure → NOT READ, an empty log → NOT READ, and the two memos are unchanged.

**Evil merge, one stated behaviour: the merge's own edit is not read.**
- A conflict resolution that rewrites the head of a row whose marker an ordinary commit introduced is still a
  rewrite. Today's head is compared with the head at that commit, so the row is flagged.
- A marker that ONLY an evil merge wrote has no introduction, so it is NOT READ. It is never "unchanged".

**Cases (real git, inside `fixture_git.isolated()`, every commit date pinned):**
- `⛔ … a marker introduced and settled on master, then MERGED in, is flagged (r2 Codex R2-1)`. This is Codex's
  scenario. It was **red before the fix** (got `None`).
- `⛔ … an EVIL merge that rewrites the head is a rewrite, never the marker's introduction`. Red before the fix.
- `⛔ … a marker only an EVIL merge wrote is NOT READ — a merge is never an introduction`. Red before the fix.
- `⛔ … the NEWEST introduction is topological, never by commit date (r2 Codex R2-1)`. The marker's first commit
  carries a 2030 date. One line removes the ask and renews it under a new head, and the other line edits another
  row. Red before the fix.

**R2-2 (Codex Low): a stated bound, not fixed.** A row is keyed by its number, so a renumbered row is a new row. Its
new number's first marker is an introduction under the head it had then. A head rewritten BEFORE the renumber is no
longer seen. Renumbering is rare here, and following a row across numbers would need a row identity this table does
not carry. The bound is written in `backlog_commits`' docstring. The case
`backlog #496 real git BOUND: a RENUMBERED row is compared with its new number's first marker (r2 Codex R2-2)` pins
it, so the case goes red, as an alarm, if the bound is ever closed.

**Measured, not recalled.**
- **Cost** (`needs_from_backlog` with the real reader):
  - `d678369d` (10-27, 28 waiting rows): 0.61-0.83 s over three warm runs, and 1.59 s on the first, cold run. r1
    measured 0.71 s. The bound is about 3 s.
  - `1b4b74d3` (10-26, 28 rows): 0.65 s.
  - The raw `git log -p` takes 0.37 s, against 0.35 s first-parent. It reads 217 commits, against 214.
- **11-03 corpus (`11a70deb`):** backlog #306 is flagged by clause 1 and backlog #384 by clause 2. Backlog #2,
  backlog #86, backlog #198 and backlog #307 are listed and unflagged. 1.08 s.
- **Every backlog commit since 10-23, to `a5f32c3d`:** 117 revisions and 1132 listed row-revisions. r1 counted 115
  and 1131; the difference is this branch's own two commits, one of which lists one more row.
  - Clause 1 fired only on backlog #90 (43), backlog #194 (43) and backlog #306 (47).
  - Clause 2 fired only on backlog #384 (15).
  - 0 were NOT READ.

  These are **identical to r1's numbers**.
- **Suite:** `--self-test` went from 450 to 455 cases.
- **Mutations:** 3 were added, so the pin moves 347 → 350.
  - `--first-parent --diff-merges=first-parent` restored is killed by the R2-1 case.
  - `--diff-merges=first-parent` alone is killed by both evil-merge cases.
  - `--topo-order` dropped is killed by the topological case.

  A scratch copy holding only these 3 entries gave **3 killed, 3 attributed to the case each names, 0 survivors**.
  That is a diagnostic slice; CI runs the full sweep.

**Not covered.** No mutation covers the renumber bound: it is a docstring and a pinned case, not code.
