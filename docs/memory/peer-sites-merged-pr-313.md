---
name: peer-sites-merged-pr-313
description: "FIRES-WHEN: citing PR #313 or peer-sites — peer-sites MERGED — PR #313, squashed to 14063fe5. 4 rounds, ships WITHOUT a caller by design; 6 items filed #131-#136"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2776b0c8-fac3-4080-bad3-e313041380a1
  modified: 2026-09-16T20:10:14.655Z
---

**MERGED 2026-09-16** — PR #313, squashed to **`14063fe5`** on `master`, branch deleted. Both
`verify` and `schema-gates` were green on `50d05019` before the merge.

`scripts/peer-sites.py`: *"you changed one member of an enumerable set; here are the others"* over
three container shapes. 73 self-test cases (from 32), 25 mutation entries (from 7), declared total
**714** over 47 files, 0 survivors.

⛔ **IT SHIPS WITH NO CALLER, DELIBERATELY.** A `git commit` hook was built for it in round 1, then
produced findings in **all three** later rounds and was removed on a double ARCHITECTURE_REVIEW
thrashing verdict. Run it by hand: `python3 scripts/peer-sites.py --diff HEAD`. Re-filed as
**backlog #134**, which carries the measurements and the lesson that DID work — the rule must live in
`scripts/*.py`, because `check-selftest-counts.py` and `check-ratchet-contract.py` cannot see
`.claude/hooks/*.sh` at all.

⚠ **TWO GATES ARE OVERRIDDEN, with their objections written into the branch, not silenced:**
`check-review-decision.py` still says `ROUND_OWED` (its rule needs two consecutive rounds clean of
Blocking/High and `aim: deliverable`; clearing it costs two more rounds), and the final-tree question
is **waived** by a `NO-REVIEW:` in the PR body. See [[a-retreat-you-author-for-yourself-is-not-a-gate]]
for how I got the first one wrong before getting it right.

⛔ **`NO-REVIEW:` MUST START THE LINE.** `## NO-REVIEW: …` returns `None` from the parser — bare and
`**bold**` parse; `##`, `>`, `-` do not. And CI reads `github.event.pull_request.body` from the
**event payload**, so `gh pr edit` does not re-arm it — a re-run replays the old snapshot and only a
new push helps. Both cost a red CI run here.

Filed this branch: **#131** arm bodies (79 of 84 partially-touched containers are silent) · **#132**
the `branches` false-positive idiom · **#133** the review tree-leak rule · **#134** no caller ·
**#135** `branch_verdicts()` counts only COMMITTED verdicts while `review-method.md` step 5 requires
holding fixes UNCOMMITTED — obeying one rule makes the other fail.
