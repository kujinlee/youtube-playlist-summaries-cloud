# Round 3 — `batch-ci` (PR #529, backlog #534) — coordinator — Codex half NOT CONVERGED; THRASHING → Phase 6; 3 of 3 findings FIXED

REVIEW GAP: claude — alternation (round 3 runs the Codex half)

```yaml
round: 3
fixes_nontrivial: true
subject: batch-ci
halves:
  codex: ran
  claude: gap
findings:
  - {id: R3-F1, severity: High, aim: deliverable, fix_induced: true, component: union, disposition: fixed}
  - {id: R3-F2, severity: Medium, aim: deliverable, fix_induced: true, component: union, disposition: fixed}
  - {id: R3-F3, severity: Low, aim: deliverable, fix_induced: false, component: plan, disposition: fixed}
```

Codex (`docs/reviews/codex/batch-ci-r3-codex.md`, on `3688c4fe`, per its verdict record), filed at `7df960aa`. Folded in the commit that adds
this file. Nothing declined, refuted or filed as a finding. Each fix has a self-test case that goes red with the fix
reverted. Each revert is a mutation in `scripts/mutations/batch-ci.json`, and each new mutation was applied by hand to a
scratch copy of `scripts/` and shown red on its named cases (14 of 14). CI's full sweep is the real gate.

## Thrashing fired the Phase 6 review

R3-F1 and R3-F2 were both caused by round 2's fix to the docs union (`a1bdd0ca`):
- R3-F1: r2's `_moved` checked sections over ONE conflict hunk, and that scope was its own design.
- R3-F2: r2's rewrite of the `blocks` branch dropped `_added(theirs, …)`.

Round 2's R2-F1 was itself round 1's fix left incomplete. So two consecutive rounds (r2→r3) carried findings caused by
the previous round's fix, in one component. That is the arming condition in `docs/dev-process.md` → *Phases*.

The narrow Phase 6 review is `docs/reviews/architecture-review-2026-11-07-batch-ci-docs-union.md` (`4e4678fb`). It
found that the defect class is *a placement decided per hunk and validated per hunk*. It also found that git can
misplace a line with NO conflict (R3-F1-CLEAN), which no resolver change can reach. It chose option (a): one
whole-file postcondition, on every merge step, that EJECTS on a violation. This fold builds that, and does not patch the
resolvers a fourth time.

**The stop condition it proposes, adopted here.** After r4, a review finding against the union resolvers is a BLOCKER
only if it shows the postcondition HOLDING on a wrong tree. "The resolver ejects a member it could have resolved" is Low
and FILED, never folded under the round cap.

## The fixes

**R3-F1 (High) and R3-F2 (Medium): `postcondition` (§4), with its call site on BOTH paths.**
- `postcondition(base, ours, theirs, result, policy)` is pure. It implements P1–P4, P6 and P7, plus the prefix cut,
  as §4.2–4.3 define them.
- `merge_into` calls `_checked` after a CLEAN merge and after a resolved one. For each union file that both sides
  changed, it reads B, O and T with `git show` and R from the worktree. A violation aborts the merge and returns
  `"<file>: <first violation>"`, so the member is ejected exactly like an unresolvable conflict.
- `git merge-base --all` printing several bases, with a union file changed on both sides, is refused.
- A `git` failure while reading is CANNOT RUN. The merge is aborted first, and an empty read is never treated as an
  empty file.
- `_moved` and `_sections` are deleted, with their two manifest entries and their one pure case. R3-F2's suggested
  "restore `_added(theirs, …)`" is NOT done: P3 covers it from outside the resolver, as §5 says.

**R3-F3 (Low): `plan` creates its worktree INSIDE the clean-up `try/finally`.** Git can create `batch/<time>` and then
fail the checkout. The branch did not exist when `plan` checked a few lines earlier (it refuses if it does), so a branch
of that name afterwards is this run's own, and the existing `if not done` clean-up deletes it.

| Finding | Disposition | The case that goes red without the fix |
|---|---|---|
| R3-F1 (High) | fixed: `postcondition` P4 + call site on both paths | `⛔ PC15 R3-F1-CLEAN` (clean path), `⛔ PC16` (one hunk, through real git), `⛔ PC2` (pure) |
| R3-F2 (Medium) | fixed: `postcondition` P3 | `⛔ PC17` (through real git), `⛔ PC1` (pure) |
| R3-F3 (Low) | fixed: worktree inside the `try` | `⛔ R3-F3: a worktree creation that made the branch and then FAILED …` |

## Where this fold departs from the review's §5, measured

1. **"The correct output for case 2" does not exist.** Ours orders `existing` before its new thread. Theirs moves
   `existing` under a heading that it inserted after the product section's head. So no arrangement keeps both ours'
   order and both sections. All 120 arrangements of the tail fail, under the self-test and under the review's own
   prototype `pc.py`. Case 2's shape is a real conflict, so it EJECTS whatever the resolver writes. `PC5` asserts the
   correct outputs of cases 1, 3 and 4, and `PC5b` asserts that case 2 has none.
2. **The mutation "the prefix cut's `c` set to `n`" is EQUIVALENT, so it is not added.** Dropping the shared heading
   relabels that section's identity to `None` in all four lists alike. No clause compares a heading's identity with
   anything outside them. It survived all 168 cases in a scratch copy. In its place:
   - "the cut not applied to the result" (red on PC5 and PC14, and 25 cases in all);
   - "P6 reads only the part after the cut" (red on `PC6b`).
3. **P6 reads the WHOLE result, not the cut.** A backlog row number reused from a section above the last shared heading
   is a duplicate. Under the cut alone it is invisible. `PC6b` is that case.
4. **Two existing real-git cases now expect an ejection** (§6 bound 3, and backlog 549):
   - the same dashboard entry appended by both members;
   - a decision record both members added.

   The plain decision-log case keeps its "each side's records land" form, with distinct records.
5. **Case 20 is green on the postcondition-free code by construction.** It asserts an ABSENCE: the postcondition is not
   called when one side left the file alone. Its falsifier is the mutation "a union file one side left alone is
   checked anyway", which is red on it.

## Filed, not built (the review's §7)

- **backlog 546:** the `rows` policy re-sorts base rows (Low, `defect`). Self-test case `PC7` makes it an ejection today.
- **backlog 547:** option (d1), deleting the `blocks` placement logic.
- **backlog 548:** the blank-line clause (the would-be P5), measure first.
- **backlog 549:** an identical addition on both sides ejects.

## Gates at the fold

- `batch-ci.py --self-test`: 168/168.
- The harness's own `load_manifests`, `anchor_problems` and `pin_drift`: clean. The manifest went 83 → 95.
- The batch-ci mutation slice was NOT run locally, at about 70 s per mutation. Each new mutation was applied by hand
  instead (above).
