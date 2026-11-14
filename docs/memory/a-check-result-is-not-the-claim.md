---
name: a-check-result-is-not-the-claim
description: "FIRES-WHEN: about to quote a green check as evidence, read a red one, read an exit code, or reset/restore a branch — ⭐⭐ green says nothing about the BASE (use `origin/master`, READ THE FILE LIST); a red is a STOP (it hid a second failure); never read `$?` after a PIPE; say the DENOMINATOR; diff the old tip BEFORE `reset --hard` (a 32KB review was lost)"
metadata:
  type: feedback
---

> Merged 2 memories. Former names (still referenced by other memories): `a-green-check-says-nothing-about-the-branch-base`, `a-red-check-is-a-stop`

**The rule: a check result is a claim about what the check READ, not about what you care about.** Before quoting
one, ask: *what would this look like if the thing I care about were wrong?* — and *would it still pass if the thing
had been deleted?*

**How to apply (current):**
1. **Branch scope against `origin/master`, never bare `master`** — `git log --oneline origin/master..HEAD` (expect
   EXACTLY your commits), `git diff --stat origin/master..HEAD`. Cut branches with `git checkout -b <name> origin/master`.
   **Read the FILE LIST of any review package or PR before dispatching it** — a filename that has no business there is
   the cheapest detector, and the one that worked.
2. **A red check is a STOP.** Merge only when (a) `gh pr view N --json headRefOid` equals local `HEAD` and the tree is
   clean (re-check after pushing), (b) there is a green run on THAT commit, never an explanation of why a red one does
   not count, (c) you remember steps after a failing step **did not run** — an early failure hides later ones.
3. **Exit codes:** never read `$?` after a pipe (`$?` is the LAST stage's) — use `${PIPESTATUS[0]}`, `set -o pipefail`,
   or redirect to a file. `A | head || echo MISSING` can NEVER fire (`grep|head`, `grep|wc -l`, `grep|cut` all exit 0) —
   use `grep -q`/`grep -c` and read the number. `rc=$?` goes on its own line right after the command. A background
   notification's "exit code 0" and a `gh run watch --exit-status` rc are not the command's/CI's verdict — read the log,
   `gh pr checks`, `check-merge-ready`. **Gate, don't echo:** guards and the commit go in separate calls, or chain
   `python3 a && python3 b && git commit` — an `echo rc=` is a report, not a gate.
4. **Run the gate against what CI reads.** Commit first, then run gates that read the committed diff
   (`check-dashboard-entry.py`), or pass CI's `--base`. Gate on the exact ref being pushed
   (`--head $(git rev-parse <branch>)`), never on HEAD mid-rebase. A CI RE-RUN replays the frozen event payload — only a
   PUSH reads an edited PR body.
5. **Run every guard whose population includes the changed file**, not just its own suite
   (`grep -rln "$(basename CHANGED.py)" scripts/*.py scripts/mutations/*.json`). A new call site can turn a guard red
   without changing its rule. **Derive the CI list from `.github/workflows/ci.yml` at the moment of running** (Python
   `re`, not BSD `sed`), never from a scratch file; a fresh worktree needs the `node_modules` symlink.
6. **Say the denominator, every time:** "73/73 CI check steps", "2 of 3 required contexts; the sweep did not run" —
   never "every", "all the guards", "CI is green". A RUN has a conclusion and so does each JOB; read
   `gh run view --json conclusion` before saying *green* (`cancel-in-progress` can cancel a green run retroactively).
   ⛔ **Never write a CI claim into the commit that changes CI's inputs** — that is a forecast, not an observation.
7. ⛔ **Before any `reset --hard`, `checkout -f`, force-push or branch-ref move: record the old tip and
   `git diff --name-only <target>..<old-tip>`**; restore from THAT list, and tag the old tip if no other ref reaches it.
8. **Verify a negative result against a known-positive control** (patterns that wrap lines, wrong selectors and
   off-by-one `tail -n +N` all report absence of something present).
9. **A setting verified in a FRESH process is not live in the CURRENT one** — ask which process reads it and when.
10. **A mutation's named case can pass for an ambient reason inside the case** — run the mutation scoped after every
    case edit.

**Why:** every instance below was a real measurement, right about what it read and silent or wrong about the
question asked. The worst form ANSWERS AFFIRMATIVELY about the wrong subject, because it feels like verification.

## History (measured)

- **2026-08-24, PR #146** (*"Documentation only"*, 3 files) squash-merged as `329b7f5` with **6 files** — all of PR #144
  — because the branch was cut from #144's branch. Head-SHA check `success`, `mergeStateStatus` `CLEAN`, my reviewed
  diff, 5 ratchets at 0: none can see the base.
- **2026-09-19, `feature-hub-spec`:** LOCAL `master` was two PRs stale. `git rev-list --count HEAD..master` → **`0`**,
  reported as "not behind". The review package was **20 commits / 50 files / 581 KB / 8,126 insertions** including all
  of PR #322; the true branch was **19 commits / 24 files / 4,347 insertions**. Caught by `fly.worker.toml` in the
  diffstat — *a number would not have caught it; a filename did.*
- **2026-08-24, PR #134:** `verify=fail`, I "recognised" an already-fixed `check-docs` error and merged; master went red.
  The fix had been pushed after GitHub resolved the merge head. And `check-arch-findings` had **never run** (CI stops at
  the first failure) — three findings past baseline were hidden. I ran five ratchets locally; there were six.
- **2026-09-22:** committed `02218390` after `check-banner-armed.py --self-test` (150/150) and the 912-mutation sweep;
  `check-fixture-variation.py` was RED on that file (`rc=1` at head, `rc=0` on master) — the fold gave `flush_line` its
  first call sites. See [[exercise-the-producer-at-two-distinct-inputs]].
- **2026-09-22:** `check-dashboard-entry.py` rc=0 on the working tree, CI **REFUSED** the committed merge resolution.
  Same session, `rc=$?` read after an `echo` twice, including a 35-min sweep whose log said `NOT MEASURED`.
- **2026-09-26:** `check-dashboard-entry.py 2>&1 | tail -4; echo "rc=$?"` printed `rc=0` under REFUSED; and
  `grep … | head -5 || echo "NO REFERENCE"` — a check structurally incapable of the failing answer
  ([[a-test-that-cannot-fail]]).
- **2026-09-26, the costliest:** `git reset --hard b8a8a828` discarded two commits; I restored the 8 files of ONE of
  them. `velocity-backfill-r3-claude.md` (**32,331 bytes**) came from the other, PR #348 merged without it, and a later
  `git gc --prune=now` collected it — **unrecoverable**. My check ("are those 8 files back?") could only confirm what I
  did. `check-review-rounds.py` said *"0 silent gaps"* — a round with no documents leaves nothing to check. And a
  `-RECONSTRUCTED.md` suffix would have made the round invisible to `check-review-rounds.parse()` — put a label where
  the READER looks, identify the reader first. See [[after-fixing-search-for-the-class]].
- **2026-10-21, 3× in one session:** "the full `ci.yml` guard list" was **6 of 62**; "REAL CI IS GREEN" over a run whose
  conclusion was **cancelled** (6 of 8 sweep shards cancelled); "`6ca7abc0` success" was one JOB of a failed run; a
  dashboard entry claiming checks pass sat in the commit that put `verify` red; and `| head -5; echo "rc=$?"` again,
  in the script written to confirm the fix.
- **2026-10-24:** twice printed `ds=1` and committed on the next line (`check-decision-scheme`).
- **2026-10-26 night:** `gh run watch --exit-status` returned 0 over a red `verify` (superseded run); `gh run rerun`
  after adding `NO-REVIEW:` changed nothing; three mutation cases passed for ambient reasons.
- **2026-10-29:** a gate scanned HEAD while a rebase had STOPPED on a conflict (`hits: 0` over 0 lines).
- **2026-10-30/31:** reported `autoCompactWindow=300000` as live from a test `claude -p`; the coordinator ran on at
  592k/1000k until the owner saw the HUD.
- **2026-11-04:** reported "every CI `check-*` step passes" four times over `gates499b.txt` — the **3 PR-only gates**;
  the full list was 73, and `check-decision-scheme.py` was red throughout.

Same family: [[a-measurement-is-only-as-good-as-its-corpus]], [[measure-the-population-the-code-actually-sees]],
[[an-inference-stated-as-measured]], [[a-positional-read-needs-a-verified-shape]],
[[a-convention-catches-what-you-read]], [[a-hang-is-not-a-diagnosis]].
