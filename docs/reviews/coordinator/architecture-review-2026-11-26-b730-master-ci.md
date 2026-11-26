# Architecture review (Phase 6) — PR #643, backlog #730: which CI run answers for master's head in `--post-cutover`

- **Subject:** `_master_ci` in `scripts/check-ask-store.py` (`:898-950`) and its one caller, `post_cutover` (`:953-1002`).
  The question it answers: *is master's CI green with the ask-store steps*, the fourth check of plan Task 13 Step 1.
- **Armed by:** THRASHING. `check-review-decision.py` reports ARCHITECTURE_REVIEW: the component
  `scripts/check-ask-store.py _master_ci` carried fix-induced findings in review rounds 2 (G1, G2) and 3 (H2).
- **Read first:** `CONTEXT.md`, `docs/adr/` (ADR-0014 is the one that bears on a guard's shape), `docs/review-method.md`
  (the stop condition, *can a redesign remove it?*, the arming condition), the three coordinator round documents, the
  Codex halves of rounds 1 to 3 and the Claude half of round 1, the round-2 fold `279993a3`, Task 13 and Task 16 of
  `docs/superpowers/plans/2026-11-24-dashboard-retire.md`, and `.github/workflows/ci.yml` (triggers, concurrency, the
  two named steps).
- **Changed by this review:** this file only. No code and no other document.
- **Tagging:** **[M]** = measured by me (a command run, or code quoted). **[I]** = inferred, not measured.
- **Baseline [M]:** worktree head `d0e368d6`; `origin/master` as last fetched is `e1b13c15`, which is also the merge
  base. `python3 scripts/check-ask-store.py --self-test` at the head: 139/139, plus 56/56 cannot-run cases, rc 0.
  Mutation sweeps were NOT run by me.
- **Not measured, by instruction:** nothing on GitHub was read. Every statement about what GitHub or `gh` returns over
  the network is **[I]**. `gh run list --help` (local, gh 2.88.1) was read.
- **Instrument:** a differential probe over `_master_ci`, run on a byte copy of the gate file in the session scratch
  directory. A fake `gh` models the run list newest first, the `--commit` filter, then `--limit`. 72 cases: 0, 1, 19,
  20, 21 or 45 runs on other commits newer than the head's run; the head's run absent, green, red or in progress; an
  optional older second run on the head. Three answers are compared per case: the code at the head, a prototype with
  `"--commit", head` added to the one `gh run list` call, and an oracle that applies the stated rule to the unlimited
  list.

## Conclusion

**The thrashing was structural in rounds 1 and 2, and the round-2 fold already was the redesign. Round 3's H2 is what
is left of it. No code change is needed before the merge. One small change is worth filing.**

1. **Rounds 1 and 2 thrashed for one reason.** The check was written to judge "the post-squash run", and the plan's own
   shape rule says no step identifies the squash commit. So each version picked the run by a proxy. The round-2 fold
   replaced the proxy with an identity: the run whose commit IS the fetched head. That rule is now written in the
   docstring, the rc comments and Task 13.
2. **The design at the head is sound.** In 72 probe cases it never answers green when the rule says otherwise. Every
   one of its 30 disagreements with the rule is rc 8, a refusal.
3. **Round 3's dismissal of H2 holds.** Its conclusion is right. Its stated reason is weaker than the one available
   (§3).
4. **A simpler design exists and removes the last selection.** Ask GitHub for the head's runs with `--commit`. It is
   two argv items. It can be filed, because what it repairs is a wrong refusal code in a state that needs a force
   move of master AND a missed CI trigger.

**The observations that would make this conclusion wrong:**

- **Unsound design:** any `gh` answer for which `_master_ci` returns green while the newest `CI` run for a master
  update on the fetched head, read from the unlimited list, is not completed with run, `verify` job and both steps
  `success`. One such case makes the change a merge blocker.
- **Reachable H2:** Task 13's command prints rc 8 twice, more than one CI duration apart, on one head, while GitHub
  shows a completed run on that head. Then the dismissal was wrong and the filed change is owed at once.

## 1. The finding chain, per finding

| Round | Finding | What selected the run at that point | Caused by the previous fold? | Can a redesign remove it? |
|---|---|---|---|---|
| r1 F1 | a red run is skipped and an older green one answers: false rc 0 | the first run whose L1 step reported `success` or `failure` | no (first round) | yes |
| r2 G1 | a green run on an earlier commit that carries the gate marker answers: false rc 0 | the newest completed run whose commit carries `GATE_L1_MARKER` (r1 fold `16738fc9`) | **yes** | yes |
| r2 G3 | `--status completed` hides the head's run in progress: false rc 0 | the same list, filtered to completed runs | no (the filter predates the fold) | yes |
| r2 G2 | the `verify` job's own conclusion is ignored | not a selection question. It is what "green" means | recorded as yes (the r1 fold keyed on the job, F6) | no. It is a missing conjunct |
| r3 H2 | 20 newer runs on other commits push the head's red run out of the list: rc 8 where rc 7 is right | the newest run on the head **among the newest 20** (r2 fold `279993a3`) | **yes** | yes |

Four of the five are one question asked three times: *which run answers?* **[M]** from the diffs of `16738fc9` and
`279993a3`. G2 is the other kind in the method's table: a branch of a rule the design governs, fixed by adding the
conjunct. The green predicate is now run AND job AND both steps (`:947-948`), and I found no fifth conjunct.

**Severity fell while the thrash ran [M]** (the coordinator documents): one false rc 0 in round 1, three false rc 0 in
round 2, one wrong non-zero code in round 3. That is a fold converging, and the arming condition does not look at
severity.

## 2. The structural cause

**A relation with no referent.** Task 13's text reads "no step identifies the squash commit". The original fourth check
still asked about "the squash's run". With nothing naming the squash, the code had to infer "post-squash" from what a
run looks like:

| Version | The proxy for "post-squash" | Why it had to fail |
|---|---|---|
| before round 1 | the L1 step reported a decisive conclusion | a red run marks the step `skipped`, so red looks like pre-squash |
| r1 fold | the run's commit carries `GATE_L1_MARKER` | every commit from S2 on carries it. `origin/master` carries it today **[M]** |
| r2 fold | none. The run's commit is the fetched head | — |

The r2 fold did what the stop condition asks for. It did not add a case. It deleted the relation and used a value
`post_cutover` already held: the `head` it judges the store, the asks and the gate blob against. A different shape
dissolved G1, G3 and the selection half of F1 in one edit. By the method's one test those were mechanism defects, and
the redesign happened one round before this review was armed.

**What the r2 fold left.** The identity is still resolved on the client, inside a window: list the newest
`RUN_LIST_LIMIT` (20) runs for the branch, then keep those on `head` (`:919-929`). H2 is that window. Before the fold
the window could not matter (the marker never leaves master, so the newest run always qualified). The fold made it
matter in principle. `fix_induced: true` is the correct label.

**The gate file already holds the rule H2 asks about, in the sibling function [M].** `store_edit_prs` refuses a full
page: `if len(prs) >= PR_LIST_LIMIT:` returns "there may be more" (`:837-838`), with case 12.14. `_master_ci` has a
window and no statement of what a full one means. Copying the sibling's rule here would be wrong: master's list is
always full, so "head absent and page full" is also the ordinary state seconds after a merge, and rc 8 would turn into
rc 2 **[I]**. The window has to go, not gain a rule (§4).

**Why no case could show H2 [M].** The self-test's fake `gh` does not model `--limit` for `gh run list`. It returns
every run it was given. A truncated list cannot be built in the self-test as it stands.

## 3. Is round 3's dismissal of H2 sound?

**Yes in its conclusion. Its evidence is one fact short, and a stronger reason was available.**

| Claim in the round-3 document | Verdict | Evidence |
|---|---|---|
| 20 newer runs need 20 updates of master between the `git fetch` and the `gh run list` | holds | the two calls are in one process, `:961` and `:919` **[M]**. Master's median gap between commits is 113 min over the last 200; 2 gaps are under 10 min **[M]** (`git log --first-parent -200 origin/master`) |
| the other route needs a force move of master, which protection forbids (`allow_force_pushes: false`) | **incomplete** | that setting binds administrators only when `enforce_admins` is on. The round-3 document does not record it, and I did not read GitHub. **[I]** |
| rc 8's line says what it found, so it does not misreport | half true | it reports the count correctly. Its advice, "wait for it and re-run", is wrong in that state: waiting does not bring the run into the list |

**The stronger reason [I].** Moving master back to commit A is itself an update of the branch. GitHub starts a new `CI`
run on A for it, and that run is the newest in the list. So the state Codex describes (A's newest run is old and red,
20 newer runs sit on other commits, and A is the head) needs two things at once: a force move of master, and that
move starting no run. Protection is one barrier. The second holds even with protection off.

**What the state costs if it is ever reached [M for the code, I for the cadence].** rc 8 is a refusal: the probe found
0 false rc 0 in 72 cases, and all 30 differences from the rule are rc 8. Task 13 is not complete on rc 8. The next
merge to master makes a new head with a new run inside the window, which ends the state. Nothing false reaches a gate,
so under `review-method.md` §0 Q4c it is not a BLOCKER.

**One more state the same line covers [I].** rc 8 also prints when the head will never get a run: Actions disabled, or
a `[skip ci]` marker in the squash message. None of master's last 400 first-parent messages carries one **[M]**. This
is not truncation and `--commit` does not remove it. It ends the same way, at the next merge.

## 4. The simpler design, and what the probe says about it

`gh run list` has had a server-side commit filter since before the installed version: `-c, --commit SHA  Filter runs
by the SHA of the commit` **[M]** (gh 2.88.1 help). Adding it asks GitHub the question the r2 fold stated, instead of
asking for a window and searching it.

| Variant | Differs from the rule (of 72) | False rc 0 | Where it differs |
|---|---|---|---|
| head `d0e368d6` | 30 | 0 | every case with 20 or more newer runs on other commits, and every case where the head's only run is older than the window. Always rc 8 |
| prototype: `"--commit", head` added, client filter kept | 0 | 0 | — |
| prototype against a server that IGNORES `--commit` | equals the head in all 72 | 0 | — |

The third row is why the client-side `headSha == head` filter must stay. With it, the worst a wrong assumption about
`--commit` can do is today's behaviour. An older `gh` without the flag exits non-zero, which is already rc 2
(`:921-922`).

**The change, stated to implement.** In `scripts/check-ask-store.py`:

1. `_master_ci`: add `"--commit", head` to the `gh run list` argv, after `"--event"` and its value. Keep
   `mine = [x for x in runs if x[1] == head]` unchanged. Keep `--limit`.
2. The rc 8 line for an empty `mine` drops "none of the newest N" and says: GitHub lists no `CI` run for a master
   update on head `<sha8>` yet; wait and re-run; if it stays so, read the head's commit page. Update the docstring's
   "in the newest RUN_LIST_LIMIT" and Task 13's "the newest `CI` run … whose `headSha` IS" sentence to match.
3. The fake `gh` (`_pc_gh`): honour `--commit` (keep only runs on that SHA) and then `--limit` (truncate, newest
   first), in that order, as GitHub does.
4. One new case, H2's shape: the head's run red, listed after `RUN_LIST_LIMIT` runs on other commits, expects rc 7.
   One new mutation: drop the `--commit` pair, and that case goes red (rc 8). Pin 98 → 99.
5. **Before it is trusted:** one read-only live call, `gh run list --workflow CI --branch master --event <the push
   event> --commit <a master SHA> --json databaseId,headSha`, must return only runs on that SHA. The fake in step 3
   is otherwise the contract as imagined.

Cost **[I]**: about 10 changed lines, one case, one mutation.

**Why it can be filed and not folded now.** Three reasons, in order of weight:

- It repairs a refusal code, never a pass (§3).
- A fold on this component is the event that produced each of the last two rounds' findings. Round 3 is at the round
  cap; folding a non-BLOCKER now buys another round on the code that just armed this review.
- The code is short-lived. Task 13 runs once. Task 16 deletes `store_edit_prs` and `PR_LIST_LIMIT` in S3 (plan
  `:1033-1034`), and `post_cutover` calls `store_edit_prs` (`:993`) **[M]**.

**The observations that would show this redesign FAILED:**

- the new case (step 4) passes with the `--commit` pair deleted: then the fake does not model the window and the case
  proves nothing;
- the live call in step 5 returns a run on another SHA, or none for a SHA whose run exists: then `--commit` does not
  mean what the help line says, the change is dropped, and the window gets the only honest rule left (head absent AND
  the page full is rc 2, with the cost named in §2);
- a later finding on `_master_ci` of the form "the wrong run answered". The next step is then not another patch: it is
  to move the question out of this function, by having Task 13 name the run it means.

## 5. Tried, and failed, to refute the design at the head

| Attack | Result |
|---|---|
| Master's concurrency group cancels the head's run | the group is per event and ref, never cancelled in progress for a master update (`ci.yml:53-55`) **[M]**. A queued run is replaced only by a newer one, and then the head has moved **[I]**. Head-pinning is the one selection rule that is immune; "newest completed" (before round 2) was not |
| Another job fails, so the run's conclusion is not `success` while `verify` is green | on a master update `mutation-sweep` and `mutation-sweep-complete` are skipped by their `if:` (`ci.yml:1199`, `:1586`) **[M]**, and a skipped job does not fail a run **[I]**. The self-test still holds a case for it (rc 7) |
| Head-pinning never settles because master moves faster than CI | 159 of 199 gaps exceed 60 min, 11 are under 20 min **[M]**. CI's duration was not measured. The coordinator also controls the merges |
| Several runs on one head | the newest is judged, with a case ("two runs on the head commit, the newest red") **[M]**. A re-run keeps its run id **[I]** |
| The head moves between the fetch and the list | every check judges the same fetched `head` (`:963`, `:997`) **[M]**; the answer is about that commit and a re-run reads the new one |
| Two workflows named `CI` | one: `ci.yml:12` **[M]** |

## 6. Decided this slice and not written down

- **`post_cutover` and `_master_ci` have no removal row.** Task 16's deletion list names `store_edit_prs` and
  `PR_LIST_LIMIT` and not their caller (plan `:1033-1034`), because the list predates backlog #730 **[M]**. Deleting
  the callee as written breaks `--post-cutover`. Either Task 16 names `post_cutover`, `_master_ci`, the `PC_*` codes
  and their cases and mutations, or it records that they stay and what `post_cutover` calls instead.
- **H2's decline has a lapse condition that nothing watches.** The round-3 document says the decision lapses if
  protection ever allows force moves of master. If the change in §4 is filed, the condition can be deleted with it.

## 7. For the coordinator

| Item | Needed before PR #643 merges? | Where it goes |
|---|---|---|
| The design at the head (judge the run on the fetched head) | — | stands |
| H2, declined in round 3 | no | the decline stands; add the second reason from §3 to the backlog row |
| `--commit` (§4, five steps) | **no** | a backlog row under backlog #730's goal. Do it with, or drop it at, Task 16 |
| Task 16's deletion list omits `post_cutover` (§6) | no | the same row, or an edit to Task 16 in the S3 plan round |
| `enforce_admins` on master's protection (§3) | no | one read-only `gh api` call by the coordinator, recorded in the row |
