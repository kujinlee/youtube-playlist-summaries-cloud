# Task 1D-13 Review — Live gates + integration migration + JobQueue.enqueue deletion

**Commit:** 59dd275 · **Base:** 233fae6 · Dual review (Claude SDD spec+quality + Claude adversarial [Codex fallback]).
**Gate:** integration 158/160 (2 live-gate skips) after `db reset`; `npm test` 1698 green; **`tsc --noEmit` 0 errors** (DECISION-2 chain fully closed).

## Spec Compliance: ✅ Approved (SDD reviewer, sonnet)
- Live gates: `gemini-live-gates.test.ts` `describe.skip` unless `RUN_LIVE_GEMINI=1`; asserts `thoughtsTokenCount` present-and-===0 + video-scale `countTokens`. `docs/reviews/1d-live-gemini-gates.md` records non-execution; `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED` stays `false`.
- Non-live fail-closed already covered (`gemini-caps.test.ts:143`) — not re-fabricated.
- All ~11 files migrated to 8-arg service path / `SupabaseEnqueuer`; job-queue-schema four insert cases per brief; producer-roundtrip re-baselined (7-bucket counts source-traced correct).
- DECISION-1 deletion: `JobQueue.enqueue` + `SupabaseJobQueue.enqueue` removed; grep confirms zero remaining callers (only retained `Enqueuer.enqueue` + `controller.enqueue` ReadableStream).

## Adversarial (Claude opus, Codex fallback) — No Blocking/High; no green-by-weakening
- **Denial tests preserved/strengthened:** canonical deny test (cost-guardrails.test.ts:231-250, all 3 vectors) UNTOUCHED. "insert for another owner" → now asserts exact `42501` grant revocation (stronger than the old WITH-CHECK). Cross-owner enqueue rejection covered by composite-FK `23503`. Idempotency legitimately re-expressed via RPC ON CONFLICT join (raw insert revoked).
- **RLS isolation strengthened:** two-owner setup via svc, bidirectional SELECT-isolation assertions (not vacuous; anti-vacuous guards retained).
- **Re-baselined counts CORRECT** by source trace, not back-fitted.
- **max_attempts=5 / max_free_users pin — intent preserved:** billing-once default (max_attempts=1) has dedicated regression coverage (cost-guardrails.test.ts:150-212); free-user ceiling's real assertion is the `max_free_users:0` branch (untouched, both directions covered).
- **Deletion clean; `p_owner_id` = intended owner everywhere** (isolation/quota assertions stay meaningful).

## Low / deferred (→ whole-branch triage / migration doc)
- The `jobs` WITH-CHECK RLS policy no longer has DIRECT coverage (grant-revocation, a stronger control, is tested instead). Moot unless the INSERT grant is ever restored — worth a one-line note in the migration doc.
- Free-user "admitted" numeric bound loosened (100→10M) for cross-file isolation — acceptable, already commented.

## Codex gap
Codex was UNAVAILABLE (background task hung — status `running`, log vanished, no findings). Per docs/plugins.md, a rigorous Claude (opus) adversarial review was run in its place (above) and satisfies the gate. **Re-attempt the Codex-specific pass before merge if access returns.**

## Verdict: Approved (CONVERGED — both passes no Blocking/High).
