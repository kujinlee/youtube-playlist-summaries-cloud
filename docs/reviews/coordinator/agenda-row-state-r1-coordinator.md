# Round 1 — `agenda-row-state` — coordinator — NOT CONVERGED (both halves), folded

Both halves reviewed `f51dcf95..2247577c` (PR #611; backlog #515, #611, #612: an agenda step naming a backlog row
follows the row's Status cell, and a passed declared wait is flagged expired).
Codex (`docs/reviews/codex/agenda-row-state-r1-codex.md`): 1 MINOR (X1). Claude
(`docs/reviews/claude/agenda-row-state-r1-claude.md`): 8 MINOR (C1-C8). No BLOCKER, no MAJOR. The fold also
closes backlog row 672, whose work merged in PR #606 while its Status cell still said `PR pending`.

Every finding was reproduced at `2247577c` before it was touched (scratch `611fold/probe.py`). Each fix has a
self-test case that goes red without it, and a mutation that the case kills.

| Id | Severity | Finding | Reproduced at `2247577c` | Disposition |
|---|---|---|---|---|
| X1 | MINOR | no case tells "every live row closed" from "any live row closed" on a two-row step | the code was right (one closed + one open read `next`), but a hand mutant to ANY survived the suite | **case added**: rows `[closed, open]`, `[open, closed]`, `[open, open]` read `next`; `[closed, closed]` reads `merged`. Mutation `r1 Codex X1` |
| C1 | MINOR | the context line names a merged PR that named a CLOSED row, as if it explained the OPEN one | step on rows 10 (✅) and 12 (open), PR #20 merged naming row 10 only: the line said `PR #20 … merged` against row 12 | **fixed**: the context PR is the first merged PR naming an OPEN row, and the line says which rows it named (`PR #N (sha) merged naming backlog #12`); when none did it says `no merged PR names it` / `them`. Two mutations |
| C2 | MINOR | `closed=("✅" in status)` reads a PARTLY-DONE cell (`🟡 … items (1)-(4) ✅ … item (5) open`) as closed | the PARTLY-DONE cell parsed `closed=True` | **fixed** in `gen-backlog-page.status_closed`: a Status cell is closed when it holds a ✅ and its FIRST status mark (✅ or one of 🔴🟠🟡🟢⏳) is the ✅ — or when the Item cell is ✅ (`sev == "done"`). Four mutations. Impact below |
| C3 | MINOR | an expired declared wait still keeps an open PR out of Running now | confirmed: the item stays OWED with the `❌ expired` flag | **rejected — deliberate.** Owner card A defines RUNNING as an open PR that nothing declares a wait on; an expired wait is still DECLARED until someone rewrites it. And OWED is where the flag is SHOWN: a Running item renders no `waits`, so moving it would hide the very flag. A comment at the `_join_waits` call in `agenda_digest` now says so |
| C4 | MINOR | `WAIT_DATE_RE` reads tokens like `v11-06`, `x11-06`, `1.11-06`, `#11-06` as dates | all four read `2026-11-06` | **fixed**: the lookbehind is `(?<![\w.#-])`, so a date needs a boundary before it; `(11-06)` and `11-06 reset` still read. Two mutations (letter, dot); the `#` mutation is rebound |
| C5 | MINOR | a yearless `MM-DD` more than ~six months old is read as NEXT year and never flags | `05-20` read on 11-20 gave `None` | **fixed**: a yearless date takes the LATEST year no more than `WAIT_AHEAD_DAYS` (92) after today, so `05-20` on 2026-11-20 is 2026-05-20, expired. A written year is never moved. Bound, in the docstring: a wait declared more than 92 days ahead without a year is misread as last year's. Four mutations |
| C6 | MINOR | expiry is by DAY, so a wait for a time earlier today stays unexpired until midnight | confirmed | **rejected — deliberate.** The `wait_expired` docstring states it: "naming one today or later … is not expired". Waits carry dates, not times; a same-day flag would need a clock-time grammar the declarations do not have |
| C7 | MINOR | an all-✅ step reads CANNOT RUN when `git` or `gh` failed | all-✅ step with `errors["merged"]` set read `cannot` | **fixed** (trivial): when every live row is closed by its Status cell the step is done whatever the merge read did, and the line adds `the merge was not read (…)`; a step with an open row still reads `cannot`. Two mutations |
| C8 | MINOR | a row named twice in one step is printed twice | `backlog #10 … backlog #10` printed `#10, #10` | **fixed**: the step's rows are de-duplicated in order (`dict.fromkeys`). One mutation |
| row 672 | — | backlog row 672's Status cell said `⏳ BUILT 2026-11-20, PR pending` after its PR merged | `gh pr view 606`: MERGED 2026-11-20T21:19:00Z, merge commit `7e4036e5`, an ancestor of HEAD | **updated**: Status `✅ (was ⏳) MERGED 2026-11-20 — PR #606, squash 7e4036e5`; Item cell `✅ (was 🟡)`, which `check-docs`' marker ratchet requires of a closed row |

## C2 — what else the new closed rule touches

`parse`'s `closed` field is read by: the backlog page (open/closed sections and counts), goal-tree's `closed_rows` and
`_blocker`, `check-features.py`, `gen-features-page.py` and `check-reference-namespace.py`.

- **Live corpus, measured on this branch:** 636 rows parsed; 228 closed under the old rule, 228 under the new;
  **no row changes reading**; `contradiction_errors` is empty. So today every consumer reads the same corpus as before.
- **The rule as briefed was wrong on the corpus.** "✅ before any 🟡/⏳/🔴" alone would have REOPENED eight genuinely
  closed rows — 152, 174, 189, 213, 218, 255, 305 and 312. Each has a Status cell that opens with `🟠/🟡/🔴 OPEN …`
  and records a later `✅ FIXED / CLOSED / SUPERSEDED`, under an Item cell of `✅ (was …)`. The Item-cell exemption
  (`sev == "done"`) keeps them closed; a case pins one of that shape.
- **Overlap with an existing ratchet.** `check-docs.py`'s `backlog_marker_errors` already refuses a ✅ Status under an
  Item cell led by a bare severity marker, so the C2 example fails `check-docs` whenever its Item cell carries one.
  The new rule covers the remaining shape: an Item cell with no marker at all.

## Mutations

New: goal-tree 487 → 499 (12), gen-backlog-page 77 → 81 (4). Rebound: three goal-tree entries whose anchors the fold
moved — `backlog #611` (now `        if by_cells:`), `backlog #612` (the `#` in the new lookbehind) and `the backlog match
drops its parentheses` (the regex now occurs three times; anchored with its context). Every anchor resolves exactly once;
`expected_mutations.py` pins both counts. Run ONLY those 15 + 4 entries, in a scratch copy of the repo
(`611fold/repo`) with a manifest holding just them:

- goal-tree (15): `OK — delivered scripts mutated: 1 file(s), 15 mutation(s), 15 killed, 15 attributed to the case each names, 0 survivor(s) — measured over ONLY scripts/goal-tree.py — a DIAGNOSTIC slice, not the gate`
- gen-backlog-page (4): `OK — delivered scripts mutated: 1 file(s), 4 mutation(s), 4 killed, 4 attributed to the case each names, 0 survivor(s) — measured over ONLY scripts/gen-backlog-page.py — a DIAGNOSTIC slice, not the gate`

The first subset run refused three entries as `repeats the edit anchors of an earlier entry`: the two C4 entries and
the C2 Item-cell entry first shared anchors with an existing one. Each was re-anchored on a distinct literal before
the run above. This is a diagnostic slice; the full manifests run in CI.

## Results at the fold commit

- `python3 scripts/goal-tree.py --self-test` → `579/579 self-test cases passed`
- `python3 scripts/gen-backlog-page.py --self-test` → `249/249 passed`
- `python3 scripts/check-features.py` → `feature map: 35 nodes (31 built, 4 declared absent); 15 anchors and 29 backlog areas all claimed exactly once`
- `python3 scripts/check-docs.py` → `Documentation integrity OK`
- `python3 scripts/check-reference-namespace.py --base origin/master` → `reference namespaces OK — no bare `#N` added in 14 reader-facing surface(s)`
- `python3 scripts/check-fixture-variation.py scripts/goal-tree.py` → `fixture variation OK — 127 parameter(s) examined across 1 file(s); 105 known-unvaried ratcheted, 71 exempt with a written reason`
- `python3 scripts/check-fixture-variation.py` (whole repo) → `fixture variation OK — 2480 parameter(s) examined across 110 file(s); …`. Its first
  run on `gen-backlog-page.py` refused `status_closed(status=…)` and `(sev=…)` as passed one value at every call site
  (the case looped one call); the case now calls it once per row.
- Every other `python3 scripts/check-*` step in `.github/workflows/*.yml` that runs without a live stack or a jest
  result file: 38 of 38 rc=0. Not run locally: `check-live-schema --prod`, `check-test-counts`, `check-selftest-counts`,
  `check-page-links --build`.

## Decision log

None this round. The earlier subjects (`running-now-worktree`, `hse-slice-e`, `rm-backup`) write a fold's row
RETROACTIVELY, after the NEXT round's result ("Written after r2's result, so retroactive"). This fold's row is owed after
round 2.

```yaml
round: 1
fixes_nontrivial: true
subject: agenda-row-state
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Minor, aim: harness, fix_induced: false, component: goal-tree-cases, disposition: fixed}
  - {id: C1, severity: Minor, aim: deliverable, fix_induced: false, component: agenda-step-context, disposition: fixed}
  - {id: C2, severity: Minor, aim: deliverable, fix_induced: false, component: backlog-closed-rule, disposition: fixed}
  - {id: C3, severity: Minor, aim: deliverable, fix_induced: false, component: running-line, disposition: rejected}
  - {id: C4, severity: Minor, aim: deliverable, fix_induced: false, component: wait-date-parse, disposition: fixed}
  - {id: C5, severity: Minor, aim: deliverable, fix_induced: false, component: wait-date-parse, disposition: fixed}
  - {id: C6, severity: Minor, aim: deliverable, fix_induced: false, component: wait-date-parse, disposition: rejected}
  - {id: C7, severity: Minor, aim: deliverable, fix_induced: false, component: agenda-step-state, disposition: fixed}
  - {id: C8, severity: Minor, aim: deliverable, fix_induced: false, component: agenda-step-context, disposition: fixed}
```

Round 2 runs ONE half (alternation): Codex, on the fold.
