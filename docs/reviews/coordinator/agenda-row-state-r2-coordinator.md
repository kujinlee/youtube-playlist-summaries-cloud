# Round 2 — `agenda-row-state` — coordinator — NOT CONVERGED (Codex), folded

Round 2 ran ONE half by alternation: Codex (`docs/reviews/codex/agenda-row-state-r2-codex.md`), reviewing `81874196`
(the r1 fold `5e182173` plus a master merge). The Claude half is a gap by alternation.

REVIEW GAP: claude — alternation.

Codex found 1 MAJOR (M1) and 2 MINOR (m1, m2). There was no BLOCKER. **All three were caused by the r1 fold**, each in a
different component: M1 by C7's all-✅ shortcut, m1 by C2's narrowing, and m2 by C5's 92-day window. This is the first
fix-induced round. Phase 6 arms on two consecutive fix-induced rounds in one component, so it fires only if round 3
finds another fix-induced finding in `agenda-step-state`, `backlog-closed-rule` or `wait-date-parse`.

Every finding was reproduced at `81874196` before it was touched. Each fix has a case that goes red without it, and a
mutation the case kills.

| Id | Severity | Finding | Reproduced at `81874196` | Disposition |
|---|---|---|---|---|
| M1 | MAJOR | with the merge log unread, the all-✅ shortcut (`by_cells`) reads a step ✅ although an OPEN PR names its row | closed row 10, open PR #41 `fix (backlog #10)`, `errors["merged"]` set: `merged`. With the log read it was `merged` too | **fixed**: `cells_held = by_cells and bool(opened)`. An open PR naming a row outranks the row's ✅ whether or not the merge log was read: the step reads ⏳ `open` (`backlog #10 ✅ in its Status cell, but an open PR names it · PR #41 open …`), never ✅ and never CANNOT RUN. With no open PR, a closed row still reads ✅ when the log is unread (C7 kept). Case `⭐ r2 Codex M1`, which covers the exact input, the same input with the log read, and the no-PR control. One mutation (`cells_held = False`) |
| m1 | MINOR | `| 900 | **Fix** | 🟢 FILED 2026-01-01; ✅ FIXED 2026-02-01 |` reads OPEN under C2's narrowing | confirmed: `closed=False` | **fixed**: a ✅ written directly before a closing word in CAPITALS (FIXED, CLOSED, SUPERSEDED, MERGED, DONE; bold and a `(was …)` may sit between) closes the row wherever it stands (`CLOSING_WORD_RE`). The match is case-sensitive on purpose: a finished half is written `(1)-(4) ✅ merged in PR #509` in lower case, and that row stays open. Measured below: no live row changes. Cases `⭐ r2 Codex m1` (`status_closed`) and `r2 Codex m1: the parser…` (the exact row, plus a lower-case half that stays open). The C2 case gains a sev-only input (`✅ landed` under a ✅ Item cell), because the new clause would otherwise mask its Item-cell mutation. Three mutations: clause removed, any case (`(?i)`), no word boundary |
| m2 | MINOR | `04-04` read on 2026-01-01 is 93 days ahead, but the 92-day window reads it as 2025-04-04 and flags a future wait | confirmed: `2025-04-04` | **fixed, with the window widened, not replaced**: `WAIT_AHEAD_DAYS` 92 → 120, so the window is 245 days back to 120 ahead. The suggested nearest-year (±6 months) rule cannot satisfy C5. Read on 11-20, `05-20` is 184 days back as 2026-05-20 and 181 days ahead as 2027-05-20, so "nearest" picks next May and never flags, which is exactly the bug C5 fixed. Any window from 93 to 180 days satisfies both inputs. 180 would leave C5 one day from its edge (`05-19` read on 11-20 would be next year's), so 120 (about four months) leaves margin on both sides. The window leans to the past on purpose: a wrong flag only says "re-check it", and a written year cures it, while a missed flag hides a stale wait. The bound is in the docstring: a yearless date more than 120 days ahead flags early, and one more than 245 days past never flags. Case `⭐ r2 Codex m2`: 04-04 and 04-30 read on 01-01 are not expired, 05-02 is last year's, and 05-20 read on 11-20 is still this May's. The C5 case's 02-25 input (which pinned 92) is now 03-25. One new mutation (120 → 92); the ~six-months mutation (→ 182) is re-anchored on `120` |

## m1 — the measurement over `docs/backlog.md`

The old rule is `status_closed` at `81874196`; the new rule is this fold's. Both were run through `parse` over the
live file:

- **636 rows. 229 closed under the old rule, 229 under the new. Rows that differ: none.**
- The pre-r1 rule (any ✅ in the Status cell) also gives 229. Every live row that holds a ✅ is already closed, so a
  clause that can only close more rows cannot flip a live one.
- The closing-word clause alone matches 201 live rows. The words after a ✅ in the corpus are CLOSED 74, DONE 74,
  FIXED 38, `built` 12, MERGED 9, SUPERSEDED 6, RESOLVED 4, and fewer than 4 of anything else. RESOLVED is left out, to
  keep to the five words the finding named; it closes no live row that is not already closed.
- 15 live rows open with an open marker before their ✅ (78, 152, 174, 189, 213, 218, 253, 255, 301, 305, 312, 350,
  351, 354 and 619). All have a ✅ Item cell, so they were closed before and are closed now.

## Mutations

New: goal-tree 499 → 501 (2) and gen-backlog-page 81 → 84 (3). Re-anchored: the C5 ~six-months entry
(`WAIT_AHEAD_DAYS = 120 `), plus the expected case name of the four C5 entries (03-25 replaced 02-25).
`expected_mutations.py` pins both counts.

The first subset run refused `r2 Codex m2` with "repeats the edit anchors of an earlier entry", because it shared
`WAIT_AHEAD_DAYS = 120 ` with the ~six-months entry. It is now anchored on `WAIT_AHEAD_DAYS = 120    # r1 C5`.

The new and re-anchored entries, together with the r1 entries they sit beside, were run ONLY in a scratch copy of the
repo (`611fold2/repo`) with manifests that hold just those entries:

- gen-backlog-page (7: 4 r1 C2 + 3 r2): `OK — delivered scripts mutated: 1 file(s), 7 mutation(s), 7 killed, 7 attributed to the case each names, 0 survivor(s) — measured over ONLY scripts/gen-backlog-page.py — a DIAGNOSTIC slice, not the gate`
- goal-tree (6: 4 r1 C5 + r2 m2 + r2 M1): `OK — delivered scripts mutated: 1 file(s), 6 mutation(s), 6 killed, 6 attributed to the case each names, 0 survivor(s) — measured over ONLY scripts/goal-tree.py — a DIAGNOSTIC slice, not the gate`

This is a diagnostic slice. The full manifests run in CI.

## Results at the fold

- `python3 scripts/goal-tree.py --self-test` → `581/581 self-test cases passed`
- `python3 scripts/gen-backlog-page.py --self-test` → `251/251 passed`
- `python3 scripts/check-docs.py` → `Documentation integrity OK`
- `python3 scripts/check-features.py` → `feature map: 35 nodes (31 built, 4 declared absent); 15 anchors and 29 backlog areas all claimed exactly once`
- `python3 scripts/check-reference-namespace.py --base origin/master` → `reference namespaces OK — no bare `#N` added in 14 reader-facing surface(s)`
- `python3 scripts/check-fixture-variation.py scripts/goal-tree.py` → `fixture variation OK — 127 parameter(s) examined across 1 file(s); 105 known-unvaried ratcheted, 71 exempt with a written reason`
- `python3 scripts/check-fixture-variation.py scripts/gen-backlog-page.py` → `fixture variation OK — 55 parameter(s) examined across 1 file(s); 105 known-unvaried ratcheted, 71 exempt with a written reason`

## Decision log

The r1 fold's row is now written to `docs/reviews/decision-scheme/decision-log.jsonl`. It is retroactive, written after
r2's result, in the form `running-now-worktree` and `hse-slice-e` use. Its prediction "r2 finds nothing caused by the r1
fold" LOST. This fold's own row is owed after round 3.

```yaml
round: 2
fixes_nontrivial: true
subject: agenda-row-state
halves:
  codex: ran
  claude: gap-alternation
findings:
  - {id: M1, severity: Major, aim: deliverable, fix_induced: true, component: agenda-step-state, disposition: fixed}
  - {id: m1, severity: Minor, aim: deliverable, fix_induced: true, component: backlog-closed-rule, disposition: fixed}
  - {id: m2, severity: Minor, aim: deliverable, fix_induced: true, component: wait-date-parse, disposition: fixed}
```

Round 3 runs ONE half (alternation): Claude, on this fold.
