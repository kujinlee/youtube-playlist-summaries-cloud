<!-- codex-review: model=gpt-5.5 -->

**Blocking**

None found.

**High**

`scripts/check-review-recorded.py:492-493` lets a stacked parent branch’s Codex gap clear the child branch’s missing Codex verdict.

```py
tails, unusable = round_tails(branch_verdicts(added))
gap = declared_gap(review_added(added))
```

Concrete sequence I reproduced in a scratch repo:

1. Base commit has `app.py`.
2. Parent branch adds `docs/reviews/claude/parent-r1-claude.md` containing:
   ```md
   **REVIEW GAP:** codex — parent branch could not run
   ```
3. Child branch, stacked on that parent, changes `app.py`.
4. PR/check is evaluated against the original base, with no Codex verdict added for the child.

The gate returned:

```text
ok — review recorded in this range: docs/reviews/claude/parent-r1-claude.md
ok — final-tree rule NOT CHECKED — no Codex verdict was added by this branch; declared: REVIEW GAP: codex: parent branch could not run
RC=0
```

That gap belongs to the parent range, not the child’s code. The prose says “review document of this branch”; the implementation accepts “review document added anywhere in base..HEAD”.

**Medium**

`scripts/codex-review.py:329-332` cannot credit a reviewed deletion, so the documented “hold fixes uncommitted” path falsely fails for deleting code.

```py
dstmode, dstsha = parts[1], parts[3]
# A deletion has an all-zero destination: no content to credit anyone with having seen.
if not dstsha.strip("0"):
    continue
```

Concrete sequence reproduced:

1. Commit `lib.py`.
2. Delete `lib.py` before review.
3. `reviewed_state()` records `dirty {}`.
4. Commit the deletion plus review doc/verdict.

The gate returned rc 1 and named `lib.py` as unseen. But the reviewer saw the deletion. Absence is a tree state too; representing only blob-bearing entries loses it.

**Medium**

`scripts/codex-review.py:311-314` drops all dirty state when `git add -A` cannot stage an ignored or sparse-checkout path.

```py
if git("add", "-A", env=env) is None:
    return head.strip(), {}
```

Two reproduced cases:

Ignored force-add:

1. `.gitignore` contains `*.gen`.
2. `tool.gen` exists during review.
3. `reviewed_state()` records `dirty {}`.
4. Later `git add -f tool.gen` and commit.

The gate fails rc 1, naming `tool.gen`, even though the reviewer saw the file.

Sparse checkout:

```text
only in-cone {'in/a.txt': '100644 dd397ca9d8ee9653b950a7a6b84bd480ded9b8ea'}
with out-of-cone untracked {}
```

An unrelated out-of-cone untracked file made temp `git add -A` fail and discarded even the valid in-cone dirty entry.

**Medium**

`scripts/codex-review.py:313-315` and `scripts/check-review-recorded.py:294-314` can compute different entries for the same worktree bytes under a non-deterministic clean filter.

```py
if git("add", "-A", env=env) is None:
    return head.strip(), {}
raw = git("diff-index", "--cached", "-z", "--no-renames", "HEAD", env=env)
```

I verified with a `filter.nondet.clean` script that appends `date +%s%N`. `reviewed_state()` recorded:

```text
f.txt = 100644 3419cd36...
```

Then committing the same worktree bytes produced:

```text
f.txt = 100644 328e4981...
```

The gate failed rc 1. Plain `core.autocrlf=true` did not reproduce this; the entries matched there.

**Low**

`docs/dashboard-entries.md:8193-8207` has counts that do not reconcile with the review records.

```md
Two review rounds then found ten defects in it
...
Six more came from the same rounds:
```

Round 1 records 8 findings; round 2 records 3 findings. That is 11 total. The “Six more” sentence then names five items: merge-base skip, no-usable-round pass, modified historical verdicts, Claude gap clearing Codex absence, unreachable live-wiring case. I could not derive “ten” or “six more” from the repo as written.

**Verification Notes**

Ran and passed:

```text
python3 scripts/check-review-recorded.py --self-test  # 65/65
python3 scripts/codex-review.py --self-test           # 68/68
```

I did not run `check-plan-code.py --mutate .`.

Other premises checked: `git -C <subdir> add -A` stages the whole tree on this Git; `git ls-tree -z` does not quote paths under either `core.quotePath=true` or `false`; `rec.partition("\t")` preserves tabs inside path names. I could not construct a `diff-index --cached -z --no-renames HEAD` record that desynchronizes the two-field parser; copy records with two paths appeared only when I explicitly enabled copy detection options the code does not pass.

NOT CONVERGED.
