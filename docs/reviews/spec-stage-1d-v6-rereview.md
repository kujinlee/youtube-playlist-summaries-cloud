# Round-6 re-review — Stage 1D spec v6 (dual; verdict: NOT converged — v7)

**Date:** 2026-07-08 · Target: v6 (commit 7ef3ac9)
**Reviewers:** Codex round-6 (`task-mrcopnpr-mywksi`, session `019f43f9`) + Claude round-6 (fresh Opus `a669157148`), independent. **Codex: no new Blocking** (1 High, 1 Med, 2 Low). **Claude: 1 new Blocking** (audio pricing) + 2 High + 2 Med. Progress: down from prior rounds; the Blocking is a discrete modeling fix.

## Blocking (Claude B-r6-1 — Codex missed it)
- **The est prices the video-transcription `fileData` input entirely at the $0.30/1M text rate, but `gemini-2.5-flash` bills audio input at ~$1.00/1M.** LOW media resolution "downsamples frames only — audio is unaffected" (`gemini.ts:514`), so `MAX_TRANSCRIBE_INPUT_TOKENS` mixes video-frame + full-audio tokens. `countTokens` returns only `totalTokens` (no modality split), so a *provable* bound must price the audio component at the audio rate. All-audio worst case: 3×300k×$1.00/1M=$0.90 input → transcription ≈$1.15 → grand total ≈**$1.65 > $1.25**; the guard test imports the same single 30¢ → green CI (modeling omission, not drift). *Fix: add `PRICE_AUDIO_IN_PER_1M_CENTS`(≈100) + `AUDIO_TOKENS_PER_SEC`(≈32, Google-documented fixed audio rate ⇒ audio ≤ 32×`max_duration_seconds`=57.6k, duration-bounded); price the audio subset at the audio rate, remainder at text rate; re-derive `est` (→$1.50); import both into the §8 guard test + deploy pricing check.*

## High
- **H-r6 (Codex + Claude M-r6-2) — the `countTokens` unsupported fallback is not a sound cap.** v6 keeps "if YouTube `fileData` can't be counted → duration×rate + flag user," an estimate not an enforced ceiling, while `est` treats 300k as enforced → theorem false in that branch, yet §1/§2 claim soundness categorically. *Fix: `countTokens` is a **hard shipping gate** — if it can't bound the video input, **fail closed** (disable the Gemini video-transcription fallback; caption-less videos → `NonRetryableError`, not billed), never a rate estimate. Qualify the top-line soundness claims as conditional on this gate.*
- **H-r6-1 (Claude) — `thinkingBudget:0` has no *honored*-verification.** (Verified good: 0.24.1 SDK forwards unknown `generationConfig` keys — `index.js:866/1377`; flash supports `thinkingBudget:0`.) §8's test only proves the field is in the request (mocked). If the API silently ignores it, thinking bills at $2.50/1M (~$0.7+) with green CI. *Fix: impl/integration gate asserting `usageMetadata.thoughtsTokenCount == 0` for a representative cloud call; flag if not — mirror the `countTokens` L1 gate.*
- **H-r6-2 (Claude) — byte-cap primitive unnamed; `.length` (UTF-16) undercounts the first-class Korean path ~3×.** `tokens ≤ bytes` is valid, but `buildIndexedTranscript` uses `.length` (code units); the app is bilingual (`language:'ko'`). A Korean transcript at "40 960 length" ≈120k UTF-8 bytes ≈120k tokens → summary term breached, common (not adversarial) case; §8's ASCII "1-char segments" test passes with the bug. *Fix: name `Buffer.byteLength(rendered,'utf8')`/`TextEncoder`; require a multi-byte (CJK/emoji) test asserting UTF-8 byte length ≤ cap.*

## Medium
- **M-r6 (Codex) — PJ003 `floor(v_dur::numeric) > max` admits `1800.999999`**, contradicting §8's "fractional over-cap → PJ003." *Fix: `v_dur::numeric > v_cfg.max_duration_seconds` (drop `floor`; length-bounded regex already prevents precision blowup).*
- **M-r6-1 (Claude/Codex Low) — model assertion targets the raw env var, not the resolved model.** `process.env.GEMINI_SUMMARY_MODEL ?? 'gemini-2.5-flash'`: unset env (normal prod) → raw is `undefined` → assertion fails a correct deploy; §9 export list omits the model. *Fix: assert the **resolved** `SUMMARY_MODEL`/`TRANSCRIBE_MODEL` (post-`??`); export them; specify the startup assertion location (handler init).*

## Low
- PJ003 regex rejects >6-fractional-digit durations (harmless; YouTube sends integers).
- `countTokens` request carries `responseMimeType`/`responseSchema` (ignored by the count endpoint; cosmetic).

## Round-5 → v6 resolution
RESOLVED: char-vs-rendered prose (byte cap), countTokens LOW-res+VOD+TOCTOU, 300k-vs-360k, double-fetch/timeout, regex length, quick-view over-estimate; at-most-once/two-client/never-release/all-or-nothing/auth.uid all re-verified. PARTIAL→v7: thinking (request-fix good, no honored gate → H-r6-1), byte cap (prose good, primitive/test not locked → H-r6-2), env-model (wrong target → M-r6-1), price-drift (text in/out done, **audio price never modeled → the Blocking**), countTokens-fallback honesty → H-r6.

## v7 plan
Model audio input separately (audio-rate × duration-bounded), est $1.25→$1.50; countTokens hard-gate fail-closed (disable video-transcribe fallback if unsupported) + conditional soundness wording; thinking honored-gate (`thoughtsTokenCount==0`); name `Buffer.byteLength utf8` + CJK test; PJ003 drop `floor`; assert/export resolved model constant. Document the est→$1.50 / ~3-jobs-per-day evolution in open-q for the user's end review. → v7; round-7 dual review.
