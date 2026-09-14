# record-review-topology — round 14, coordinator adjudication

Both halves ran against HEAD `dc9fe107` plus the uncommitted delta, which was the shipping state.

* Claude: `docs/reviews/claude/record-review-topology-r14-claude.md` — 0 Blocking, **1 High**, 2 Medium, 1 Low. **NOT CONVERGED.**
* Codex: `docs/reviews/codex/record-review-topology-r14-codex.md` (`gpt-5.5`) — **0 findings at every severity. CONVERGED.**
* Verdict: `docs/reviews/verdicts/record-review-topology-r14-codex.verdict.json`, `gate_ran: true`.

## ⭐ THE HALVES SPLIT, AND ON THIS EVIDENCE THE FINDING-REVIEWER IS RIGHT

This is the round to remember, because the two halves disagreed **twice, in opposite directions**,
and each disagreement is informative.

**1 — Codex found nothing; Claude found a fail-open in the deliverable.** Codex ran the right
commands and reported everything green, including a full `--mutate .` at 620/620/0. It was not
careless: every claim it made is true. It simply never asked whether the gate's own `git diff` is
the diff the gate reasons about. Claude did, and the answer was no.

**2 — Codex CONFIRMED a claim Claude REFUTED, and Claude was right.** The r13 adjudication asserted
that an attributable manifest entry for the printer regression is *impossible by construction*,
because the case that detects a broken printer is printed by that printer. Codex verified that claim
and reproduced it exactly:

```text
manual full revert got=  ok=False  killed=1/1  attributed=0/1
expect ... matched 0 red case(s) — caught by something else:
["the FAIL line ...: got=['a plain case: got=1']", ...]
```

Claude tested the same thing, got the same result for that candidate — and then went looking for a
**different** case whose garbled form is short and stable. A boolean case has one: its tail is a
literal `: got=False` under any revert of the delimiter, embedding no repr and moving with no
fixture. That entry now ships and is attributed.

**Two reviewers, one conclusion, both wrong.** The measurement was identical; what differed was that
one stopped at the first candidate and the other asked whether a better candidate existed. This is
the sharpest illustration on this branch of why *"the halves are not redundant"* survives even though
*"zero overlapping findings"* did not: agreement is not verification.

`docs/dev-process.md` already records this — *"never treat a single CONVERGED as proof; prefer the
reviewer that reports a finding until you have traced the code yourself."* Traced, and the finding
holds.

## H1 — a FAIL-OPEN in the gate this branch ships

`changed_paths` and `added_paths` ran `git diff --name-only` with git's rename detection **on by
default**, so `--name-only` printed only a rename's destination. Move a guarded file to a prose path
and the code file vanished from the gate's view:

```text
$ git diff --name-status --no-renames master-base HEAD
A       docs/x.ts
D       lib/x.ts

$ python3 scripts/check-review-recorded.py --base master-base
ok — no guarded path changed — a review round is not required          rc=0
```

A code file left the tree, no review document, no `NO-REVIEW:` declaration, exit 0 — the exact
outcome this file's WHY THIS EXISTS section was written against. **It defeated the second question
too**, which is worse because that half is new here: `tail_candidates` intersects `after` (from
`_changed_since`, which passes `--no-renames`) with `branch_delta` (from `changed_paths`, which did
not), so the path was silently dropped and the round credited with seeing it. Control: adding the
flag and changing nothing else turns both scenarios red.

**M2 is the same root cause inverted** — with `--diff-filter=A`, a review document *moved* into
`docs/reviews/` is classified `R` and never reaches `review_added`, so a branch performing the
`docs/reviews/<writer>/` relocation this project mandates was told no review round was recorded. A
false FAIL on a branch doing the right thing is backlog #56's shape.

⚠ **The same two lines were edited one round earlier for the same class of defect.** r11 added `-z`
to both, and its own docstring says the sibling was *"fixed there as an INSTANCE, not searched for as
a class, which is this project's own recorded failure shape."* `--no-renames` is one flag over.

## M1 — "IMPOSSIBLE", refuted (see above)

**FIXED.** The twelfth entry ships; the comment now records what was measured and why the long-form
variant was rejected, instead of an unfalsifiable word. An *"impossible"* in a guard's source is a
durable instruction to future authors not to try.

## The exhaustiveness pass — the class, closed structurally

`review-method.md` prescribes FIX **plus an exhaustiveness pass** for a branch-coverage defect, and
that is what H1 is: no reshaping of this feature dissolves a missing `git` flag. The pass was run
mechanically — every git invocation in the two files enumerated with `ast`, because both wrappers
hide their flags at the call sites and grep reads past them.

| invocation | flags | verdict |
|---|---|---|
| `changed_paths` | `-z --no-renames` | ✓ via `diff_argv` |
| `added_paths` | `-z --no-renames --diff-filter=A` | ✓ via `diff_argv` |
| `_changed_since` | `-z --no-renames` | ✓ **now also via `diff_argv`** |
| producer `diff-index` | `-z --no-renames` | ✓ agrees |
| `ls-tree -z HEAD -- <paths>` | no `-r` | ✓ **measured, not assumed** |

Two results worth recording:

* **A suspected second instance was refuted by measurement.** `ls-tree` without `-r` lists only a
  tree's top level, so a nested guarded path looked like it might be invisible. Built a repo with
  `lib/deep/x.ts` and ran it: an exact nested pathspec **does** resolve without `-r`. Thirty seconds
  of execution settled what an hour of reasoning would have got wrong — which is the r14 lesson
  applied to the r14 fix.
* **Fixing all three to agree left the agreement as a CONVENTION** — three call sites that happen to
  match, which is precisely how they drifted apart in the first place. `_changed_since` now goes
  through `diff_argv` too, so there is **one builder**, the existing cases cover all three, and the
  manifest entry deleting `--no-renames` reds through the case that names it.

## Measured on this tree

```
check-review-recorded --self-test  122/122      codex-review --self-test        85/85
check-plan-code       --self-test  128/128      check-ratchet-contract          41/41
check-fixture-variation --self-test 60/60       check-selftest-counts           18/18
check-review-rounds   --self-test   29/29       check-guard-coverage            37/37
live: check-selftest-counts, check-fixture-variation, check-ratchet-contract, check-docs,
      check-anchors, check-review-rounds — all rc=0
EXPECTED_MUTATIONS: 44 files, sum 622
```

⚠ The last completed `--mutate .` measured **620** — before the final two entries and the `diff_argv`
unification. The 622-entry run is in flight and is **not** a figure to quote until it lands.

NOT CONVERGED — the fix for H1/M1/M2 is itself unreviewed code, so a final round against the frozen
tree is owed before merge.
