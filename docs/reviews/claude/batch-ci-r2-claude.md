Reviewed head: 8d84b0142a55e8a6cf0423e8b167f167907e48a7

# batch-ci (PR #529, backlog #534): round 2, Claude half (adversarial, mandate REFUTE)

The Codex half is skipped this round by alternation.

Every experiment ran on a scratch copy (`git archive HEAD | tar -x`) or in throwaway git repositories. Nothing in
the worktree was touched except this file, and GitHub was not contacted.

## Job 1: are the round-1 fixes real?

- `python3 scripts/batch-ci.py --self-test` at HEAD: **123/123**, rc 0.
- `python3 scripts/check-merge-ready.py --self-test` at HEAD: **348/348**, rc 0.
- **All 68 mutations in `scripts/mutations/batch-ci.json` were applied one at a time** to a copy of `scripts/`,
  and the self-test was re-run each time, six at a time. The harness itself took about 70 s per mutation, so I
  ran a stand-in instead. Result: **68/68 went red, and in every one the `[FAIL]` lines included each `expect`
  label the entry names.** No mutation survived, and none was killed only by some other case. That covers every
  fold item: R1-F1 (admission, the HOLD refusal and the re-ask in land), C1/R1-F3 (master did not move, the
  predicted squash), C2 (the base re-read), C3/R1-F4 (`latest_run`, `classify`), C4/R1-F2 (block union), C5/R1-F5
  (closure and call site), R1-F6, R1-F7's eleven survivors, and C-refresh.
- Every anchor in `batch-ci.json` (68) and in the merged `check-merge-ready.json` (156) is still present in its
  target, and there are no duplicate names. I did not sweep check-merge-ready's 156 entries. The self-test passes,
  and every anchor binds.
- The #508 merge (`8d84b014`): `git diff 88a2752d HEAD -- scripts/check-merge-ready.py` contains only the batch
  additions and the re-keyed `ACCOUNTED_MENTIONS` entry for the new alert `if:`. `verdict`, `mergeability`,
  `hold_reasons`, `final_verdict`, `review_answers` and `tree_matches` are byte-identical to master's, so the
  merge itself does not change what READY or HOLD means. The advisory line stays outside `results`. Each call
  carries the 15 s timeout, and any exception becomes `info`. I found no way for it to stall the checker or move
  its verdict.

The fixes are real. What follows is what the fold left open, or what it introduced in combination with #508.

### R2-F1 — High — block union reattaches a headless addition to the OTHER side's new section (goal threads land under the wrong goal)

`scripts/batch-ci.py:296-304` (`resolve_hunk`, policy `blocks`), applied to `docs/goal-threads.md` and `docs/dashboard-entries.md`

**The defect.** `blocks` returns `ours + theirs' new blocks`.
- That is right when both sides' additions start with a `## ` heading.
- It is wrong when one side adds a new `## ` section and the other adds lines that belong to the section ALREADY
  last in the file. In `docs/goal-threads.md` that is the ordinary operation: a thread is one `- ` line appended
  under its `## GOAL …` section. When the goal is the last section, the line is appended at end-of-file.
- Opening a new goal adds a new `## GOAL` section at end-of-file. `f8aa1ae9` did exactly that ("open GOAL product").

**Reproduced with real git**, through `merge_into(_run, wt, theirs)` from the scratch copy:

- base: `## GOAL dev-speed` / `- fix · one` / `## GOAL product` / `- fix · PR #392 · held`
- ours (the earlier member) appends `## GOAL billing` / `> new goal` / `- fix · PR #600 · billing thing`
- theirs (the later member) appends `- fix · PR #601 · a product thread`

`merge_into` returned `None` (resolved), and the file ends:

```
## GOAL product
- fix · PR #392 · held

## GOAL billing
> new goal
- fix · PR #600 · billing thing
- fix · PR #601 · a product thread
```

PR #601's product thread is now a billing thread. `land` pins master to this tree, so the misfiled thread is what
lands, and the goal tree derived from it shows it under the wrong goal.

`docs/dashboard-entries.md` has the same shape. A side that appends a line to the last existing entry (rather than
opening a new `## date` entry) has that line attached to the other member's new entry. This is the R1-F2 class:
the fold fixed it for heading-led blocks only.

**Fix.** In `blocks`, split each side's added lines into a headless PREFIX (the lines before its first `## `) and
its heading-led blocks. Emit: ours' prefix, theirs' prefix, ours' blocks, theirs' new blocks. A prefix then stays
in the section that was last at the base.
- Alternatively, Refuse (eject) whenever one side's added lines begin headless and the other side added a `## `
  heading.
- Add a real-git case shaped like the one above, to `_e2e_union`.

### R2-F2 — Medium — the import closure still misses real dependencies, and its docstring's safety claim is false: a miss EJECTS the innocent member

`scripts/batch-ci.py:401-433` (`import_closure`, `widen`), and the docstring at :406-409

**The false claim.** The docstring says a missed module "can only turn an eject into a bisect, never the reverse,
because this set only ever GROWS what a failure owns". It grows relative to the round-1 code. Relative to the
truth, a missed dependency SHRINKS what the failure owns. The culprit is then not an owner, and an innocent
member that touched the target becomes the single owner and is ejected. That is C5 / R1-F5 again.

**Reproduced.** I called `attribute(widen(found, read), {3: {"scripts/t.py"}, 9: {culprit}})` for a target
`scripts/t.py` that contains:

```
import os, helper2
m = importlib.import_module('helper3')
subprocess.run(['bash', '.claude/hooks/h.sh'])
X = load('scripts/ci/sub.py')
open('docs/backlog.md')
```

Every culprit below returned `('eject', [3])`, which ejects the innocent PR 3:
- `scripts/helper2.py`: only the first name of `import a, b` is read.
- `scripts/helper3.py`: `import_module` with a module name is not read.
- `.claude/hooks/h.sh`: not a `.py` file.
- `scripts/ci/sub.py`: `PY_LITERAL` keeps only the basename, so it maps to `scripts/sub.py`.
- `docs/backlog.md`: a data file is not read.

**This is not hypothetical in this repository:**
- **The workflow files.** `check-merge-ready.py`'s own self-test reads the real `.github/workflows/*.yml`
  (`unaccounted_mentions(w.read_text(), …)` over `workflow_files(WORKFLOW_DIR)`, and `pr_only_steps(WORKFLOW…)`).
  So if member B adds an unaccounted `pull_request` mention to a workflow, check-merge-ready's control goes red.
  If member A also made a harmless edit to `check-merge-ready.py`, A is told "its diff owns the failing manifest"
  and is ejected, while B stays in the batch.
- **The hook scripts.** 25 of the 89 manifest targets name a `.claude/hooks/*.sh` path.
- **`importlib.import_module`.** 4 targets call it (check-plan-code, codex-review, record-review-verdict,
  check-fixture-git-isolation).

**A second copy of an existing rule.** This is a weaker second copy of a rule that already exists.
`check-plan-code.select_manifests` (`scripts/check-plan-code.py:665`) already answers "which targets does this
diff reach?" for the scoped PR sweep. It also counts a module whose text names the changed path (`_names_of`),
which catches the hook-script and data-file cases above.

**Fix.** Attribute through the harness's own rule: a member owns a failure of target T only if
`select_manifests("pull_request", <that member's diff>, …)` selects T. Then two members can never disagree with
the CI sweep about what reaches T.
- At minimum, EJECT only when every other member's diff is limited to `UNION_FILES`. Otherwise BISECT.
- Correct the docstring either way.
- Add a case with a hook-script dependency and one with a workflow file as the culprit.

### R2-F3 — Medium — the landing refresh and #508's exact-tree answers deadlock: a refreshed member with an answered "loosens a gate" flag is HELD for ever, after its branch was already pushed to

`scripts/batch-ci.py:799-808` (the DIRTY branch of `land`) and `:864-886` (`_refresh`), against
`scripts/check-merge-ready.py:1058-1097` (`review_answers` → `tree_matches`), which arrived with the #508 merge

**The sequence:**
1. `plan` admits a PR with a #508 flagged line. At its reviewed head the final round answered `not a loosening`,
   `tree_matches` holds, and there is no HOLD.
2. The batch goes green. During `land`, an earlier member lands, and this member turns DIRTY: the common case, a
   backlog row.
3. `_merge_ready(…, cur, conflict_ok=True)` is still asked at the OLD head, so it admits. `_refresh` then pushes
   a merge-of-master commit to the PR's branch (an outward act) and stops.
4. On the re-run, `use` is the refresh commit, and `_merge_ready(conflict_ok=False)` runs there.
   - `review_answers` compares the verdict's reviewed tree with HEAD's FULL tree.
   - The refresh's tree contains the earlier members' files, so `tree_matches` is false.
   - Checked directly: `tree_matches(reviewed, {}, reviewed + another member's file)` is `False`.
   - So the answer no longer counts, the flag is a `HOLD loosens a gate …`, and `land` STOPs on
     "not READY now".
5. Nothing short of a new review round on the refresh commit clears it. Every later member is behind it
   (`land` is sequential), so the batch cannot finish.

**Why it fails closed and still matters.** It fails closed, and nothing wrong merges. But the batch premise in the
fold record ("once any member lands, every other open PR … is DIRTY") makes this the expected path, not an edge
case, for any member that relied on a #508 answer. The refresh has already rewritten that PR's branch before the
HOLD is discovered.

**Fix.** Before pushing a refresh, refuse it, without pushing, when the member's diff carries any
`failure_path_flags`. Then it is "re-review needed", and the branch is left as it was. Better, make that test
part of admission, so `plan` does not admit a DIRTY PR whose READY depends on a #508 answer.
- The other way: teach `review_answers` the same "master explains it" allowance that `check-review-recorded`
  already has (`master_explains`), so an answer survives a merge of master that touches none of the flagged
  paths. That is a #508 design change for that row's owner.
- Add an e2e case: an answered-flag member that turns DIRTY at land is refused BEFORE any push.

### R2-F4 — Low — a red whose log names no failure bisects at once, so a flaky or infrastructure-failed shard convicts the newest PR

`scripts/batch-ci.py:383-385` (`attribute`: `if not found: return "bisect"`), `:725-735`

A shard can end `failure` without a mutation or control red. Causes include a runner or setup failure, or one of
the known flakes (backlog #483, #495). Then `failures()` reads nothing, and `status` prints
`BISECT … --exclude <newest>`, rc 1. The re-assembled batch is green because the flake did not recur, so the
operator concludes the newest PR was the culprit. R1-F4 made "cancelled" NO VERDICT. A failure that names nothing
is the same kind of unmeasured red.

**Fix.** When the failed jobs are only sweep shards and `failures()` finds nothing, print
`NO VERDICT — re-run the failed jobs once (gh run rerun <id> --failed)`, rc 2, and bisect only on a second
unattributable red at the same tip.

### R2-F5 — Low — two small seams in `land`, and a stale comment

- `scripts/batch-ci.py:799` decides between the refresh path and the READY path from a `_view` taken right after
  the previous squash. GitHub may return `mergeStateStatus: UNKNOWN` there (see `check-merge-ready.mergeability`'s
  own note, measured on PR #317).
  - In that case a member that is really DIRTY takes the READY path.
  - `_merge_ready(conflict_ok=False)` then reports DIRTY, and the stop reads "is not READY now".
  - What it actually needs is a refresh. A re-run recovers, but the message sends the reader to the wrong cause.
  - Fix: treat `UNKNOWN` at that branch as "re-read before deciding" (one re-`_view`), or name DIRTY in the stop.
- `scripts/mutations/expected_mutations.py`, the `batch-ci.py` pin comment, contradicts itself. It still says
  "Not mutated, on purpose: … `_refresh`'s own tree check", and three lines later "`_refresh`'s pre-push tree
  check IS mutated now". Delete the stale clause.
- `plan` (`:610-631`): a `CannotRun` raised mid-loop (for example from `_merge_ready`'s `_worktree`) drops the
  worktree but leaves the local `batch/<time>` branch. A re-run in the same minute then refuses with "already
  exists". Delete the branch in the same `finally` when `members` was not completed.

VERDICT: NOT CONVERGED
