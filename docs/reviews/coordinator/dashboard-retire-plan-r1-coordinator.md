# Round 1 — `dashboard-retire-plan` — coordinator — ⟳ NOT CONVERGED (both halves); 9 fixed, 0 rejected

```yaml
round: 1
fixes_nontrivial: true
subject: dashboard-retire-plan
halves:
  codex: ran
  claude: ran
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: cutover, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: false, component: cutover, disposition: fixed}
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: false, component: rename, disposition: fixed}
  - {id: XM4, severity: Medium, aim: deliverable, fix_induced: false, component: goal-tree-view, disposition: fixed}
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: false, component: store-gate, disposition: fixed}
  - {id: CM2, severity: Medium, aim: deliverable, fix_induced: false, component: store-gate, disposition: fixed}
  - {id: Cm3, severity: Low, aim: deliverable, fix_induced: false, component: ask-reader, disposition: fixed}
  - {id: Cm4, severity: Low, aim: deliverable, fix_induced: false, component: retired-reference-gate, disposition: fixed}
  - {id: Cm5, severity: Low, aim: deliverable, fix_induced: false, component: cutover, disposition: fixed}
```

Subject: `docs/superpowers/plans/2026-11-24-dashboard-retire.md` at `c1580091` (reviewed); fold in the commit
after `0a0188b3`. The approved spec's decisions are not reopened.

- Codex half: `docs/reviews/codex/dashboard-retire-plan-r1-codex.md` — 4 MAJOR (here XM1–XM4). NOT CONVERGED.
- Claude half: `docs/reviews/claude/dashboard-retire-plan-r1-claude.md` — 2 MAJOR, 3 MINOR (here CM1, CM2,
  Cm3–Cm5). NOT CONVERGED.

Each finding was checked against the code before folding; each proposed fix was treated as a hypothesis.

| Id | Finding | Verified against | Disposition — where fixed |
|---|---|---|---|
| XM1 | Task 13's `gh pr list` stops at gh's default 30, and a failed `gh` call reads as an empty list | the plan's Task 13 block: no `--limit`, no rc check in the `while` loop | **Fixed.** The listing moved into code: Task 12's `store_edit_prs` + `--list-store-prs` (`--limit PR_LIST_LIMIT`; a full page, any non-zero rc or an unparseable list is CANNOT RUN). Cases 12.13–12.16 (a PR past the default page, a full page, a failed list, a failed diff), 4 mutations. Task 13 Step 1b calls it; Task 16 deletes it |
| XM2 | the pre-squash cutover check leaves a window before the squash | `--match-head-commit` pins the PR head, not the base; master can move | **Fixed** by checking after the squash, not by narrowing the window: Task 13 Step 1 runs `--cutover-check <squash>^1`, the exact store the squash was built on, with a stated repair (C1 over that blob, re-ask as files, restore by L1's printed blob command). Case 12.12 (REF is read, not HEAD), 1 mutation. Task 12 Step 10 is reworded as early, not sufficient |
| XM3 | Task 8 renames the gate but leaves the PR-gate step invoking the old path | `ci.yml:1112` runs `scripts/check-dashboard-entry.py`; Task 8's grep, run on today's tree, prints `ci.yml:988` and `ci.yml:1112` | **Fixed.** Task 8 repoints the gate step's path, arguments unchanged; its FAILS IF names a workflow `run:` line, with that control recorded. **Same class, found while fixing:** Task 9 deletes `--pr-body-file` while the CI step still passes it, so the step would fail on argparse until Task 12 — Task 9 now drops the flag, `BODY` and `printf` from the step, case 9.8 plus a grep that must print nothing |
| XM4 | no severed-call mutation for the old reader in S1, which spec K4 requires | spec §5 K4: *In S1 the same holds for the old store's reader*; 0 `goal-tree.json` entries name `needs_from_dashboard` in their `before` text | **Fixed.** Task 3 adds "the goal tree's call to the old store's reader is severed" (in `collect`'s source loop), expecting 3.9, which is now driven through `collect`. Pin 525. Task 10 deletes it with its anchor |
| CM1 | after Task 2 the existing `main` cases reach real git, and go red only in CI (no local `master`) | `check-dashboard-entry.py` self-test: the malformed-entry case stubs only `g["collect"]` and calls `main(["--base", "master"])`; CI checks out with `origin/master` and no local `master` | **Fixed.** Every existing `main` case stubs `ask_store_problems`; cases 2.14 (rc 1 on a problem list) and 2.15 (rc 2 on err), mutation "main ignores A1's err". Step 5b runs the self-test in a clone with no local `master` — run on today's tree it passes (13/13 cannot-run) — with a stated control (unstub one case → red) |
| CM2 | 2.12 (git off `PATH`, through `main`) fails in `collect` first, so `ask_store_problems` swallowing its error is unwitnessed | `main` calls `collect`, whose first act is a git call | **Fixed.** 2.12 drives `ask_store_problems` directly under `_with_run` (raise, and rc 128), asserting `err is not None`; mutation "A1's git failure returns err=None" |
| Cm3 | 1.16 names two triggers | the plan's 1.16 row | **Fixed.** One trigger: `MAX_ASKS` patched to 3 with 4 files, restored in `finally` |
| Cm4 | K8's scanner would flag two fixture literals Task 15 does not list | `check-review-decision.py` (the "harness script is no longer assumed contained" case) and `gen-goals-page.py` (`_shown`) each hold `"scripts/gen-dashboard.py"` as a list element | **Fixed.** Task 15 renames both to `scripts/gen-backlog-page.py` (a live script, so no exemption), and Step 7 runs both self-tests |
| Cm5 | the push-mode L1 step also runs on `batch/**` | ci.yml `on.push.branches` | **Fixed** as a stated decision: intended, no `if:` on the ref; a batch carrying a store edit is red as its PR would be |

**Mutation arithmetic after the fold.** Gate manifest: 44 → **62** after S1 (Task 1 +11, Task 2 +7) → **63** after
S2 (−9, Task 12 +10) → **45** after S3 (−12 grammar, −6 cutover). Check: 23 staying + 18 from S1 + 4 L1 = 45.
`goal-tree.json` 520 → 525. Every pin the plan quotes was updated to match.

`fixes_nontrivial: true` — XM1 and XM2 add code, cases and mutations to Task 12 and restructure Task 13; CM1
changes how every existing `main` case is built.

Next: round 2, ONE half by alternation (Codex), against this fold.
