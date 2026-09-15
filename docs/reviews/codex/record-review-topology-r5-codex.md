<!-- codex-review: model=gpt-5.5 -->

**Design Review**

No Blocking/High/Medium findings.

The representation is now complete for the rule it is trying to enforce. A git tree entry, `"<mode> <sha>"`, plus the all-zero absence shape, is the right answer to “did the reviewer see what is merging?” for tracked paths. It captures file content, executable bit, symlink targets, gitlinks/submodules, file/type swaps, deletions, additions, and ignored-then-force-added files once they enter the index. Things it does not capture, like xattrs, non-executable chmod bits, working-tree smudge bytes, or dirty contents inside a submodule, are not merge-tree facts. Non-deterministic clean filters remain a fail-closed accepted limit, not a false pass.

The organ is mostly right, but slightly under-owned. `codex-review.py` produces the testimony and `check-review-recorded.py` consumes it; that split is natural. The weaker part is that the tree-entry wire format is still a convention between them rather than a tiny shared codec/schema. A shared `TreeEntry`/`Absent` parser would have made some of the last four defects harder to write, especially zero-width absence and blob-only parsing. I do not think that means another redesign is owed: the representation shape is right. This is hardening, not a different mechanism.

The cheap missing question is schema validation: when reading a verdict, require `schema == 2`, `tool == "codex-review"`, and tree-entry strings matching either absence or `"<mode> <object-id>"`. Today malformed records mostly fail closed, but the contract is important enough to state mechanically.

The accepted limits do not compose into a larger hidden mechanism hole as long as the result is read honestly: this gate certifies only “a Codex verdict in this PR range saw the final merge tree.” It does not certify dual review, reviewer competence, true stacked-parent attribution, or default-branch push coverage. The dangerous composed hole is prose/operational: someone treating this one green as “the review process is complete.” The current docs mostly avoid that by saying steps 1-4 are convention and the Claude half is owed.

The `docs/review-method.md` Round topology prose is load-bearing. The ~60 lines are doing real work: they separate interference safety from final-tree review, explain why alternating exists, and state retirement observations. I would not shrink it yet.

**Low**

[scripts/check-review-recorded.py:309](/Users/kujinlee/code/agentic-ai-docs/.yps-worktrees/review-topology/scripts/check-review-recorded.py:309) has stale prose from before r4: it says `"<mode> <blob>"`, “absent means it is not a blob,” and says submodules are excluded. The code now correctly keeps every entry. This is stale cross-reference/editorial, not MECHANISM and not BRANCH COVERAGE.

Verification run:
`python3 scripts/check-review-recorded.py --self-test` → 75/75 passed  
`python3 scripts/codex-review.py --self-test` → 68/68 passed

CONVERGED. The SHAPE is now right.
