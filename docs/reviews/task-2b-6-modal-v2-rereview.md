# Task 6 Re-Review (round 2) — CONVERGED

**Artifact:** NewPlaylistModal after fix `d9d814b` (full task diff `8946cb3..d9d814b`). **Date:** 2026-07-11.
**Reviewers:** Codex (gpt-5.5) + Claude (independent). **Verdict: CONVERGED — no new findings.**

## Prior findings — both confirm genuinely fixed
- **[HIGH] double-submit** — synchronous `submittingRef` mutex; second rapid submit returns before `createIngest`. Reset on null-playlistId + non-401 catch (retryable → resubmit works); NOT on success/401 (unmount/navigate). No deadlock, no ref/state desync (paired with setSubmitting).
- **[LOW×3]** double-submit test (Claude reverted to pre-fix `96c7e0e` → 2 calls, fix → 1: non-vacuous), Shift+Tab reverse-wrap test, re-enable-after-reset (null + IngestError) tests.

## Notes (pre-existing, not this round)
- Success/401 paths never reset `submitting`/ref — matches pre-fix behavior (relies on parent unmounting on success). NewPlaylistModal has no call site yet (grep clean) → the unmount-on-success assumption is discharged by **T9** wiring. Carry to T9: `onSuccess` must close/unmount the modal.

11/11 jest, tsc 0. **T6 done.**
