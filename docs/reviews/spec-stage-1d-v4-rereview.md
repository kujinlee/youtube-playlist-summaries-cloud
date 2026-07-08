# Round-4 re-review — Stage 1D spec v4 (dual; verdict: NOT converged — v5)

**Date:** 2026-07-08 · Target: v4 (commit c086d38)
**Reviewers:** Codex round-4 (`task-mrcnpezu-x4z3mq`, session `019f43df`) + Claude round-4 (fresh Opus `a037b67c`), independent.
**Note:** the two reviewers now **agree** (both: not converged, v5 required) with heavily overlapping findings — the loop is tightening. One genuine severity split remains (video-input token ceiling: Codex Blocking, Claude Low-inherent), resolved in v5 by a `countTokens` preflight (hard cap) rather than re-litigating.

## Blocking

- **B1 — Guard test still can't prove the bound: the pass-count multipliers are un-exported, hard-coded (Claude; = Codex-H1 deeper).** The §3 derivation's `3× transcribe / 12× summary / 3× quickview` multipliers come from `transcribeViaGemini retries=2`, `MAX_SUMMARY_ATTEMPTS=4` (gemini.ts:201, **not exported**) × `generateJson retries=2`. §9 exports only token caps + prices, so the guard test must hard-code `3/12/3`. Tune `MAX_SUMMARY_ATTEMPTS 4→8` (one line) → summary term doubles → one-run worst ≈ $1.37 > $1.00, but the test computes with `12` and still passes → cap silently unsound. *Fix: export the pass-count constants (or `SUMMARY_MAX_PASSES`/`TRANSCRIBE_MAX_PASSES`/`QUICKVIEW_MAX_PASSES`); the test imports + recomputes; add to the coupled-set enumeration.*
- **B2 — Transcript-input truncation not specified as an enforceable token bound (Codex).** v4 says "truncate to `MAX_TRANSCRIPT_INPUT_TOKENS`" but names no tokenizer/`countTokens`/char-ceiling, so an approximate local counter could under-count vs Gemini billing. *Fix: char-based truncation with the proof `billed tokens ≤ characters`; drop whole trailing segments; feed the same truncated list to the prompt and `resolveTranscriptTokens`.*
- **B3 — Transcription-fallback video input is not a hard ceiling (Codex; Claude rates Low-inherent).** v4 derives 270k from `duration × 150 tok/s` — an uncited assumption; no API-level cap or preflight count. *Fix: `countTokens` preflight on the cloud transcribe request → reject > `MAX_TRANSCRIBE_INPUT_TOKENS` (hard cap); documented-margined-rate fallback if `countTokens` can't resolve YouTube `fileData` (verified in impl). Size `est` from `MAX_TRANSCRIBE_INPUT_TOKENS`.*

## High

- **H1 — `est` ~2¢ margin, and its largest term (transcription) rests on un-plumbed threading (Claude; = Codex H2+M2).** `resolveTranscriptSegments` (transcript-source.ts:21) has a fixed signature with no cap slot and is injected **raw** at summary-handler.ts:72 (only `generateSummary` is wrapped); §8 omits `resolveTranscriptSegments` and `summary-core.ts` from touched files. *Fix: specify a `CloudGeminiCaps` threaded through `summaryCore` opts to all three cloud calls; add both files to §8.*
- **H2 — Guard tautological for `summary_max_attempts ≤ 0`; schema doesn't forbid it (Codex).** `claim_next_job` bills once even at `max_attempts=0`; `est ≥ per_run_worst × 0` passes. *Fix: DB CHECK `summary_max_attempts ≥ 1`, `dig_max_attempts ≥ 1`, est/cap ≥ 0.*

## Medium

- **M1 — PJ003 `::int` overflow (both).** A huge finite `durationSeconds` (zod `z.number().finite().positive()` admits `1e21` → jsonb `->>'…'` renders plain decimal, passes the regex) → `('…')::int` raises `22003`, not `PJ003` → unmapped 500 instead of `VideoTooLongError`. *Fix: `floor(v_dur::numeric) > v_cfg.max_duration_seconds` — numeric compare, no `::int`.*
- **M2 — `MAX_TRANSCRIBE_OUTPUT_TOKENS` converts some legit dense transcriptions into charged dead-letters (Claude).** ≤30-min fast-speech video whose transcript JSON exceeds 32 768 out → `MAX_TOKENS` → all 3 passes throw → `max_attempts=1` dead-letters, quota+reservation charged, no output; compounds anon lockout (open-q #4). *Fix: size the cap against the worst real 30-min transcript; document the failure mode in open-q #4.*
- **M3 — Rework must replace EVERY `auth.uid()` with `p_owner_id` (Claude).** Under `service_role`, `auth.uid()` is NULL; a leftover in the JOIN-branch SELECT (0009:22,27,34) makes idempotency lookup match nothing → INSERT conflict → 8-try loop `retry limit exceeded`. *Fix: state "replace all `auth.uid()` with `p_owner_id`" explicitly in §4.*

## Low
- **L1 — Video-input term is duration-enforced × rate-assumed, not code-capped (Claude).** Even with a `countTokens` preflight, the *est sizing* rate is empirical; "every token term is code-enforced" (§1/§2c) is slightly overstated. *Fix: one honest sentence; cite the code's own ~142 tok/s observation (256k/1800s) and set the rate above it with margin.*
- **L2 — CONFIRMED NON-ISSUES (both attacks held):** truncated-output→retry fails fast (≤3 passes, under budget, no breach); transcript prefix-truncation is `[[TS:n]]`-safe (model cites only visible indices; `resolveTranscriptTokens` resolves in-range). No fix.
- SQLSTATE `PJ001/2/3` confirmed clean (outside PostgREST `PT`).

## Round-3 → v4 resolution status
Token-ceiling enforcement: RESOLVED for output + (with v5) transcript input; provability PARTIAL (B1 multipliers). Guard test: PARTIAL (B1). PJ003 cast: PARTIAL (M1 overflow). Handler-reads-config, test-file split, SQLSTATE, advisory wording: RESOLVED. Re-verified still-holding: at-most-once, two-client split, never-release, all-or-nothing rollback, cloud-only-3-Gemini-surfaces.

## v5 plan
Export pass-count constants + guard test recomputes; char-based transcript truncation (tokens≤chars); `countTokens` preflight hard-cap on video input (+ documented-rate fallback); `CloudGeminiCaps` threading through `summaryCore` to all three cloud calls (+ §8 files); DB CHECK `max_attempts≥1`; PJ003 numeric compare; raise `est` to 125¢ + prompt/schema overhead + document the cap→charged-failure mode; explicit `auth.uid()`→`p_owner_id`; honest video-input-residual sentence. → v5; round-5 dual review.
