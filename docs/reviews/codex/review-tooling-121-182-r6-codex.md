<!-- codex-review: model=gpt-6.1-sol -->

1. **Major — `scripts/codex-review.py:669–671`: a pre-existing artifact-directory symlink bypasses the refusal. Fix-induced: yes.**

   Concrete input: before dispatch, set `B/docs/reviews -> /external/reviews`, containing `claude/victim-r1-claude.md`. Run from B with `--out B/docs/reviews/claude/victim-r1-claude.md --allow-overwrite`.

   Reproduced through the CLI with a stub reviewer: **rc 0, victim overwritten, `intrusions: []`**. Resolution puts the destination outside both checkout identities, so it passes. No directory changes during the run; this differs from #400. The same layout is refused at `c9dcc13c`.

   **Fix:** retain the checkout-wide identity check and additionally refuse destinations inside either checkout’s resolved `docs/reviews` root. Add this static symlink layout as a regression case. Under DEFER, file this finding.

Reviewed `f7d2c932`, including both requested diffs. No additional ordinary-scratch refusal, recorded/executed tree mismatch, or merge regression found. #400’s findings are excluded.

Validation ran:

- Self-test: **203/203 passed**.
- Requested mutation command: **66/66 killed and attributed, zero survivors**, exit 0. It identifies itself as a diagnostic slice, not the full gate.

**NOT CONVERGED.**
