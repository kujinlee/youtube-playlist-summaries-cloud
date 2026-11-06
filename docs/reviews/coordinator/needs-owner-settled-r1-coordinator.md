# Round 1 — `needs-owner-settled` — coordinator — ⟳ NOT CONVERGED (both halves); RESTRUCTURE (per-row `-S` → one row-aware history read)

```yaml
round: 1
fixes_nontrivial: true
subject: needs-owner-settled
halves:
  codex: ran
  claude: ran
findings:
  - {id: R1, severity: Medium, aim: deliverable, fix_induced: false, component: settled-history-reader, disposition: fixed}
  - {id: R2, severity: Medium, aim: deliverable, fix_induced: false, component: settled-history-reader, disposition: fixed}
  - {id: R3, severity: Medium, aim: deliverable, fix_induced: false, component: settled-history-reader, disposition: fixed}
  - {id: R4, severity: Low, aim: deliverable, fix_induced: false, component: settled-prose-clause, disposition: fixed}
  - {id: R5, severity: Low, aim: deliverable, fix_induced: false, component: settled-flag-message, disposition: fixed}
  - {id: F1, severity: Medium, aim: instrument, fix_induced: false, component: settled-history-reader, disposition: fixed}
  - {id: F2, severity: Medium, aim: instrument, fix_induced: false, component: settled-history-reader, disposition: fixed}
  - {id: F3, severity: Medium, aim: deliverable, fix_induced: false, component: settled-history-reader, disposition: fixed}
  - {id: F4, severity: Low, aim: deliverable, fix_induced: false, component: settled-history-reader, disposition: fixed}
  - {id: F5, severity: Low, aim: deliverable, fix_induced: false, component: settled-history-reader, disposition: fixed}
  - {id: F6, severity: Low, aim: instrument, fix_induced: false, component: settled-prose-clause, disposition: fixed}
  - {id: F7, severity: Low, aim: deliverable, fix_induced: false, component: settled-flag-message, disposition: fixed}
```

**Subject:** `git diff origin/master...HEAD` on `needs-owner-settled` (PR #528, backlog #496), both halves on `435ef151`.
**Halves:** `codex/needs-owner-settled-r1-codex.md` (R1-R3 Medium, R4-R5 Low, model `gpt-6.1-sol`) ·
`claude/needs-owner-settled-r1-claude.md` (F1-F3 Medium, F4-F7 Low). Both NOT CONVERGED. No finding is fix_induced:
this is the first round.

**One root, both halves.** Clause 2's reader was `git log --reverse -S<segment> -- docs/backlog.md`, then
`git show` of the oldest hit. The pickaxe is file-wide and counts occurrences, so it knew neither WHICH row (R1) nor
WHICH introduction (R2). It ran two git calls per listed row (F3). The shallow clone (R3, F4) and the empty answer
both fell through to "unchanged". Fixing each of these alone would have kept the pickaxe and added a guard per
symptom. So the reader is replaced.

**The new reader** (`scripts/goal-tree.py`: `backlog_commits`, `status_cell`, `head_when_marked`,
`git_head_when_marked`):
- `backlog_commits` first runs `git rev-parse --is-shallow-repository`. Anything but `false` is NOT READ.
- It then runs ONE `git log --first-parent --diff-merges=first-parent -p -U0 -- docs/backlog.md`. Every commit
  becomes (sha, rows before, rows after), newest first. A row is a line `gen-backlog-page.ROW` matches, and the
  lines are keyed by item number.
- A git failure is NOT READ, and so is a log with no commit.
- `head_when_marked(commits, num, segment)` walks newest-first. It returns the status head of the NEWEST commit
  where row `num`'s status holds the segment and the parent's row status does not. Another row's identical text is
  never read. A removed-then-renewed marker compares against its renewal.
- If no commit introduced the marker (for example, it is uncommitted), that is NOT READ.
- The status is the line's last cell. A line without one is NOT READ.
- `git_head_when_marked` reads the commits once, on the first row that asks. It memoises per (row, marker), and
  memoises failures too.
- `head_moved_on` treats a `None` answer as NOT READ. It is never "unchanged".

**Dispositions.**
- **R1 (Codex Medium): fixed.** The history is keyed by item number. Case: row 8 later carries row 5's exact marker
  text under today's head. Row 5 is still flagged and row 8 is not. Mutation "the lookup reads any row holding the
  marker text" is killed.
- **R2 (Codex Medium): fixed.** The walk is newest-first and requires the parent's row to lack the segment. Case: an
  ask is removed, then renewed under `NEW OPEN QUESTION`, and it is not flagged. Mutation `reversed(commits)` is killed.
- **R3 (Codex Medium) and F4 (Claude Low): fixed.** A depth-1 `git clone` of a real repository now reads `its history
  was NOT READ (the repository is shallow, …)`. Codex's "empty successful history" half has its own case: a repository
  with no backlog commit is NOT READ.
- **R4 (Codex Low): fixed.** `NEGATED` (`not`/`never`, optionally `yet`, right before the word) skips that match.
  Four adjacent cases cover it:
  - `not DECIDED` does not flag;
  - `not yet answered by the owner` does not flag;
  - a `not` far before the word does not negate it;
  - a negated word does not hide a later un-negated one.

  Each case has its own mutation.
- **R5 (Codex Low) and F7 (Claude Low): fixed, as a message and a bound, never by reading the edit.** Clause 2's flag
  now ends "…or restate the question as a new `NEEDS-OWNER` marker if it is still open". Restating moves the
  introduction to a commit whose head is today's. The comment block states that an unrelated head edit is a known
  false positive the heuristic flags and never hides.
- **F1 (Claude Medium): fixed.** Each failure is now a case over REAL git:
  - a `.git` pointing nowhere gives `git rev-parse exited 128`;
  - an unborn repository gives `git log exited 128`;
  - an empty history, a no-status-cell row and a never-introduced marker are each NOT READ.

  All of these run inside `fixture_git.isolated()`. Each assertion names the call, so a mutation that turns one
  failure into a different NOT READ is still red.
- **F2 (Claude Medium): fixed.** Three real-git cases, each killing a named mutation:
  - an unchanged head (with a later tail edit) is not flagged. This kills Claude's mutation E, which returns the whole
    status.
  - the last marker's segment is the one looked up (mutation G, `find`).
  - a newer `docs/other.md` row with the same text is not read (mutation F, the `-- docs/backlog.md` filter).
- **F3 (Claude Medium): fixed.** Measured by `needs_from_backlog` with the real reader on `d678369d` (10-27, 28 waiting
  rows). It took **20.5 s** before and takes **0.71 s** after. `1b4b74d3` (10-26, 28 rows) takes 0.60 s. A case pins
  the cost: two rows asking three times make exactly `rev-parse` + `log` and one lookup per (row, marker).
- **F5 (Claude Low): fixed by design and stated.** Today's `parse` is no longer applied to history. Only the row's
  last cell is read. A line without one is NOT READ, and stays so while that marker stands. Restating the marker
  moves the read. Mutation I's path (the row absent at the marker commit) no longer exists. A row absent from every
  commit is the never-introduced NOT READ case.
- **F6 (Claude Low): fixed.** Case: `DECIDED by the owner, as backlog #11 recorded` keeps clause 1's own text, not
  "may already be answered by backlog #11". Mutation C is killed.

**Measured, not recalled.**
- **11-03 corpus (`11a70deb`), real git:**
  - backlog #306 is flagged by clause 1 and backlog #384 by clause 2;
  - backlog #2, backlog #86, backlog #198 and backlog #307 are listed and unflagged.

  That is 2/2 hits and 0 false positives, in 0.90 s.
- **Daily revisions (last backlog commit per day, 10-23..11-06, plus `11a70deb`):** 16 revisions and 130 listed
  row-revisions. There are 18 flags:
  - backlog #90 ×5, backlog #194 ×5 and backlog #306 ×6, all from clause 1;
  - backlog #384 ×2, from clause 2.

  All are settled, and 0 are NOT READ. That is the same 18 as the build.
- **Every backlog commit since 10-23 (115 revisions, 1131 listed row-revisions):**
  - clause 2 fired only on backlog #384 (15 revisions);
  - clause 1 fired on backlog #90 (43), backlog #194 (43) and backlog #306 (47);
  - 0 NOT READ.

  This matches the Claude half's own dense measurement.
- **Suite.** `--self-test` went from 430 to 450 cases.
- **Mutations.** 2 `-S`-specific entries were retired, 3 were re-anchored and 20 were added, so the pin moves
  329 → 347. Run on a scratch copy that holds only the 31 backlog #496 entries:
  `check-plan-code.py --mutate . --only scripts/goal-tree.py --allow-long-local`. Result: **31 mutations, 31 killed, 31 attributed to the case each names, 0 survivors** (a diagnostic slice; CI runs the full sweep).

**Not covered.** No case has a merge commit, so `--first-parent` / `--diff-merges=first-parent` carry no mutation.
On this repository's squash-merged master the two readings agree.
