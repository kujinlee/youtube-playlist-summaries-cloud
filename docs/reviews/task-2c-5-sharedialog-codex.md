# Codex Adversarial Review — Stage 2c Task 5 (ShareDialog)

**Model:** gpt-5.5. **Date:** 2026-07-11. **Diff:** d25d435..6fc6191 (R1), fix 0952d60 (R2).

## Round 1
HIGH [components/cloud/ShareDialog.tsx:37](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/components/cloud/ShareDialog.tsx:37): Backdrop/Escape dismissal is gated by `busy` state, not the synchronous `inFlightRef`. The ref guards create/revoke calls, but dismissal can still depend on a stale render between `inFlightRef.current = true` and React committing `setBusy(true)`. The brief explicitly requires the synchronous in-flight ref to gate backdrop + Escape too.  
Fix: change `guardedClose` to read the ref, e.g. `if (!inFlightRef.current) onClose();` or `if (!inFlightRef.current && !busy) onClose();`, and add/adjust a test that proves dismissal checks the ref rather than only post-render disabled state.

LOW [tests/components/share-dialog.test.tsx:69](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/components/share-dialog.test.tsx:69): Unauthorized and non-401 error paths are only tested for create, not revoke. The component implementation appears to handle revoke errors correctly, but this is an unguarded branch for a required behavior.  
Fix: add revoke `UnauthorizedError -> replace('/login')` and revoke generic error `role="alert"` tests.

Mocking check: OK. The `jest.mock` factory returns bare `jest.fn()`s, and tests control `createShare`/`revokeShare` per case with `mockResolvedValue`, `mockRejectedValue`, or `mockReturnValue`; outcomes are not locked to a static factory return.

Other checks: tokens are real, no `--bg`/`--bg-elevated`/`--text`; no service-role/DB access; focus trap selector matches; no self focus-restore cleanup; dismissal paths are covered; `npx jest share-dialog --runInBand` passes.

Verdict: needs fixes before merge, due to the ref-gated dismissal requirement.
tokens used
29,260
HIGH [components/cloud/ShareDialog.tsx:37](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/components/cloud/ShareDialog.tsx:37): Backdrop/Escape dismissal is gated by `busy` state, not the synchronous `inFlightRef`. The ref guards create/revoke calls, but dismissal can still depend on a stale render between `inFlightRef.current = true` and React committing `setBusy(true)`. The brief explicitly requires the synchronous in-flight ref to gate backdrop + Escape too.  
Fix: change `guardedClose` to read the ref, e.g. `if (!inFlightRef.current) onClose();` or `if (!inFlightRef.current && !busy) onClose();`, and add/adjust a test that proves dismissal checks the ref rather than only post-render disabled state.

LOW [tests/components/share-dialog.test.tsx:69](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/components/share-dialog.test.tsx:69): Unauthorized and non-401 error paths are only tested for create, not revoke. The component implementation appears to handle revoke errors correctly, but this is an unguarded branch for a required behavior.  
Fix: add revoke `UnauthorizedError -> replace('/login')` and revoke generic error `role="alert"` tests.

Mocking check: OK. The `jest.mock` factory returns bare `jest.fn()`s, and tests control `createShare`/`revokeShare` per case with `mockResolvedValue`, `mockRejectedValue`, or `mockReturnValue`; outcomes are not locked to a static factory return.

## Round 2 (fix confirmation, 6fc6191..0952d60)
CONVERGED.
tokens used
11,098
1. CONFIRMED-FIXED: `guardedClose` checks `!inFlightRef.current && !busy`, so backdrop/Escape are ref-gated.

2. CONFIRMED: two revoke error tests added, each uses its own `revokeShareMock.mockRejectedValue`; 401 asserts `router.replace('/login')`, generic error asserts `role=alert` and dialog stays open.

3. CONFIRMED: initial focus ref moved to default-checked `30d` radio.

4. NO NEW DEFECT FOUND: targeted test file passes, `18/18`.
