# Final Whole-Branch Review — Gemini Transcript Fallback (`f27191e..54168b5`)

**Reviewer:** Claude (opus), whole-branch. **NOTE:** Both adversarial reviews (spec + plan) were Claude standing in for usage-limited Codex (until Jul 18 2026) per `docs/plugins.md`. Re-run Codex before merge if access returns — the Claude passes already satisfy the gate.

## Verdict: READY TO MERGE (minor caveats)

Feature is correct, well-integrated, does what it claims. Full `npm test` 963 green; `npx tsc --noEmit` clean. No Critical or Important findings.

## Scrutiny (7 focus areas — all PASS)

1. **End-to-end cascade.** `writeSummaryDoc` → `resolveTranscriptSegments` → `transcribeViaGemini` → `mapGeminiTranscriptSegments` → `generateSummary` → `resolveTranscriptTokens`. Strictly-increasing-offset requirement (transcript-timestamps.ts:86) satisfied by construction (filter non-finite/empty → sort → dedupe equal startSec keep-first). Adversarial cases (all-same-startSec, single segment, unsorted) cannot break ▶ links or throw — `resolveTranscriptTokens` degrades gracefully (drops ▶, summary intact), never throws.
2. **`mediaResolution` passthrough — verified at SDK runtime, not just compile.** SDK 0.24.1 `index.js`: stores the whole `generationConfig` (line 1358), forwards it (1377), `JSON.stringify`s params with no field allow-listing (866/992) → `mediaResolution` reaches the HTTP body. The 700k→256k saving is real; no path drops it. Correctly inside `generationConfig` (top-level would be stripped).
3. **Error/cost semantics.** Gemini called ONLY when captions throw/empty — 257 captioned videos make no extra call. Both-fail throws → caught by runIngestion per-video try/catch → `error` event, loop continues (no sync crash). `durationSeconds:0` re-summarize path: coverage guard `> 0` skips cleanly, transcript still produced.
4. **Coverage safeguard.** `lastOffset/durationSeconds < 0.6` guarded by `> 0` (no div-by-zero); `console.warn`, never hard-fails.
5. **Integration regressions — none.** `writeSummaryDoc` is the only summary consumer changed. Deep-dive (`deep-dive/write-doc.ts`) correctly out of scope (own 3-path fallback, already survives gated videos). Re-summarize (`html-doc/ensure.ts`) + runIngestion both route through patched `writeSummaryDoc` → gain fallback for free.
6. **Security — parity.** URL as `fileData.fileUri` identical to pre-existing deep-dive path. No new SSRF/injection surface.
7. **Test integrity — non-vacuous.** Cascade tests prove ordering (Gemini not called on caption success; exact args on throw; exact mapping output). Pipeline test exercises the REAL resolver (only youtube+gemini mocked) → proves wiring.

## Findings

**Critical:** none. **Important:** none.

**Minor:**
- **M1** — `tests/lib/gemini.test.ts:495,502`: two error tests `jest.spyOn(console,'warn')` without `.mockRestore()`. Harmless (each re-spies; no later assertion on original). Hygiene. **[FIXED before PR]**
- **M2** — test const `URL` shadows the global (`gemini.test.ts`, `transcript-source.test.ts`). Cosmetic; rename `VIDEO_URL`. **[FIXED before PR]**
- **M3** — captions-empty + Gemini-throws subcase not directly unit-tested (captions-throw variant is; code path identical). Low risk. **[follow-up]**
- **M4** — `REQUEST_TIMEOUT_MS` (60s) shared with deep-dive video call; unverified for multi-hour transcription. Fails gracefully if exceeded (recovery-rate risk, not correctness). Spike evidence ≤47-min; playlist ≤~1h observed. **[follow-up]**

## Merge recommendation

Ship it. Cascade correct, cost discipline verified at SDK level, error isolation preserves graceful degradation, deep-dive exclusion justified. M1/M2 applied pre-PR; M3/M4 noted as follow-ups.
