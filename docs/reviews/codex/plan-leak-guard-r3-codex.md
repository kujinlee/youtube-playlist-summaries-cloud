<!-- codex-review: model=gpt-6.1-sol -->

**NOT CONVERGED** — the output-channel half of the SPLIT bet is refuted.

1. **Low — `scripts/check-plan-leak.py:296–305` — incomplete path redaction.**
   **fix_induced: true** — the F5 fold derives redaction solely from added-name hits.

   Concrete input: synthetic plan item `zirconium narwhals orchestrate velvet zeppelins beneath saffron glaciers`. The remote already contains an empty or clean file named `zirconium-narwhals-orchestrate-velvet-zeppelins-beneath-saffron-glaciers.md`. Modify that file to contain the item, commit, and push.

   The real push was blocked, but hook stderr printed the full phrase-bearing filename. Manual execution printed it to stdout; redirecting either channel preserved the phrase in files. Existing paths have no added-name hit, so `named` excludes them.

   **Fix:** check every displayed path against plan text independently of added-name hits, then redact matching paths.

2. **Low — `scripts/check-plan-leak.py:297` — plan-source labels bypass redaction.**
   **fix_induced: false.**

   Concrete input: give the synthetic plan the phrase-bearing filename above, then commit its eight-word item in ordinary `leak.md` and push.

   The real push was blocked, but stderr printed all eight words through `(a run of plan text from …/<filename>)`. Manual stdout did likewise.

   **Fix:** use opaque plan identifiers, or redact source labels through the same output sanitizer.

Validation: **119/119 self-tests passed**, run in the foreground. Real pushes blocked leaks under the requested diff settings, effective `includeIf` configuration, rename/copy cases, non-ASCII paths, and `GIT_DIR`/`GIT_WORK_TREE` overrides. External-diff and pager probes wrote no marker file. Moved clones and an actual old-main-branch checkout pushed unchecked as explicitly documented; status/session warnings identified those limits.

No new `hits 0` bypass found. Mutation sweep skipped as requested. Only temporary repositories received hooks; no real plan files were accessed, and no review file was written.
