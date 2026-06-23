# Adversarial Spec Review — transcript-fallback-gemini

**NOTE: Codex at usage limit (until Jul 18 2026); Claude adversarial review per docs/plugins.md.**

Verdict: needs-rework → all Blocking/High applied; now sound-to-plan.

## Blocking
- **B1** `generateJson(model, prompt:string, …)` is STRING-ONLY (gemini.ts:118-129) — cannot carry the
  `fileData` YouTube-URL part. → `transcribeViaGemini` must call `model.generateContent([{fileData},{text}])`
  directly with a LOCAL JSON.parse+Zod+retry loop, mirroring `generateDeepDiveCombined` (gemini.ts:383-397).
  Do NOT reuse `generateJson`.

## High
- **H2** Coverage safeguard needs `durationSeconds`, but the specced signatures don't receive it. → Plumb
  `durationSeconds` through `resolveTranscriptSegments(videoId, youtubeUrl, durationSeconds)` →
  `transcribeViaGemini(youtubeUrl, videoId, durationSeconds)` (available at writeSummaryDoc, pipeline.ts:42).
- **H3** `dev-logger.ts` has no warn API (only `logError(ctx, err)`). gemini.ts convention is `console.warn`.
  → coverage warns via `console.warn('[transcribe-coverage] low coverage <pct>% for <videoId>')`.
- **H4** `mediaResolution` passthrough survives at runtime ONLY inside `generationConfig` (SDK spreads it to
  the body) — keep it there, not a top-level field. Test: the existing `getGenerativeModel` mock discards
  its args; hoist it to a named `jest.fn()` so the test can assert
  `getGenerativeModelMock.mock.calls[0][0].generationConfig.mediaResolution === 'MEDIA_RESOLUTION_LOW'`.
  The `fileData` part is assertable via `mockGenerateContent.mock.calls[0][0]` (like the deep-dive test).

## Medium/Low (folded)
- **M5** OpenAPI responseSchema can't enforce text-min-1/finite startSec → Zod + post-parse cleanup is the
  real guarantor (keep the drop-empty/non-finite step).
- **M6** Resolver must capture the caption error to include in the final "both failed" message.
- **M7** Map step should DEDUPE equal `startSec` (keep first) — `resolveTranscriptTokens` requires strictly
  increasing offsets (transcript-timestamps.ts:79-89); duplicate-start tokens would drop ALL ▶ links.
- **M8** Add a token-budget bound for the longest playlist video (duration × words/min) so a multi-hour
  video doesn't blow the downstream `generateSummary` context.
- **L9/L10/L11** error rethrow includes videoId ✓; detectLanguage source-agnostic ✓; youtubeUrl in
  SummaryDocInput ✓ (pipeline.ts:16).
