<!-- codex-review: model=gpt-5.5 -->

**Blocking**

[scripts/check-review-recorded.py](/Users/kujinlee/code/agentic-ai-docs/.yps-worktrees/review-topology/scripts/check-review-recorded.py:324) treats a final gitlink/submodule as absent, so a reviewed deletion can pass even though the final tree contains a new submodule at that path.

```py
if name and len(parts) >= 3 and parts[1] == "blob":
    entries[name] = f"{parts[0]} {parts[2]}"
```

paired with:

```py
if not (reviewed.get(p) and final.get(p, ABSENT_ENTRY) == reviewed.get(p))
```

Concrete scratch input:

1. `HEAD` has regular file `sm`.
2. Before review, delete `sm`; `reviewed_state()` records:
   ```py
   {'sm': '000000 0000000000000000000000000000000000000000'}
   ```
3. After review, replace `sm` with a submodule and commit.
4. Final tree contains:
   ```text
   160000 commit 8897f89dc7077d7c373aa0e582976de776c28834	sm
   ```
5. `_final_entries(["sm"])` returns `{}` because the entry is not `blob`.
6. `round_tail(["sm"], dirty, final)` returns `[]`.

That is a false pass: the reviewer saw absence; the merge contains a gitlink. A full tree-entry comparison, including entry type or at least non-blob entries, dissolves this.

**High**

[scripts/check-review-recorded.py](/Users/kujinlee/code/agentic-ai-docs/.yps-worktrees/review-topology/scripts/check-review-recorded.py:267) does not implement r3’s accepted mitigation for stacked parent gaps. The adjudication said the pass now names the document, but the message only names the reason:

```py
return 0, (f"final-tree rule NOT CHECKED — {why}; declared in this range: "
           f"REVIEW GAP: {gap}")
```

`declared_gap()` also discards the path before returning:

```py
texts = [(ROOT / rel).read_text(encoding="utf-8", errors="replace")
         for rel in review_docs if (ROOT / rel).is_file()]
return first_codex_gap(texts, mod_parse)
```

Concrete failing input: `tail_verdict({}, gap="codex: parent branch could not run")` returns a green “declared in this range” message with no `docs/reviews/...` path. That leaves the r3 High effectively accepted without the stated visibility fix. The docstring also claims the pass names the document at [scripts/check-review-recorded.py:59](/Users/kujinlee/code/agentic-ai-docs/.yps-worktrees/review-topology/scripts/check-review-recorded.py:59), but the code cannot.

**Medium**

[scripts/check-review-recorded.py](/Users/kujinlee/code/agentic-ai-docs/.yps-worktrees/review-topology/scripts/check-review-recorded.py:105) hard-codes SHA-1-width absence:

```py
ABSENT_ENTRY = "000000 " + "0" * 40
```

In a SHA-256 repo, `git diff-index` writes 64 zeroes:

```text
:100644 000000 4b6c...7b78 0000000000000000000000000000000000000000000000000000000000000000 D
```

Concrete result from scratch: `reviewed_state()` recorded the 64-zero deletion, but `round_tail(["f"], dirty, {})` returned `["f"]`. This is fail-closed, not fail-open: a reviewed deletion falsely fails in SHA-256 repositories. `core.abbrev=7` did not affect `diff-index`; it still emitted full SHA-1 zeros.

**Low**

None found.

**Other Checks**

The ordinary tree-state sweep held for added, modified, deleted, mode-only, file↔symlink type changes, renamed-as-delete+add, unchanged, and absent-from-both paths. I could not produce a zero destination for a non-deletion among those. An unmerged real index path was recorded as the conflict-marker worktree blob through the throwaway index, not as zeros. I also could not produce duplicate path records from `diff-index --cached -z --no-renames HEAD`.

For `git add -A` failure, the sparse/out-of-cone case I reproduced kept the valid in-cone entry. I did not find a case where the partial index produced a wrong entry rather than an incomplete one.

The mutation table no longer appears to have the “expected value computed from the mutated constant” shape. Several entries would also be killed by sibling cases, but I did not find one whose named expected case would stay green.

The prose counts now reconcile: r1 = 8 findings, r2 = 3, r3 = 5, total 16. Fixed = 7 + 3 + 3 = 13. Accepted = 1 + 0 + 2 = 3. `docs/plugins.md:120`, `docs/review-method.md` Round topology, the Phase 6 item, and the dashboard line all reflect the recounted topology/counts, except for the false “names the document” claim above.

Verification run:

```text
python3 scripts/check-review-recorded.py --self-test  # 68/68 passed
python3 scripts/codex-review.py --self-test           # 68/68 passed
```

NOT CONVERGED.
