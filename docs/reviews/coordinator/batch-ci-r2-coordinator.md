# Round 2 — `batch-ci` (PR #529, backlog #534) — coordinator — Claude half NOT CONVERGED; all 5 findings FIXED

REVIEW GAP: codex — alternation (round 2 runs the Claude half; Codex takes round 3)

```yaml
round: 2
fixes_nontrivial: true
subject: batch-ci
halves:
  codex: gap
  claude: ran
findings:
  - {id: R2-F1, severity: High, aim: deliverable, fix_induced: false, component: union, disposition: fixed, commit: a1bdd0ca}
  - {id: R2-F2, severity: Medium, aim: deliverable, fix_induced: true, component: attribution, disposition: fixed, commit: a1bdd0ca}
  - {id: R2-F3, severity: Medium, aim: deliverable, fix_induced: false, component: landing, disposition: fixed, commit: a1bdd0ca}
  - {id: R2-F4, severity: Low, aim: deliverable, fix_induced: false, component: run-verdict, disposition: fixed, commit: a1bdd0ca}
  - {id: R2-F5, severity: Low, aim: deliverable, fix_induced: false, component: landing, disposition: fixed, commit: a1bdd0ca}
```

Claude (`docs/reviews/claude/batch-ci-r2-claude.md`, on `8d84b014`), filed at `d92132ec`, folded in `a1bdd0ca`. Nothing
declined, refuted or filed. Each fix has a self-test case that goes red with the fix reverted, and each revert is a
mutation in `scripts/mutations/batch-ci.json`. `fix_induced`: R2-F2 is marked true because its false safety claim and
its weaker second copy of the selection rule came from round 1's C5/R1-F5 fold. R2-F1 is that round's fix left
incomplete (the headless case was misplaced before round 1 too), not caused by it. R2-F3 arrived with the master merge
of backlog #508.

**R2-F1 (High) — every line stays under its own section heading, or the union is refused.** In `blocks`, theirs'
HEADLESS prefix (its added lines before its first `## `) belongs to the section open where the hunk starts. It now goes
in BEFORE ours' first heading, ahead of the blank lines that lead it, and theirs' heading-led blocks follow ours as
before. Then a check runs, whatever the placement: each line on each side carries an identity (`_tagged`: the k-th base
line of its text, or that side's added line). `_moved` compares the section heading every line sits under in the result
with the one it sat under in the side it came from. Any difference REFUSES the hunk, so the PR is ejected and a wrong
tree is never written. The review's repro is a real-git case through `merge_into` for `goal-threads.md`, with a second
case for `dashboard-entries.md`. A pure case covers the refusal itself.

**R2-F2 (Medium) — one selection rule: the harness's.** `import_closure` and `widen` are deleted. `reached` asks
`check-plan-code.select_manifests` (loaded from beside this file) which targets each member's diff reaches, over the
batch tip's own tree (a temporary worktree). `attribute` counts a member as an owner when its diff touches the
manifest or target, or reaches the target (None = the whole manifest, as for a harness edit). The docstring's false
claim is replaced with the true one: a miss in that rule can still eject an innocent member, and the same miss would
leave the defect unswept on that member's own PR. A selector that cannot run BISECTS and says so; it never attributes.
Cases: a workflow edit reaching check-merge-ready (the review's example) BISECTS rather than ejecting the innocent
check-merge-ready editor. A hook script, `import a, b`'s second name, an `import_module` name and a nested `.py` path
each reach their target. The e2e fixture now has a target that reads `docs/`, as the real gates do.
⚠ **Measured consequence, 2026-11-07, on this tree:** a `docs/backlog.md` edit reaches 64 of the 89 manifest targets,
`docs/dashboard-entries.md` 60, and `docs/goal-threads.md` 53. Nearly every member makes one, so most reds will
BISECT, and an eject survives only for a target that no union-file edit reaches. That is the honest answer: a backlog
row really can break a gate that parses the backlog. A bisect costs sweeps; a wrong eject costs a correct PR.

**R2-F3 (Medium) — decided: a member whose READY rests on exact-tree answers is NEVER refreshed. It goes first, and
it is ejected if it would need a refresh.** The options weighed:
- **Stop refreshing entirely and eject DIRTY members.** Rejected. Once one member lands, every other member that
  appended a backlog row is DIRTY, so each batch would land one PR. That defeats the batch.
- **Teach `review_answers` a "master explains it" allowance.** Rejected here. That is a #508 design change for that
  row's owner, and backlog #544 (binding each answer to the flagged file's blob) is that change, already filed.
- **Chosen: never refresh only the members that depend on exact-tree answers.** A member is answer-bound when its
  diff adds a verdict under `docs/reviews/verdicts/` with a non-empty `loosening_answers`
  (`answer_records`/`_answer_bound`). That is exactly the input `review_answers` reads. Without one, a refresh changes
  nothing that `tree_matches` decides. `VERDICT_DIR` is an independent copy, checked against check-merge-ready's own
  by a case.

How it works:
- `plan` puts answer-bound members FIRST (number order among them) and merges each with `clean_only`. Any conflict at
  its step, even an append-only one, EJECTS it, with the reason "needs re-review after the master merge".
- The first answer-bound member lands onto the very master it was reviewed against, so every batch lands at least one.
  None waits for ever behind lower-numbered PRs.
- `land` keeps a backstop: an answer-bound member that is DIRTY anyway (a batch assembled otherwise) STOPS before any
  push. The message names the re-review and `plan --push --exclude N`.
- So `land` never pushes to a branch it then refuses. Its stop is never permanent either: the exclude re-assembles the
  rest.

A comment at both sites says #544 would make the refresh safe. Cases: plan's ordering and its ejection of a second
answer-bound member through real git, plus land's backstop on a hand-built batch whose answer-bound member is second.
The backstop case asserts that the PR head is unchanged.

**R2-F4 (Low):** a red whose sweep-shard log names no failing mutation or control is NO VERDICT, rc 2, the FIRST time
at a tip (`first_red`: attempt 1, and no other red run at the tip). It prints `gh run rerun <id> --failed`. A second
such red bisects. Cases cover the pure rule and both e2e steps.

**R2-F5 (Low):**
- **UNKNOWN mergeability.** At the refresh-or-READY branch, UNKNOWN is re-read up to `MERGEABILITY_POLLS` (4) times,
  3 s apart. If it is still UNKNOWN, `land` STOPS, pushing nothing. The e2e asserts the bound (4 pauses) and that an
  UNKNOWN which turns DIRTY takes the refresh path.
- **The pin comment.** The `expected_mutations.py` comment no longer contradicts itself.
- **`plan` failing part-way.** It now deletes its own local `batch/<time>` branch (only one it created), so a re-run in
  the same minute is not refused.

**Counts:** self-test 123 -> 145 (derived from the run). Manifest 68 -> 83: 4 retired with the closure, 5 re-bound
(four anchors moved by the union rewrite, and the call site's), 19 added. Pin 68 -> 83, with its comment.
`check-fixture-variation`'s keys for batch-ci were re-derived with `analyse()` (41 -> 47), and two exemptions that went
dead were deleted.

**Mutation evidence:**
- The local harness slice (`--mutate . --only scripts/batch-ci.py --allow-long-local`) was NOT RUN. At about 70 s per
  mutation, 83 mutations is about 97 minutes, over this fold's 45-minute bound. The CI full sweep on push is the gate.
- Instead, a stand-in applied each manifest entry to a copy of `scripts/`, ran the self-test, and required a `[FAIL]` on
  every `expect` label the entry names. It is the same stand-in the round-2 reviewer used.
- Result: **83/83 killed**, each red on every label it expects. The run went in three parts on the final tree: the 29 new, re-bound and neighbouring entries, the two re-anchored after `load_manifests` refused a repeated anchor, and the other 54.
