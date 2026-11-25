# Round 4 — `dashboard-retire-plan` — coordinator — ⟳ NOT CONVERGED (Codex); 2 BLOCKERs fixed — ROUND CAP REACHED

REVIEW GAP: claude — alternation (rounds 2+ run one half; the Claude half ran round 3).

```yaml
round: 4
fixes_nontrivial: false
subject: dashboard-retire-plan
halves:
  codex: ran
  claude: gap
findings:
  - {id: XB1, severity: Critical, aim: deliverable, fix_induced: true, component: cutover, disposition: fixed}
  - {id: XB2, severity: Critical, aim: deliverable, fix_induced: true, component: cutover, disposition: fixed}
```

Subject: `docs/superpowers/plans/2026-11-24-dashboard-retire.md` at `ec39c705` (reviewed); the fold is the
commit after it. The approved spec's decisions are not reopened.

- Codex half: `docs/reviews/codex/dashboard-retire-plan-r4-codex.md` — 2 BLOCKER, nothing else. NOT CONVERGED.
- Claude half: not run (alternation).

**Round cap (review-method §0 Q4c): from r4 only a BLOCKER is folded; anything less is filed.** Both
findings are BLOCKERs by the definition the prompt gave (a gate step unable to fail; a step impossible to
execute as written), so both are folded. No MAJOR or MINOR was reported, so nothing is filed.

**Thrashing or prose floor? NOT thrashing.** Both findings were caused by round 3's fold (Cm4 moved Task 13
Step 1 into a detached worktree and wrote its cleanup line), so r4 is fix-induced — but r3's findings were
NOT caused by r2's fold (the r3 coordinator traced each one to the first draft or to r1). Thrashing needs
two CONSECUTIVE fix-induced rounds in one component; this is one. The residue is executable shell inside
prose that no case runs until the post-merge cutover — the cost of a hand-run step, not of the design.

| Id | Finding | Verified against | Disposition — where fixed |
|---|---|---|---|
| XB1 | Task 13 Step 1 stores the check's status in `rc` and ends with `echo`, so the block returns 0 when the check fails | the plan's block as written; control: `bash -c 'false; rc=$?; echo "rc=$rc"'` returns 0 | **Fixed.** The block's LAST command is `test "$rc" -eq 0`. Control, run 2026-11-24: `bash -c 'false; rc=$?; echo "rc=$rc"; test "$rc" -eq 0'` → 1; with `true` → 0. **FAILS IF** a red `--cutover-check` leaves the block's status 0 |
| XB2 | Step 1b runs `scripts/check-ask-store.py` in the main checkout right after Step 1 removed the squash worktree; before the main checkout's fast-forward the script is absent (rc 2) | Codex measured rc 2 on a copy of today's checkout | **Fixed.** Step 1 no longer removes `$T`; Steps 1b and 3 run the gate as `(cd "$T" && …)` with the same `test "$rc" -eq 0` tail; Step 3 removes the worktree. **FAILS IF** Step 1b or 3 runs the gate from a checkout without the renamed script |

`fixes_nontrivial: false` — three lines of shell, each shape run as a control above; no new logic for a
reviewer to read. The plan goes to its PR.
