# Architecture review (Phase 6) — the dashboard-retire plan's `cutover` component (Task 13)

Convened 2026-11-24 because `scripts/check-merge-ready.py --pr 636` holds PR #636 with *thrashing armed* on
the component `cutover`. Subject: `docs/superpowers/plans/2026-11-24-dashboard-retire.md` at `0c336f9b`
(the r4 fold is `223f24a1`). The approved spec and the ADRs are not reopened.

## Verdict — CHANGE PLAN BEFORE MERGE (the change is applied in this worktree, uncommitted)

1. **It is thrashing, and the round-4 coordinator's "not thrashing" is refuted.** One nine-line shell block
   (Task 13 Step 1) was rewritten by all four folds, and each rewrite produced the next round's finding.
   A fifth defect is live in the r4-folded text (finding F2), in a fold nobody reviewed.
2. **A redesign removes the class**, so by the method's one test (`docs/review-method.md` → *Can a redesign
   remove it?*) these are mechanism defects, not a prose floor.
3. **The redesign cannot wait for the build slices.** Task 13 says "No file changes": it has no builder, no
   PR and no review round of its own. The plan is the only place its text is ever reviewed, and it then
   runs once, on master, outward-facing.
4. **The redesign is small and is applied:** Task 13 is rewritten, three sentences in Task 12 that cited
   the old Step 1 are repointed, and one phrase in the carried-findings table is corrected. No code
   interface, case, mutation or pin in the plan changes.
5. **One review half is owed on the changed text** before the plan merges (the REDESIGN bet's own check).
   If that half finds a defect in Task 13's shell, the next route is SPLIT, stated below — not another patch.

## Findings

| Id | Severity | Finding | Status |
|---|---|---|---|
| F1 | High | Task 13 Step 1 is executable shell in prose with no case, and it re-accreted in every fold | Fixed by the redesign |
| F2 | High | The r4 fold carries `$T` between steps; the coordinator's shell calls share no state | Fixed by the redesign |
| F3 | Medium | The squash-parent check duplicated push-mode L1 on master, and was the weaker of the two | Fixed by the redesign |
| F4 | Medium | The r3 and r4 "not thrashing" arguments rest on a narrower test than the one the headers record | Reported; coordinator documents not edited |
| F5 | Low | Step 4 required the CI run "on S2's merge commit", which may never complete | Fixed by the redesign |
| F6 | Low | The carried-findings table said "every open PR"; Task 13 acts only on PRs that edit the store | Fixed (one phrase, plan line 97) |
| F7 | Low | `check-review-decision.py` cannot read the r4 coordinator header (`severity='Critical'`) | Reported; not edited |
| F8 | Note | With Step 1 gone, `--cutover-check` and the base pin serve only the early pre-squash check | Not acted on — see below |

### F1 — one block, four folds, four findings (High, mechanism)

The plan's history, read with `git show <commit>:<plan>` for each of its five commits:

| Commit | Round | What the fold did to Task 13 Step 1 | The defect it left | Found in |
|---|---|---|---|---|
| `c1580091` | draft | no such step; Step 4 already said "the `ask store (push)` step … is green" | — | — |
| `f03edd02` | r1 fold (Codex M2) | added Step 1: 3 lines, squash found by `git log --grep='^Ask store S2'` | a title the plan never sets; cwd unspecified | r2 XM2, r3 Cm4 |
| `0fb68ffe` | r2 fold (XM2) | replaced it with a five-link `gh pr view` chain | still runs `python3 scripts/check-ask-store.py` from cwd, one line after proving the file is in the squash's tree | r3 Cm4 |
| `ec39c705` | r3 fold (Cm4) | added a detached worktree, `; rc=$?`, a cleanup line | the block ends in `echo` (status always 0); the worktree is removed before Step 1b needs it | r4 XB1, XB2 |
| `223f24a1` | r4 fold (XB1, XB2) | ended with `test "$rc" -eq 0`; kept `$T` for Steps 1b and 3 | `$T` crosses shell calls (F2) | this review |

Every row's fix is correct for the finding it answers. That is the stop condition's point
(`docs/review-method.md:296-301`): "a wrong shape never fails a round; it emits a stream of defects that
get fixed". The shape here is a multi-line shell procedure, with variables, a subshell, a temp worktree and
an exit-status convention, written in a document. Nothing runs it until the one time it runs on master.
Each reviewer finding is what a test would have reported on first execution.

**Can a redesign remove it? Yes** — see *The redesign*. So this is a mechanism defect, and the r4
coordinator's own description of the residue ("executable shell inside prose that no case runs until the
post-merge cutover — the cost of a hand-run step, not of the design",
`docs/reviews/coordinator/dashboard-retire-plan-r4-coordinator.md:30-31`) names the design and then denies
it is one. Choosing a hand-run step over a tested entry point is the design decision.

Share of the review's findings: `cutover` carries 9 of the 20 findings in the four coordinator headers
(r1: 3 of 9; r2: 2 of 4; r3: 2 of 5; r4: 2 of 2), counted from the headers.

### F2 — the r4 fold's kept worktree depends on shell state that does not persist (High)

After `223f24a1`, Step 1 sets `T` and `SQ`; Step 1b runs `(cd "$T" && python3 … --list-store-prs)`; Step 3
runs `git worktree remove --force "$T"`; the repair text uses `"$SQ^1"`. The plan does not say the steps
share one shell. The coordinator is an agent whose shell calls share no variables. Measured 2026-11-24 in
this harness: a variable exported in one call is empty in the next.

With `T` empty, measured on this machine's bash 3.2.57:

| Step as written at `223f24a1` | With `T` empty | Effect |
|---|---|---|
| 1b: `(cd "$T" && python3 scripts/check-ask-store.py --list-store-prs)` | `cd ""` returns 0 and stays in the current directory | the listing runs from whatever checkout the call started in — the case r4 XB2 was folded to prevent |
| 3: `git worktree remove --force "$T"` | `fatal: '' is not a working tree`, rc 128 | the worktree Step 1 made is never removed |

This fails closed in the main checkout before its fast-forward (rc 2, as Codex measured for XB2), so it is
a step that cannot be executed as written rather than a gate that passes wrongly. It is still the fifth
consecutive fix-induced defect in the same block. The r4 coordinator recorded `fixes_nontrivial: false`
("three lines of shell … no new logic for a reviewer to read", `…-r4-coordinator.md:38-39`), so under the
round cap this fold went to the PR unreviewed.

If the coordinator happened to run Steps 1 through 3 in a single shell call, the r4 text works. The plan
does not require that, and "it works if run the unstated way" is the same shape as r3 Cm4.

### F3 — the squash-parent check duplicated L1 on master, and saw less (Medium)

The plan's own text says the condition Step 1 looked for is already visible elsewhere: on rc 1 "master's
push-mode `ask store` step is red on the squash (L1 sees the stray bytes)" (plan at `223f24a1`, Task 13
Step 1), and the first draft's only master-side check was that CI step.

Measured 2026-11-24 on a fixture repository (a 40-entry store; branch `s2` rewrites header lines 3–6;
`git merge --squash`):

| Case | Squash's store = the pin? | Squash's parent store = the base pin? | Master's tip store = the pin? |
|---|---|---|---|
| A — master unchanged before the squash | yes | yes | yes |
| B — an entry appended on master before the squash | **no** (the diff is that entry) | no | no |
| C — an entry appended on master AFTER the squash | yes | **yes — the parent check passes** | **no** |

In A and B the two checks agree. In C — the spec's "residual race", which r6 Claude M1 called the normal
case — only the state check sees the stray entry. So the check the four folds kept repairing was redundant
where it worked and blind where the spec says the traffic is. The five identity links (merged, ancestor,
one parent, file in tree, worktree) existed only because the check was about one commit's history. A check
about master's state needs none of them.

Bound: the fixture squashes with local `git merge --squash`. That GitHub's squash builds the same tree is
inferred, not measured. A header edit and an end-of-file append merged cleanly here; an edit adjacent to
lines 3–6 would conflict, and GitHub then refuses the merge, which sends S2 back to Task 12 Step 4.

### F4 — the "not thrashing" arguments (Medium, process)

- r3's header marks Cm4 `component: cutover, fix_induced: true`
  (`docs/reviews/coordinator/dashboard-retire-plan-r3-coordinator.md:16`), and its prose says "No round-3
  finding was caused by round 2's fold" (`:27`). The gate reads the header. `docs/review-method.md:253`
  asks "did the previous round's fix cause this?", so one of the two is wrong, and nothing in the document
  says which.
- The prose is right about origin: the cwd defect was written by the r1 fold (`f03edd02`). But the r2 fold
  rewrote that exact command and added `git cat-file -e "$SQ:scripts/check-ask-store.py"` on the line
  before it (`0fb68ffe`). A fold that proves where the script is and then runs a different copy did not
  merely fail to notice an old defect.
- r4 argues "Thrashing needs two CONSECUTIVE fix-induced rounds in one component; this is one"
  (`…-r4-coordinator.md:29-30`). By the headers it is three (r2, r3, r4). By the strict previous-round
  reading it is r2 and r4 with r3's finding one fold older. Neither reading supports "the plan goes to its
  PR": the method's test is *can a redesign remove it*, and that question was not asked in either document.

Not edited: the coordinator documents are the record of what was argued at the time.

### F5 — a CI run that may not exist (Low, inferred)

Step 4 named "the CI run on S2's merge commit". `.github/workflows/ci.yml:50-55` puts master runs in one
concurrency group without `cancel-in-progress`, and its comment says a second run replaces a first's
pending run. If two merges land close behind S2, the squash's own run can be replaced before it starts.
L1 reads state, so the redesigned Step 5 accepts the newest completed master run at or after the squash.
Not measured: no run was observed being replaced.

### F7 — the r4 header is unreadable to the decision script (Low, measured)

`python3 scripts/check-review-decision.py` on this branch prints: `CANNOT RUN — a round document for
'dashboard-retire-plan' has no usable header: finding 'XB1' has severity='Critical', not one of
['Blocking', 'High', 'Low', 'Medium']`. `check-merge-ready.py` evidently reads the same headers by another
route, since it armed. The r4 coordinator header needs `Blocking`. Not edited (outside this review's
write scope).

### F8 — the base pin after the redesign (Note, not acted on)

`LEGACY_STORE_BASE_BLOB`, `cutover_problem` and `--cutover-check REF` now serve only Task 12 Steps 6 and
10, the early pre-squash check. PR CI's L1 on GitHub's merge ref and Task 13 Step 1 cover the same event
later. They were left in place because the spec's carried finding M1 part 2 asks for a pre-merge check
(spec `:337`), and removing them changes the mutation arithmetic (6 entries, plan `:126`). Removing them is
a possible simplification for the S2 builder to raise, not a defect.

## The redesign

**Rule (now the first paragraph of Task 13, plan `:811-817`):** every command in Task 13 is ONE call of a
tested entry point of `check-ask-store.py`, in ONE shell call, whose own exit status is the answer. No
variable crosses steps, no step identifies the squash commit, no step builds a worktree. Anything more is
code for the gate file with a case and a mutation.

**What changed in the plan (all in `docs/superpowers/plans/2026-11-24-dashboard-retire.md`):**

| Where | Before | After |
|---|---|---|
| Task 13 Step 1 (`:819`) | nine-line chain: find the squash by PR, four identity links, detached worktree, `--cutover-check "$SQ^1"`, `rc` convention | `cd <S2's worktree> && git fetch origin master && git checkout -q --detach origin/master && python3 scripts/check-ask-store.py` — push-mode L1 over master's tip, the same command the CI step runs |
| Task 13 Steps 1b and 3 (`:840`, Step 4) | `(cd "$T" && … --list-store-prs); rc=$?; echo; test`, then `git worktree remove --force "$T"` | `cd <S2's worktree> && python3 scripts/check-ask-store.py --list-store-prs`; no worktree to remove |
| Task 13 repair text | `git show "$SQ^1:…" > "$TMPDIR/s.md"` then C1 with `--store` | C1 with no argument in the same checkout: the store at HEAD is the stray one |
| Task 13 Step 4 → Step 5 (`:853`) | the run on S2's merge commit | the newest completed master run at or after the squash |
| Task 13 **Test** line | 12.12 is Step 1's check | 12.10 is Step 1's check (mutations "push mode skips L1", "L1 compares nothing") |
| Task 12 Step 1 note (`:740-743`), Step 10 (`:798-800`), FAILS IF M1 part 2 (`:803-805`) | cite Task 13 Step 1's `--cutover-check "$SQ^1"` | cite push-mode L1 over master's tip |
| Carried-findings table (`:97`) | "every open PR" | "every open PR whose diff still edits the store" |

**Plan tasks changed:** 13 (rewritten) and 12 (three sentences). **Unchanged:** every interface, every
behavior row 12.1–12.16, the ten mutations of Task 12 Step 8, the mutation arithmetic and every pin. Case
12.12 keeps its subject: Step 10 passes `origin/master`, a REF that is not HEAD.

**Controls for the new Step 1, run 2026-11-24 on a scratch clone:**

| Control | Result |
|---|---|
| the gate file absent at `origin/master` (S2 not merged) | python rc 2, block rc 2 |
| today's gate name standing in for the renamed one | `ok — …`, block rc 0 |
| a failed `git fetch` | block rc 128, the gate never runs |
| the `<S2's worktree>` placeholder left unfilled | bash syntax error, rc 2 |

Not measured, because the code does not exist yet: that `main([])` of the built `check-ask-store.py`
returns 1 on a moved store. That is behavior 12.10 and the mutation "push mode skips L1", owed by Task 12.

**The observations that would show this redesign failed:**

1. The review half owed on this fold reports a defect in shell written in Task 13. Then SPLIT: Task 13's
   steps leave the plan's prose and become one entry point of the gate file (for example
   `check-ask-store.py --post-cutover`) with cases over a fixture repository and a stubbed `gh`, built in
   S2 as a task with a builder and a review. The plan's Task 13 then holds one command.
2. At the cutover itself: Step 1 returns 0 while `git rev-parse origin/master:docs/dashboard-entries.md`
   is not `LEGACY_STORE_BLOB`.
3. Step 2 or Step 4 needs a variable, a second command or a worktree to run as written.

Per the escalation ladder (`docs/review-method.md` → *Redesign or accretion*), ACCRETE was tried four times
on this unit and is not retried; this is the REDESIGN route; SPLIT is next.

## What was decided in this work that is not written down

1. **The binding check for M1 part 2 moved from before the merge to after it.** The spec's carried finding
   says "S2's merge step checks master's store is unchanged since the pin" (spec `:337`). The r1 fold made
   the pre-merge check "early, not sufficient" and put the binding check after the squash. That is recorded
   only as "(r1 Codex M2)" inside a step. This review keeps the decision and changes what the binding
   check reads.
2. **Who runs Task 13, and in what shell.** "The coordinator's" is stated; that the coordinator is an agent
   whose calls share no shell state is not, and four folds wrote text that assumed otherwise. The shape
   rule now states it.
3. **A task with no file changes is reviewed only as plan text.** Nothing in the process says so. It is why
   this redesign could not be deferred to the slices.
4. **What `fix_induced` means when a defect comes from a fold two rounds back.** The r3 header says true,
   the r3 prose says not thrashing, and the merge gate believed the header (F4).
5. **Under the round cap, the folder judged its own fold trivial.** `fixes_nontrivial: false` on the r4
   fold is what sent it to the PR without a reader. The cap says which findings are folded; it does not say
   who decides a BLOCKER's fix needs no review.
6. **M1 part 3 was narrowed** from the spec's "every PR still open" to PRs whose diff names the store. The
   narrowing is sound (a PR with no store edit has nothing to drop, and L1 passes on its merge), and it was
   only implied by Task 13's steps while the table said otherwise (F6).

## Measured or inferred

| Claim | Basis |
|---|---|
| Task 13 Step 1 was rewritten by each of the four folds | Measured — `git show` of the plan at `c1580091`, `f03edd02`, `0fb68ffe`, `ec39c705`, `223f24a1` |
| `cutover` holds 9 of 20 findings | Measured — counted from the four coordinator headers |
| A shell variable does not persist between the coordinator's shell calls | Measured — in this agent harness, 2026-11-24; inferred to hold for the coordinator, which uses the same tool |
| `cd ""` returns 0 and stays put; `git worktree remove --force ""` returns 128 | Measured — bash 3.2.57 on this machine |
| A store moved before the squash leaves the squash's store ≠ the pin | Measured — fixture repository, local `git merge --squash` |
| A parent check passes on an entry that lands after the squash; a tip check does not | Measured — same fixture, case C |
| GitHub's squash builds the same tree as local `git merge --squash` | Inferred |
| The new Step 1 chain stops non-zero on a missing script, a failed fetch, an unfilled placeholder | Measured — scratch clone, four controls |
| Push-mode `main([])` of the built gate returns 1 on a moved store | Not measured — the code is not built; owed by 12.10 and its mutation |
| A pending master CI run can be replaced by a later one | Inferred — from the comment at `.github/workflows/ci.yml:50-52` |
| `check-review-decision.py` cannot read the r4 header | Measured — its own CANNOT RUN message |
| `python3 scripts/check-docs.py` after the plan edit | Measured — prints "Documentation integrity OK" |
| The other document guards, `check-merge-ready.py --pr 636`, the plan-leak gate | NOT RUN in this review |

Scratch material, including the plan as it stood before this edit:
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/b387c8e6-9003-42f5-a944-1d4eb1de0c9b/scratchpad/p6-cutover/plan.before-phase6.md`
