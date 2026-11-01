# Round 1 — `review-round-cap` — coordinator — NOT CONVERGED (both halves); every finding FIXED, one bound FILED

**Round cap, pre-committed before any finding (this PR's own §0 Q4c):** r1 both halves; r2 and r3 one half each,
alternating; from r4 findings are FILED unless a BLOCKER, and r5 only re-checks a r4 BLOCKER fix.

```yaml
round: 1
fixes_nontrivial: true
subject: review-round-cap
halves:
  codex: ran
  claude: ran
findings:
  - {id: C-H1, severity: High, aim: deliverable, fix_induced: false, component: recorded-overlay, disposition: fixed}
  - {id: X-H2, severity: High, aim: deliverable, fix_induced: false, component: recorded-overlay, disposition: fixed}
  - {id: C-M1, severity: Medium, aim: deliverable, fix_induced: false, component: head-declaration, disposition: fixed}
  - {id: X-H1, severity: High, aim: deliverable, fix_induced: false, component: head-declaration, disposition: fixed}
  - {id: C-M1b, severity: Medium, aim: deliverable, fix_induced: false, component: verdict-word, disposition: fixed}
  - {id: C-M2, severity: Medium, aim: deliverable, fix_induced: false, component: blocker-definition, disposition: fixed}
  - {id: X-M3, severity: Medium, aim: deliverable, fix_induced: false, component: blocker-definition, disposition: fixed}
  - {id: C-M3, severity: Medium, aim: deliverable, fix_induced: false, component: round-3-fold, disposition: fixed}
  - {id: X-M2, severity: Medium, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: C-L1, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: C-L2, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: C-L3, severity: Low, aim: deliverable, fix_induced: false, component: symlink, disposition: fixed}
  - {id: X-M1, severity: Medium, aim: deliverable, fix_induced: false, component: symlink, disposition: fixed}
  - {id: C-H1-bound, severity: Medium, aim: deliverable, fix_induced: false, component: recorded-overlay, disposition: filed}
```

Both halves on `45858d37`. C = Claude half (`docs/reviews/claude/review-round-cap-r1-claude.md`), X = Codex half
(`docs/reviews/codex/review-round-cap-r1-codex.md`). The halves agree on the core: the producer ASSERTED a clean
overlay it never observed, and accepted any hex token as "naming" the head.

## Dispositions

- **C-H1 / X-H2 — fixed.** `main` now reads `codex-review.reviewed_state(root)`, refuses `TREE MOVED` unless its
  HEAD equals the resolved `--head`, and records the observed overlay unchanged (`None` stays `None`). The Claude
  half's repro (`scratchpad/r457/repro.py`, given a `## Verdict` heading) went from gate rc 0 to gate rc 1.
- **C-M1 / X-H1 — fixed.** The review must carry a `Reviewed head <sha>` line of its own. The regex is anchored at
  the line start, so a `>` quote never matches, and fenced lines are skipped. Every sha on that line must resolve
  through `git rev-parse` to the head, which refuses an ambiguous abbreviation. X-H1's "another subject's
  namespace" needs no separate rule: the id IS the review's filename, and that file must declare the head. "Edited
  after the fact" is the stated bound the Codex record shares.
- **C-M1b — fixed.** The verdict is the first written line under every `Verdict` heading, matched at its start
  (`NOT CONVERGED` / `CONVERGED`). Prose, a bare word, or two headings that disagree give no verdict. The parsed
  word is recorded as `verdict`. No other script parses a review's verdict word (grep `CONVERGED` over
  `scripts/*.py`: only record-review-verdict and codex-review fixtures), so this is the one rule.
- **C-M2 / X-M3 — fixed.** BLOCKER is now three checkable tests: a concrete input under which the merged PR gives a
  false green, data loss or a security hole; the reviewer ran it and quotes the result; and the fix is local. The
  chain is bounded: r4 runs only when r3's fold changed a guarded path, r5 only to re-check a r4 BLOCKER fix, every
  r5 finding is filed (a BLOCKER is also notified), and there is no r6.
- **C-M3 — fixed.** With C-H1 fixed, Q4(b) answer 2 works with either half. Q4c says to record before any commit,
  and r4 is named as the tree-identity round for a r3 fold of guarded code.
- **X-M2 / C-L1 / C-L2 — fixed.** `process-checklists.md:18,26` and `dev-process.md:23` point to Q4c, and the
  checklist's "cannot converge → WAIT" now FILES at r3. `plugins.md:119`'s "because" is back on alternation.
  `plugins.md` and *Round topology* step 4 no longer call alternation undecided: backlog #339 records the owner's
  decision of 2026-10-28 (one half per round).
- **C-L3 / X-M1 — fixed.** `link_problem` refuses a review or verdict path that resolves through any symlink,
  including a linked `verdicts/` directory. The overwrite test uses `lexists`.
- **C-H1-bound — FILED as backlog #435** (a new mechanism, §0 Q3). The overlay is observed at RECORD time.
  Measured after the fold: revert the reviewed fix BEFORE recording, and the gate still passes with `BAD`.

## Evidence

- `record-review-verdict.py --self-test`: 10 new end-to-end cases red against `45858d37`'s code (48/58), then 74/74.
- `check-plan-code.py --mutate . --only scripts/record-review-verdict.py --allow-long-local`: 19 mutations, 19
  killed, 19 attributed, 0 survivors. Pin 10 → 19. Four entries were retargeted onto the rewritten clauses. Nine
  were added, one per new refusal or record field.
