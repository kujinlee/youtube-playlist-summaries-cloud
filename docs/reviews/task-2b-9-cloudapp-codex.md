# Codex Adversarial Review — Stage 2b Task 9 (CloudApp wiring, integration)

**Reviewer:** Codex (gpt-5.5). **Diff:** `b2d35ed..3fb7b93`. **Date:** 2026-07-11.
**Verdict:** No Blocking. 1 High + 1 Medium.

## Findings
1. **[HIGH → FIXED] Retained `playlistUrl` for one render after cross-playlist nav (spend path, distinct from the R3 async race).** `PlaylistLibrary` is not keyed; the `playlistUrl` reset lives in the `[cloudScope]` useEffect which runs AFTER B's first render. So navigating A→B renders B for one commit with A's `playlistUrl` still in state → Refresh enabled with A's URL → a click `createIngest(A)` while viewing B. The reqSeq async guard does not cover this (no stale response involved — just retained state). *Fix:* tie the URL to its playlist id — store `{ playlistId, url }`, derive `playlistUrl` as live only when `entry.playlistId === current playlistId`. Makes the spend path correct-by-construction (timing- and key-independent). NOTE (controller): the observable window is sub-frame (reset effect covers realistic interaction; not RTL-reproducible), so severity is theoretical — but fixed anyway because the derived design removes the timing dependency AND the fragile non-key invariant Claude flagged.
2. **[MEDIUM → ADDRESSED] Test gap** — the R3 test covers async in-flight poisoning but not the retained-state window (A never becomes a loaded URL in state there). *Fix:* added a test where A loads + Refresh enabled, nav to B (B pending), assert Refresh disabled + A not POSTed.

## Verified OK
reqSeq guard present in try+catch before all setState (drops stale listVideos(A); doesn't break mount/sort/onProgress). onIngestSuccess closes modal before setSummary+push. IngestSummaryNotice gated `summary.playlistId===playlistId` (no leak). Refresh: no nav, 401→/login, IngestError→refreshError, bumps bannerNonce. Real tokens.
