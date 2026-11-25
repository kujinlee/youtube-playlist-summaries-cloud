Reviewed head: 0fb68ffe141076d65ab133acc764e24c48befcf9

# dashboard-retire plan — round 3, Claude half (adversarial)

Subject: `docs/superpowers/plans/2026-11-24-dashboard-retire.md` (1003 lines, read whole) against the approved spec
`docs/superpowers/specs/2026-11-24-dashboard-retire-design.md`. Round 3 of 3 before the cap (r4+ folds BLOCKERs only).
Codex took r2; this half was briefed to try first to REFUTE the r1/r2 fixes, then sweep for CI-only reds and broken
mutation anchors. Experiments ran on copies under the session scratchpad `plan-r3-claude/`; nothing in the repository
was modified except this file.

## Findings

### MAJOR 1 — cases 2.13 and 12.11 call git on the LIVE tree, and the mutation harness stages a tree with no `.git`

**Evidence.**
- Plan Task 2 table, case 2.13 (plan:~270): "the live tree passes | this repo, `docs/asks/.gitkeep` only | `([], None)`".
  A1 is `git ls-tree HEAD docs/asks/`, so a live case reaches git with `cwd=ROOT`.
- Plan Task 12 table, case 12.11 (plan:715): "live: `git hash-object` and SHA-256 of the store at HEAD;
  `git rev-parse <pin-base>:docs/dashboard-entries.md` | equal to the constants". Step 1 (plan:722–725) says 12.11
  "alone is live and patches nothing".
- `scripts/check-plan-code.py` `HARNESS_TREE` (~:471) has no `.git` entry, and `stage_tree` (~:973–1009) copies the
  tree into a temp dir. `.github/workflows/ci.yml:1427` says the sweep "copies the tree into a temp dir with no `.git`
  at all".
- Measured in a plain (non-repo) directory: `git ls-tree --name-only HEAD docs/asks/` → rc 128;
  `git rev-parse HEAD:docs/f` → rc 128 (`git hash-object docs/f` → rc 0, so only the HEAD/rev-parse halves die).
- `fixture_git.isolated()` isolates git's env and config and gives a temp TMPDIR. It does not create a repo, so it
  cannot rescue a live case.

**Consequence.** Inside the staged tree, `--self-test` fails 2.13 (and 12.11 once Task 12 lands). The harness needs a
GREEN control before and after mutating. A red control means every manifest entry for this gate is reported NOT
MEASURED or refused. That happens locally (Task 2 Step 7, Task 12 Step 8) and in CI's PR-selected and nightly sweeps.
The gate's mutations, including Task 3's sever and the A1/F1/L1 entries the plan adds, can then never fail. Precedent
for the failure mode: `scripts/check-review-recorded.py:1444` raises CANNOT RUN without `.git` instead of running.

**Fix.**
- Build 2.13 on a `fixture_git` temp repository holding exactly `docs/asks/.gitkeep`, with `ROOT`/cwd pointed at it.
- Move 12.11's live comparison out of `--self-test` into `main`, as part of L1, where CI runs it on a real checkout.
  Alternatively, give it its own CI step, or run it on a fixture repo whose blob is computed in the case.
- Add one line under Task 2 Step 7: "the control must be green in the staged tree", run with
  `check-plan-code.py --mutate . --only check-ask-store`.

### MAJOR 2 — 12.11's `<pin-base>` is never defined in code, and its derivable readings go red on master after S2

**Evidence.**
- Plan:715 compares against `git rev-parse <pin-base>:docs/dashboard-entries.md`. Task 12 Step 4 (plan:728–729)
  records the pin-base only in the commit message, and no constant or argument names it.
- The cases can derive it only as `origin/master`, `--base` or the merge-base. After S2's squash, master's store blob
  is `LEGACY_STORE_BLOB` (the header-only file). That differs from `LEGACY_STORE_BASE_BLOB` (the pre-cutover file), so
  every one of those readings fails on master.
- The failure persists until Task 16 deletes `LEGACY_STORE_BASE_BLOB` in S3 (plan:951–957). Task 13 Step 4
  (plan:820–821) confirms only the `ask store (push)` step on master, not the self-test step.

**Consequence.** The `check-ask-store self-test` CI step goes red on master pushes and every PR opened between S2 and S3.
Alternatively, the implementer guesses a reading that passes trivially, and the gate cannot fail.

**Fix.** Pick one:
- (a) Add a `LEGACY_STORE_PIN_BASE = "<40-hex sha>"` constant. 12.11 reads `git rev-parse $PIN_BASE:…`, and a missing
  object is CANNOT RUN, not a pass.
- (b) Drop the BASE half of 12.11, since `--cutover-check <squash>^1` in Task 13 already asserts the pre-cutover blob
  against the real parent. Keep only the HEAD half, moved per MAJOR 1.

Also extend Task 13 Step 4 to confirm the self-test step on the master push.

### MINOR 3 — Task 3's sever anchor is fixed before Step 3 restructures the line it anchors

**Evidence.** The Task 3 Step 5 sever (plan:372–378) anchors on `needs_from_dashboard),` and replaces it with
`lambda _t: ([], [])),`. Today that token occurs once, in the source loop at `scripts/goal-tree.py:1563`
(`for key, rel, fn in (("dashboard", DASHBOARD_REL, needs_from_dashboard), …`). Task 3 Step 3 (plan:346–348)
rewrites that loop to read the ask store, and nothing says the tuple keeps that exact text.

**Fix.** Either state the loop's post-Step-3 shape, so the anchor is known to survive, or say "take the anchor from
the implemented line, then run the all-manifest anchor resolve". Expect case 3.9 to go red.

### MINOR 4 — Task 13 Step 1 runs `--cutover-check` from an unspecified checkout

**Evidence.** Plan:789–812 finds the squash through `gh pr view … --json mergeCommit`, checks the parent count, then
runs `python3 scripts/check-ask-store.py --cutover-check "$SQ^1"`. It does not say where that runs. In the main
checkout, before a fast-forward, the script does not exist yet (it is still `check-dashboard-entry.py`).

**Fix.** Run `git show "$SQ:scripts/check-ask-store.py" | python3 - --cutover-check "$SQ^1"`, or name the S2 worktree,
fast-forwarded to `$SQ`, as the cwd.

### MINOR 5 — Step 5b says "the same count as Step 5", but `tail -1` shows only the impure suite's line

**Evidence.** Step 5b (plan:296–310) pipes `--self-test` through `tail -1` under `set -o pipefail`. The gate prints two
summary lines (pure, then impure; `check-dashboard-entry.py` `main` ~:1485 and `check-selftest-counts.py:512`'s stated
limit), so the last line is the impure count alone. Step 5's count is not the same quantity.

**Fix.** Compare both lines (`tail -2`), or name the impure count explicitly.

## r1/r2 fixes tested and held (refutation attempted, failed)

- **Step 5b with `pipefail`.** I tested its logic and its control. The `wc -w` padding (`[       2]`) inside
  `test "$(… | wc -w)" -eq 2` is harmless: rc 0, measured.
- **Task 9 Step 6b (CI repoint).** I applied Task 9's edit to a copy of `ci.yml` and ran the Step 6b awk/grep block:
  rc 0, the step names `check-ask-store.py`, carries no `--pr-body-file`/`BODY`, and exactly one `--pr-body-file`
  remains (the `check-review-recorded` step at ci.yml:1130–1138). It still goes red if the step keeps a body flag.
- **Tasks 12/13: `store_edit_prs`, the `mergeCommit` jq select, `^1` syntax, parent-count chain.** All are correct.
  CI's merge-commit L1 detects master moving under the PR.
- **Task 2 stubs and A1's error case.** 2.12/2.14/2.15 stub `_run` correctly. A1's rc≠0 path is CANNOT RUN, not a
  pass. 2.13 is the only defect (MAJOR 1).
- **`check-merge-ready.py` `_gate_main` fixtures (:4171–4280).** They fake `_run`, so neither A1 nor the rename reaches
  them.
- **Guard tables naming the renamed file.** Plan:515–531 names `check-fixture-variation.py` (whose `EXAMINED_KEYS`
  pins `check-dashboard-entry.py`; a departure is CANNOT RUN), `check-main-drivable.py`, `check-plan-code.py`,
  `check-shipping-sets.py`, `check-ratchet-contract.py`, `check-fixture-git-isolation.py`,
  `check-selftest-counts.py` and the manifests. That matches a `git grep` of live references, with no omission found.

## Severity note

Neither MAJOR is a BLOCKER in the plan as written: both surface as red gates before merge (the local sweep in Task 2
Step 7, and CI) rather than shipping wrong behaviour. But MAJOR 1, left unfixed, would be "fixed" most cheaply by
dropping the live case, and MAJOR 2 by an implementer choosing a trivially-passing pin-base. Both would leave a check
unable to fail, which is why they are MAJOR rather than MINOR.

VERDICT: NOT CONVERGED
