Reviewed head: 2afc4e28de9bb8d9733ca89f0b3742d16c74ed06

# PR #643 (backlog #730, `check-ask-store.py --post-cutover`) — review round 1, Claude half

Diff: `git diff dashboard-retire-s2...HEAD` (one commit, 2afc4e28). Mandate: refute that it is right; the worst outcome is a false rc 0 on the single real run after PR #640's squash.

## What was run

- `python3 scripts/check-ask-store.py --self-test` at the reviewed head: **139/139 passed, 42/42 cannot-run cases passed** (5.7 s).
- The 13 new `730 …` mutations in `scripts/mutations/check-ask-store.json`, hand-applied one at a time in a `git archive HEAD` copy (scratch `b730r1/tree`, its own `git init`): **every one turns exactly one case red, and that case is its `expect`** (13/13, nfail=1 each).
- Seven extra mutations of my own on the same copy (results under M2): 6 of 7 **survive**.
- A direct probe of `_master_ci` with `gh` stubbed to the step conclusions GitHub actually reports (script `b730r1/ci_probe.py`). Results under M1.
- Read: the backlog #730 row, `.github/workflows/ci.yml` (the `verify` job's steps, the `on:` block), the plan's Task 13 rewrite, `git config remote.origin.fetch`.

## Findings

### M1 (MEDIUM, and a false rc 0 is reachable) — a SKIPPED `ask store (push)` step is read as "before the squash", so master's real red is passed over

`scripts/check-ask-store.py`, `_master_ci`:

```python
if steps.get(CI_L1_STEP) not in ("success", "failure"):
    continue                                        # before the squash, or cancelled before the step
```

In the real workflow both steps are in the one `verify` job: `check-ask-store self-test` at `.github/workflows/ci.yml:987`, `ask store (push)` at `ci.yml:1116`. Neither has `continue-on-error` or `if: always()`; the L1 step's `if: github.event_name == 'push'` carries the implicit `success()`. So when ANY earlier step in `verify` fails (the self-test, typecheck, unit tests), GitHub marks `ask store (push)` **`skipped`**, and this loop skips the whole run as if it came before the squash. Probe results (`_master_ci` over stubbed `gh` answers):

| `gh` world (newest first) | got | right answer |
|---|---|---|
| 906 {self-test `failure`, L1 `skipped`}, 905 {both `success`} | `(None, "CI run 905 … success …")` → **rc 0** | red: master's newest post-squash run failed |
| 906 {Typecheck `failure`, self-test `skipped`, L1 `skipped`}, 905 {both `success`} | **rc 0** | red |
| 906 {self-test `failure`, L1 `skipped`} (the squash's own run), 800 {pre-squash} | rc 8 "the squash's run has not completed; wait for it" | rc 7: it completed, and it is red. The operator waits on a run that will never qualify |

Consequences:
1. **A false 0.** The first row is the case the brief asked about: "a run on a commit BEFORE the squash" is handled, but a red run AFTER it is filtered out by the same test that identifies pre-squash runs, and an older green run answers. It is reachable on the one real run whenever a later master push is red while the squash's run was green, and on any re-run (Step 3 of the rewritten Task 13 re-runs this command after the per-PR repairs, which is exactly when later merges will have landed).
2. **The rc 7 case tests a world GitHub cannot produce.** Case "730 L2: … with its self-test red, is rc 7" feeds `{self-test: failure, L1: success}` — a self-test red with the later L1 step still running. In the real job a self-test red skips L1, which this code turns into rc 8 or rc 0, never 7. The case and its mutation ("a red self-test step … reads as green") are green against an impossible input.
3. **The only reachable rc 7 has no case.** With all earlier steps green, the only real red is L1 itself `failure`. Mutation `not in ("success", "failure")` → `!= "success"` (an L1 failure skipped to the next run) **survives** the whole self-test.

Fix direction: decide "at or after the squash" from the run's COMMIT, not from step presence. For example, a run is post-squash when its `headSha`'s `scripts/check-ask-store.py` contains `GATE_L1_MARKER` (`git cat-file` at that sha, after the fetch), or when the squash commit is an ancestor of `headSha`. Then take the NEWEST completed post-squash run and require both steps `success`; `skipped`, `cancelled` or absent there is red (or "not yet" only when the run is not completed). Add cases using GitHub's real shapes: self-test `failure` + L1 `skipped` → rc 7; L1 `failure` → rc 7; a red newest post-squash run over an older green one → rc 7, not 0. Consider also requiring `headSha == origin/master`'s tip, or saying in the ok line that an older run answered (today the rc table's "0: all four green" overstates).

### M2 (MEDIUM) — the error paths that would turn a `gh`/git failure into rc 0 have no case

The code currently routes each `err` correctly, but nothing can turn red if it stops doing so. The brief names "a gh error" as a false-0 input. Hand-applied in the archive copy, the self-test still passes 139/139 with each of these (all SURVIVE):

| Mutation | Effect on the real run |
|---|---|
| `prs, prs_err = store_edit_prs(); prs_err = None` | a failed or full-page `gh pr list` (PR_LIST_LIMIT) → **rc 0** with "no open pull request edits the frozen store" |
| `gh run view` failure → `continue` | an older green run answers, so **rc 0** (or rc 8) instead of 2 |
| A1's `a1_err` dropped | a git failure reading `docs/asks/` → rc 0 |
| L1's err dropped (`legacy_store_check(...)[0], None`) | a git failure reading the store → rc 0 |
| `gh run list`'s parse error → `runs = []` | rc 8 instead of 2 (not a false 0) |
| L1 step `failure` skipped (see M1.3) | — |

Only "order drops `PC_CI_RED`" of my seven was killed. Add at minimum: `gh pr list` failing under `--post-cutover` → rc 2; `gh run view` failing → rc 2. These are two more `_pc_gh` table entries (`pr_list_rc`, `run_view_rc`), with a mutation each. The A1/L1 git-error paths after a successful fetch are harder to drive. Filing them with a stated bound is acceptable.

### M3 (MEDIUM/LOW) — the plan's Step 1 command brings back r5 M1's "exit 1 means three things"

`docs/superpowers/plans/2026-11-24-dashboard-retire.md`, Task 13 Step 1:

```
cd <a checkout of origin/master> && git fetch -q origin master && git checkout -q --detach origin/master && python3 scripts/check-ask-store.py --post-cutover
```

The command's exit status is what the new rc table is read against. But a `cd` into a missing path exits **1**, and a `git checkout --detach` blocked by a local edit exits **1**. Both read as table row 1, "master's store moved". That is r5 M1 word for word, now in the documented invocation of the command built to remove it. Similarly, before the squash the chain ends in `python3: can't open file` (rc 2, per the old text's own control), so the table's rc 3 "no gate file" row cannot be reached through the documented command. It reads as CANNOT RUN instead. Fix: say the status is the script's only when the last line printed is `post-cutover rc N`, and read N from that line. Or replace the `cd`/`checkout` with `git worktree add --detach <fresh path> origin/master` and run the script there, a step with no prior state to collide with. Either way, add a sentence on what a 1 without that last line means.

### L1 (LOW) — the fetch relies on the opportunistic remote-tracking update

`_ask_git(root, "fetch", "-q", remote, branch)` updates `refs/remotes/origin/master` only because this clone's `remote.origin.fetch` is `+refs/heads/*:refs/remotes/origin/*` (checked). A clone with a narrower refspec (`--single-branch` of another branch) fetches into `FETCH_HEAD` only. `origin/master` then stays stale, and the stale tree is judged. If the stale ref is pre-squash, the result is rc 3, safe. If it is post-squash but older, a store that moved since is missed. Fix: an explicit refspec, `fetch -q <remote> +refs/heads/<branch>:refs/remotes/<remote>/<branch>`. This costs nothing, and the existing "skips its fetch" case already guards it.

### L2 (LOW) — steps are merged across jobs by name

`steps = {s["name"]: ... for j in jobs for s in j["steps"]}`: a later job's same-named step overwrites the earlier one. No collision exists today (master pushes run `verify` only, ci.yml:17-21). Keying on the `verify` job's steps would remove the hazard.

## Checked and not a finding

- A locally modified or stale `check-ask-store.py` judging master: refused by the blob-id comparison (rc 4). The comparison runs before any check, and the mutation removing it is killed. Pins live in the same file, so L1 judges master's store against master's pins.
- A dirty worktree: L1, A1 and the gate all read through `ls-tree`/`cat-file` at the fetched ref, and the dirty-worktree case is killed by the working-tree-A1 mutation.
- The gate file not yet on `origin/master`: rc 3 runs before rc 4, so a newer script run from another checkout gets the right cause. (Verified: today's `origin/master` has no `scripts/check-ask-store.py` at all, so rc 3's "no gate file" branch is the real pre-squash state.)
- Whether the `ask store (push)` step existed before S2: it is absent from `origin/master`'s `ci.yml`, so step presence does identify post-squash runs (M1 is about step ABSENCE, not presence).
- The gh page limit: `store_edit_prs` refuses a full page as CANNOT RUN (but see M2: that err is unguarded under `--post-cutover`). `RUN_LIST_LIMIT` 20 exhausting without an L1 run gives rc 8, not 0.
- Counts: 12 impure cases, 13 mutations, `expected_mutations.py` 71 → 84. All three match the diff.
- L3 (12.3 vs 12.10) is fixed in Task 13's **Test:** line. L4 (the carried-findings cell): NOT CHECKED in this round.

VERDICT: NOT CONVERGED
