# Round 3 — `agenda-row-state` — coordinator — NOT CONVERGED (Claude), folded; Phase 6 convened

Round 3 ran ONE half by alternation: Claude (`docs/reviews/claude/agenda-row-state-r3-claude.md`), reviewing `b1e98095`
(the r2 fold). The Codex half is a gap by alternation.

REVIEW GAP: codex — alternation.

Claude found 3 MINOR (F1, F2, F3). There was no BLOCKER. **All three were caused by the r2 fold**, one in each of the
components round 2 named. In `backlog-closed-rule`, round 2's m1 came from round 1's C2 fix and round 3's F1 came from
m1's fix: two consecutive fix-caused rounds in one component. **That is THRASHING, so Phase 6 is convened:**
[`../architecture-review-2026-11-20-backlog-closed-rule.md`](../architecture-review-2026-11-20-backlog-closed-rule.md).
Its answer to *can a redesign remove it?* is yes: the Status cell is written newest-first, so only its first mark is
state, and the fold reverts to the rule that reads it that way. F2 and F3 are fix-caused too, but neither is a rule
fighting a grammar (a stated precedence trade and a one-day docstring slip), so they do not arm Phase 6 on their own
components.

| Id | Severity | Finding | Reproduced at `b1e98095` | Disposition |
|---|---|---|---|---|
| F1 | MINOR | the r2 closing-word clause ignores position, so a reopened row that keeps its old closure in the history reads closed | `🟠 **REOPENED 2026-11-07** — …; previously ✅ CLOSED 2026-10-24` under sev `none`: `True` (and the review's four other inputs) | **fixed by REVERT** (Phase 6): the r2 clause (`CLOSING_WORD_RE`) is removed, and the rule is round 1's again: closed when the FIRST status mark is ✅, or the Item cell is ✅. The `status_closed` docstring now says why (newest-first grammar) and states the bound below. r2 m1 is therefore **REJECTED**, with its measurement: 0 of 636 live rows and 0 of 352 parsed historical versions differ. Its cure is to write the closure first. Case `⭐ r3 Phase 6: only the FIRST status mark is state …`: F1's five inputs and the r2 m1 row read OPEN, and the closure-first form reads closed. One mutation (the LAST mark read as state, `reversed(status)`). The r2 cases (`⭐ r2 Codex m1`, `r2 Codex m1: the parser…`) and their three mutations are removed. The C2 case's sev-only input (`🟠 **OPEN** — … ✅ landed`, `done`) was added in r2 only because the clause masked the Item-cell mutation through the `✅ **FIXED`** input. With the clause gone that input kills it again, so the sev-only input is removed and the C2 case is back to its round-1 form. Killed in the subset run below |
| F2 | MINOR | an open PR that only MENTIONS a ✅ row holds the step at ⏳, and the step then disagrees with the tree leaf | row 10 ✅, PR #41 open titled `File backlog #700, … after backlog #10`: step `open`, leaf `merged` | **STATED LIMIT, no code change.** Written in the comment at `cells_held` in `scripts/goal-tree.py`. Why: in the house flow the ✅ is ticked ON the PR branch before the PR opens, and the tree reads `docs/backlog.md` from its own checkout, so a ✅ row whose PR is still open SHOULD read ⏳. A title match cannot tell that PR from one that only mentions the row, and the narrowing `and not hit` would show a second slice ✅ once its first slice merged. The cost is asymmetric: a stale hold costs a glance (the detail says the ✅ is in the cell and names the PR), and a false ✅ hides open work |
| F3 | MINOR | the `wait_expired` docstring says the window is 245 days back; it is 244, and a date 245 days back is already next year's | `wait_expired("re-check 03-20", "2026-11-20 12:00")` → `None` | **fixed**: the docstring says "the 244 days before today and the 120 after", names the boundary (03-20 read on 11-20 is exactly 120 days ahead, so next year's; 03-21 is 244 back, this year's), and the bound says "one 245 or more days past". Case `r3 F3: the window's edges read on 11-20 …` (`2026-03-21`, `None`). One mutation (`<=` → `<` on the ahead test) |

## F1 — the measurement over `docs/backlog.md`

The old rule is `status_closed` at `b1e98095`; the new rule is this fold's. Both were run through `parse`:

- **Live file: 636 rows. 229 closed under `b1e98095`, 229 under this fold. Rows that differ: none.**
- **History:** every version from `git log -- docs/backlog.md`, 377 versions, 352 of which parse to rows. **0 versions
  have a row that differs.**

So the revert changes nothing that is on disk today or ever was. What it changes is the reading of rows not yet
written, and there the newest-first grammar is the one every live row follows.

## Mutations

gen-backlog-page 84 → 82: the r2 clause's three entries removed, one new (`r3 Phase 6: the LAST status mark is read as
the row's state`). goal-tree 501 → 502: one new (`r3 F3: a date exactly WAIT_AHEAD_DAYS ahead is out of reach`).
No entry was re-anchored. `expected_mutations.py` pins both counts.

The new entries, with the entries beside them on the same rule, were run ONLY in a scratch copy of the repo
(`611fold3/repo`) with manifests holding just those entries (and their pins set to match, in the copy only):

- gen-backlog-page (5: the 4 r1 C2 entries + r3 Phase 6): `OK — delivered scripts mutated: 1 file(s), 5 mutation(s), 5 killed, 5 attributed to the case each names, 0 survivor(s) — measured over ONLY scripts/gen-backlog-page.py — a DIAGNOSTIC slice, not the gate`
- goal-tree (6: 4 r1 C5 + r2 m2 + r3 F3): `OK — delivered scripts mutated: 1 file(s), 6 mutation(s), 6 killed, 6 attributed to the case each names, 0 survivor(s) — measured over ONLY scripts/goal-tree.py — a DIAGNOSTIC slice, not the gate`

This is a diagnostic slice. The full manifests run in CI.

## Results at the fold

- `python3 scripts/goal-tree.py --self-test` → `582/582 self-test cases passed`
- `python3 scripts/gen-backlog-page.py --self-test` → `250/250 passed`
- `python3 scripts/check-docs.py` → `Documentation integrity OK`
- `python3 scripts/check-features.py` → `feature map: 35 nodes (31 built, 4 declared absent); 15 anchors and 29 backlog areas all claimed exactly once`
- `python3 scripts/check-reference-namespace.py --base origin/master` → `reference namespaces OK — no bare `#N` added in 14 reader-facing surface(s)`
- `python3 scripts/check-fixture-variation.py scripts/goal-tree.py` → `fixture variation OK — 127 parameter(s) examined across 1 file(s); 105 known-unvaried ratcheted, 71 exempt with a written reason`
- `python3 scripts/check-fixture-variation.py scripts/gen-backlog-page.py` → `fixture variation OK — 55 parameter(s) examined across 1 file(s); 105 known-unvaried ratcheted, 71 exempt with a written reason`
- `python3 scripts/check-arch-findings.py` → `2/18 criteria met; 0 regressed past baseline` (the 2026-07-30 ratchet; this Phase 6 note adds no metric to it)

## Decision log

The r2 fold's row is now written to `docs/reviews/decision-scheme/decision-log.jsonl`, retroactively, in the form the
r1 row used. Its prediction "r3 finds nothing caused by the r2 fold" LOST. This fold's own row is owed after round 4.

```yaml
round: 3
fixes_nontrivial: true
subject: agenda-row-state
halves:
  claude: ran
  codex: gap-alternation
findings:
  - {id: F1, severity: Minor, aim: deliverable, fix_induced: true, component: backlog-closed-rule, disposition: fixed}
  - {id: F2, severity: Minor, aim: deliverable, fix_induced: true, component: agenda-step-state, disposition: rejected}
  - {id: F3, severity: Minor, aim: deliverable, fix_induced: true, component: wait-date-parse, disposition: fixed}
```

F2's `rejected` means "kept as a stated limit": the behaviour is deliberate and is now written at its site. Round 4
runs ONE half (alternation): Codex, on this fold. Under the round cap, its findings are FILED unless a BLOCKER.
