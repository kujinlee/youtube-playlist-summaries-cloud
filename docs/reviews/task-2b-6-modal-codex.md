# Codex Adversarial Review — Stage 2b Task 6 (NewPlaylistModal, §13)

**Reviewer:** Codex (gpt-5.5). **Diff:** `8946cb3..96c7e0e`. **Date:** 2026-07-11.
**Verdict:** No Blocking. 1 High + 3 Low.

## Findings
1. **[HIGH] Double-submit not synchronously guarded** (NewPlaylistModal.tsx submit). `submit()` calls `setSubmitting(true)` (async React state), no `if (submitting) return` / ref lock. Two submit events in the same render window fire `createIngest(url)` twice → two ingest jobs enqueued for the same playlist (spend / velocity-guardrail path). *Fix:* synchronous `submittingRef` mutex.
2. **[LOW] No double-submit test** — the disabled-while-submitting test waits for disabled (after the vulnerable window). Add a test firing two submits and asserting `createIngest` called once.
3. **[LOW] Focus-trap only tests forward wrap** (Tab last→first); Shift+Tab first→last untested though implemented.
4. **[LOW] Reset paths (null-playlistId, IngestError, generic) don't assert the submit button re-enables** after `setSubmitting(false)`.

## Confirmed OK
All 4 dismissal paths guarded while submitting (backdrop/Escape via guardedClose; ✕/Cancel disabled+guarded); inside-dialog clicks stopPropagation; playlistId===null keeps open + exact message + no onSuccess + reset; onSuccess only when playlistId!==null; 401→router.replace('/login') no post-nav setState; IngestError/generic → role=alert + reset; DOM-only icon change state-machine-neutral; real tokens only.
