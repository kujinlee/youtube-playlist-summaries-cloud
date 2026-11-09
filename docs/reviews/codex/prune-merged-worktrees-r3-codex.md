<!-- codex-review: model=gpt-6.1-sol -->

**F1 — MEDIUM — The placeholder leaves the original race open.**  
Evidence: `scripts/prune-merged-worktrees.py:460–465`. In a temporary repo, I recreated the old directory and wrote `late.txt` immediately before `leave_placeholder()`. The run returned **rc 0, ARCHIVED**, but `git -C <old> rev-parse --show-toplevel` resolved to the **main checkout**. The hook also suppresses the row’s placeholder-failure reason.  
**Fix:** Coordinate moves with writers through a shared lifecycle lock. At minimum, surface placeholder failures prominently in the hook and return failure instead of silently treating protection as installed.

**F2 — MEDIUM — A deleted remote allows a newly committed HEAD outside the merged PR to be archived.**  
Evidence: `:309–335`. I deleted the remote branch, then injected a commit before `git status`, after the worktree listing supplied its HEAD. Result: **rc 0, ARCHIVED**; `git merge-base --is-ancestor HEAD <merged-PR-head>` in the archive returned **1**. The unique file survived, but rule 2 was violated and the report named the stale HEAD.  
**Fix:** Refresh HEAD and branch before moving and rerun eligibility if either changed. Use lifecycle coordination to close the remaining check/move race.

**F3 — MEDIUM — BY-PEER mistakes an interrupted move for completed archival.**  
Evidence: `:375–385`, `:466–469`. I simulated a peer interrupted after directory rename but before Git’s administrative update. The current run returned **rc 0, BY-PEER**, while `git worktree list --porcelain` still registered the **old path as prunable**. Matching `.git` text proves identity, not successful completion.  
**Fix:** Verify that Git registers the candidate archive path and that its administrative backlink agrees. Otherwise report an incomplete move requiring repair.

**F4 — MEDIUM — Placeholder write failure hides an archive that already happened.**  
Evidence: `:361–362`, `:638–642`. Injecting `OSError(28, "No space left on device")` during placeholder writing produced:

```text
hook rc: 0
archive exists: True
CANNOT RUN — unexpected OSError ... (treat as NOT RUN)
```

The output omitted the moved worktree entirely. Only `os.open()` failures are caught; writing and closing can also fail.  
**Fix:** Catch the entire placeholder operation and retain completed move results when reporting unexpected exceptions.

**F5 — MEDIUM — A transient move failure disables archival indefinitely at unchanged HEAD.**  
Evidence: `:475–477`, `:317–320`. A one-shot injected move error returned **FAILED, rc 1**. A subsequent run with working Git returned **KEPT, rc 0**, without retrying. Every qualifying nonzero result becomes a persistent refusal, including temporary filesystem errors.  
**Fix:** Cache only recognized structural refusals; give other failures a bounded retry interval and retain visible diagnostics.

**F6 — LOW — The self-test does not protect the placeholder’s exclusive-create rule.**  
Evidence: I executed an in-memory mutant removing `| os.O_EXCL` from `:358`. It still returned **79/79 passed**. Without exclusivity, a racing regular file at the old path can have its contents overwritten.  
**Fix:** Add a case placing a sentinel file at the old path before placeholder creation; assert its bytes remain unchanged and the collision is reported.

**F7 — LOW — The generated undo command is unusable for paths containing spaces.**  
Evidence: `:345–349`. Calling `undo_cmd()` with `/tmp/repo space/...` produced literal `<path withheld: ...>` tokens, which are shell syntax rather than executable path arguments.  
**Fix:** Generate commands using shell quoting, separately from display sanitization; test executing undo with spaced paths.

Validation: baseline **79/79 passed**. All adversarial moves used temporary repositories. No repository files were changed, GitHub was untouched, and `.claude/plans/` was not read. I found no loss of existing worktree contents in the unmodified move sequence.

Could not check: the full ~16-minute mutation sweep, real deadline termination between Git’s internal updates, or live hook/editor coordination. Walker compatibility was inspected statically; plan-reading walkers were not executed.

NOT CONVERGED
