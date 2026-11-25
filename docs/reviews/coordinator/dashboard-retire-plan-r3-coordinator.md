# Round 3 — `dashboard-retire-plan` — coordinator — ⟳ NOT CONVERGED (Claude); 5 fixed, 0 rejected

REVIEW GAP: codex — alternation (rounds 2+ run one half; the Codex half ran round 2).

```yaml
round: 3
fixes_nontrivial: true
subject: dashboard-retire-plan
halves:
  codex: gap
  claude: ran
findings:
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: false, component: store-gate, disposition: fixed}
  - {id: CM2, severity: Medium, aim: deliverable, fix_induced: false, component: cutover, disposition: fixed}
  - {id: Cm3, severity: Low, aim: deliverable, fix_induced: true, component: goal-tree, disposition: fixed}
  - {id: Cm4, severity: Low, aim: deliverable, fix_induced: true, component: cutover, disposition: fixed}
  - {id: Cm5, severity: Low, aim: deliverable, fix_induced: true, component: store-gate, disposition: fixed}
```

Subject: `docs/superpowers/plans/2026-11-24-dashboard-retire.md` at `0fb68ffe` (reviewed); fold at the commit
after `72bda429`. The approved spec's decisions are not reopened.

- Claude half: `docs/reviews/claude/dashboard-retire-plan-r3-claude.md` — 2 MAJOR, 3 MINOR (here CM1–CM2,
  Cm3–Cm5). NOT CONVERGED.
- Codex half: not run (alternation).

**Thrashing: NO.** No round-3 finding was caused by round 2's fold. Traced through the plan's history:
CM1's 2.13 and 12.11 rows and CM2's `<pin-base>` are in the first draft (`c1580091`); Cm3's sever anchor,
Cm4's unspecified cwd and Cm5's `tail -1` were all written by round 1's fold (`f03edd02`) and survived
round 2 — r2's XM2 and Xm4 rewrote the lines Cm4 and Cm5 sit in without introducing either defect. The one
link to r2: r2 XM3 made 12.11 an actual case in Step 1, which is what lets CM1's 12.11 half bite; the
defect (a live read) predates it. Three r1-induced findings found a round late is a review-coverage
signal, not a fix-causes-fix loop. The next round is r4: by the round cap, findings are FILED unless a
BLOCKER.

| Id | Finding | Verified against | Disposition — where fixed |
|---|---|---|---|
| CM1 | 2.13 and 12.11 call git on the live tree; the mutation harness stages a tree with no `.git` | `check-plan-code.py` `HARNESS_TREE` (:471) has no `.git`; the `ci.yml` sweep comment says "a temp dir with no `.git` at all". Measured in a scratch copy with no `.git`, inside `fixture_git.isolated()`: `git ls-tree --name-only HEAD docs/asks/` rc 128; the same call in a `fixture_git` temp repo holding `docs/asks/.gitkeep` rc 0 | **Fixed.** 2.13 builds a `fixture_git` temp repo and calls `ask_store_problems(None, <that repo>)`. 12.11 reads the store FILE (`git hash-object -- <path>`, which needs no repository, and `hashlib.sha256`) — measured in the no-`.git` copy: rc 0, and the blob equals `rev-parse HEAD:` in this checkout; `docs` is in `HARNESS_TREE`. Task 2 Step 7 now requires a green control in the staged tree. **FAILS IF** any case reads this checkout's git: the harness control goes red there |
| CM2 | 12.11's `<pin-base>` is never defined, and every derivable reading goes red on master after S2 | the plan: the pin-base lives only in a commit message; after the squash master's store is `LEGACY_STORE_BLOB`, not `LEGACY_STORE_BASE_BLOB` | **Fixed, the reviewer's option (b):** 12.11 has no base half. The base pin is checked where its subject exists — Task 12 Step 6 (new line) and Step 10 run `--cutover-check origin/master`, Task 13 Step 1 runs `--cutover-check "$SQ^1"`. **The gate can still fail:** a base blob other than the store REF names returns 1 (12.8; 12.12 drives it on a fixture repo). Task 13 Step 4 also confirms the `check-ask-store self-test` step on the master run |
| Cm3 | Task 3's sever anchors `needs_from_dashboard),` before Step 3 restructures that loop | `goal-tree.py:1563`, the only occurrence today | **Fixed.** Step 3 keeps the tuple line verbatim and adds the `asks` source as a separate block after the loop; if it must reshape, the anchor is taken from the implemented line and the all-manifest resolve runs before Step 5 |
| Cm4 | Task 13 Step 1 runs `--cutover-check` from an unspecified checkout | before a fast-forward the main checkout has no `check-ask-store.py` | **Fixed, NOT the reviewer's first option:** `git show … \| python3 -` is refuted — the gate's `ROOT` is `Path(__file__).resolve().parent.parent`, and under `-` that resolved to the cwd's PARENT (measured), so its git calls would read the wrong directory. The chain now adds a detached worktree at `$SQ`, runs the check there, and removes it. Extracted and run on a scratch clone (gh stubbed, squash `7a6ffa00`, today's gate name): MERGED → `rc=0`, worktree removed; OPEN → `rc=1`, no worktree made |
| Cm5 | Step 5b's `tail -1` shows only the impure suite's line | today's self-test prints `149/149 passed`, then `13/13 cannot-run cases passed` | **Fixed.** `tail -2`; Expected names both lines. Re-run on a scratch clone with no local `master`: both lines, rc 0 |

**Mutation arithmetic:** unchanged — no fix adds or removes a mutation. Pins as round 1 left them.

`fixes_nontrivial: true` — 12.11 is redesigned (no base half, reads the file, not HEAD) and Task 13 Step 1's
chain gains a worktree; both are new text a reviewer has not read.

Next: round 4, ONE half by alternation (Codex), against this fold — under the cap, only BLOCKERs are folded.
